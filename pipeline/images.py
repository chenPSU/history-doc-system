"""AI illustrations for shots no real image shows (TASKS P3.4, decision D7).

Files in the episode folder:
- assets/ai_prompts.yaml   one entry per illustration_ai shot: the scene to draw (`subject`), plus the
                            episode's `style`, `context` and `real_people`. `init` writes it from the shot
                            list; we edit it by hand before any paid run.
- assets/ai-<no>.png        the image; its manifest row has ai_generated=y and the prompt hash.

Quota rules (lesson from Lupas, see memory/decisions): `plan` says how many requests a run sends and
what it costs before anything is called; `--go` is needed to send; an image whose prompt has not changed
is never requested again; a daily-quota answer stops the run at once.

Guard for the AC "no realistic AI image of a real person": every prompt is built as style + scene +
fixed rules (historical print, anonymous figures, no faces, no portraits), and a scene that names a real
person, a single ruler (sultan, emperor...) or asks for realism is refused before a request is sent.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import json
import os
import re
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import yaml

from pipeline.assets.common import read_manifest, write_manifest
from pipeline.voice import QuotaExhausted, VoiceError, _post_json, _with_retries, load_env

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "images.yaml"
VT = "illustration_ai"
PREFIX = re.compile(r"^\s*(illustration|old[- ]print style|ai)\s*:\s*", re.I)
STYLE_TAIL = re.compile(r",?\s*old[- ]print style\s*$", re.I)


class ImageError(VoiceError):
    pass


def load_config(path: Path = CONFIG_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- prompts file
def _cells(v: str | None) -> list[str]:
    return [x.strip() for x in (v or "").split("|")]


def ai_subshots(ep: Path) -> list[tuple[str, int, int, dict, str]]:
    """(key, sentence_no, j, row, search term) for every illustration_ai sub-shot.
    key is "N" when the sentence has one shot, "N.k" when it has several (k counts from 1)."""
    out = []
    for r in _shots(ep):
        terms = [t for t in _cells(r["search_terms"]) if t] or [""]
        vts = _cells(r["visual_type"])
        for j, term in enumerate(terms):
            vt = vts[j] if len(vts) > 1 and j < len(vts) else vts[0]
            if vt == VT:
                no = int(r["sentence_no"])
                out.append((str(no) if len(terms) == 1 else f"{no}.{j + 1}", no, j, r, term))
    return out


def _shots(ep: Path) -> list[dict]:
    with (ep / "shotlist.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def subject_from_terms(terms: str) -> str:
    s = STYLE_TAIL.sub("", PREFIX.sub("", terms.strip()))
    return s[:1].upper() + s[1:]


def prompts_path(ep: Path) -> Path:
    return Path(ep) / "assets" / "ai_prompts.yaml"


def load_prompts(ep: Path) -> dict:
    p = prompts_path(ep)
    if not p.exists():
        raise ImageError(f"{p} missing: run `python tools/images.py init {ep}` first")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def init_prompts(ep: Path, cfg: dict) -> tuple[Path, int]:
    """Write (or extend) assets/ai_prompts.yaml from the shot list. Existing entries are kept as edited."""
    ep, p = Path(ep), prompts_path(ep)
    data = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else None
    data = data or {"style": cfg.get("default_style", "engraving"), "context": "", "real_people": [], "shots": {}}
    shots = data.setdefault("shots", {})
    added = 0
    have = {str(k) for k in shots}
    for key, no, j, r, term in ai_subshots(ep):
        if key not in have:
            shots[int(key) if "." not in key else key] = {"sentence": r["sentence"], "subject": subject_from_terms(term)}
            added += 1
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# AI illustration prompts (tools/images.py). Edit `subject` per shot; `style` from config/images.yaml.\n"
                 + yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
    return p, added


# ---------------------------------------------------------------- prompt + guard
def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def problems(subject: str, context: str, cfg: dict, real_people: list[str]) -> list[str]:
    """Why this scene may not be sent (empty list = fine)."""
    out, text = [], f"{subject} {context}"
    words = _words(text)
    for w in cfg.get("banned_words", []):
        ws = _words(str(w))
        if ws and ws <= words:
            out.append(f"asks for realism or a portrait: {w!r}")
    for w in cfg.get("banned_roles", []):
        if w in words:                  # singular only: "a sultan" is one real man; "kings" in a crowd is not
            out.append(f"names a single ruler: {w!r} (draw anonymous people only)")
    for name in real_people or []:
        if re.search(rf"\b{re.escape(name)}\b", text, re.I):
            out.append(f"names a real person: {name!r}")
    if not subject.strip():
        out.append("empty subject")
    return out


def build_prompt(subject: str, context: str, style: str, cfg: dict) -> str:
    styles = cfg["styles"]
    if style not in styles:
        raise ImageError(f"unknown style {style!r}; config/images.yaml has: {', '.join(styles)}")
    ctx = f" Setting: {context.strip()}" if context.strip() else ""
    return f"{styles[style].strip()}\nScene: {subject.strip().rstrip('.')}.{ctx}\n{cfg['rules'].strip()}"


def prompt_hash(model: str, aspect: str, prompt: str) -> str:
    return hashlib.sha256(json.dumps([model, aspect, prompt]).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- plan
@dataclass
class Item:
    key: str             # "N" or "N.k" (sub-shot k of sentence N)
    no: int
    j: int
    sentence: str
    prompt: str
    hash: str
    file: str            # relative to the episode folder
    status: str          # "done" (image with this prompt exists) | "todo" | "refused"
    reasons: list[str]

    @property
    def asset_id(self) -> str:
        return f"ai-{self.no:03d}" if "." not in self.key else f"ai-{self.no:03d}-{self.j + 1}"


def plan(ep: Path, cfg: dict, only: set[int] | None = None) -> list[Item]:
    ep = Path(ep)
    data = load_prompts(ep)
    style, context, people = data.get("style", cfg.get("default_style")), data.get("context", ""), data.get("real_people", [])
    subs = {key: (no, j) for key, no, j, _, _ in ai_subshots(ep)}
    entries = {str(k): v for k, v in (data.get("shots") or {}).items()}
    man = {m["asset_id"]: m for m in read_manifest(ep / "assets" / "manifest.csv")}
    items = []
    for key, (no, j) in subs.items():
        entry = entries.get(key)
        if entry is None or (only and no not in only):
            continue
        aid = f"ai-{no:03d}" if "." not in key else f"ai-{no:03d}-{j + 1}"
        if entry.get("reuse"):                     # an AI image already made for another shot: no request
            src = man.get(entry["reuse"])
            ok = src is not None and (ep / src["file"]).exists()
            items.append(Item(key, no, j, entry.get("sentence", ""), "", "", src["file"] if ok else "", "reuse" if ok else "refused",
                              [] if ok else [f"reuse: {entry['reuse']} has no image"]))
            continue
        subject, ctx = entry.get("subject", ""), entry.get("context", context)   # a shot may override the setting
        prompt = build_prompt(subject, ctx, entry.get("style", style), cfg)
        h = prompt_hash(cfg["model"], cfg["aspect_ratio"], prompt)
        reasons = problems(subject, ctx, cfg, people)
        file = f"assets/{aid}.png"
        row = man.get(aid)
        done = row is not None and f"prompt_hash={h}" in row.get("notes", "") and (ep / row["file"]).exists()
        items.append(Item(key, no, j, entry.get("sentence", ""), prompt, h, row["file"] if done else file,
                          "refused" if reasons else ("done" if done else "todo"), reasons))
    missing = [k for k in subs if k not in entries] if not only else []
    if missing:
        raise ImageError(f"shots {missing} are {VT} but have no entry in ai_prompts.yaml: run `init` again")
    return items


# ---------------------------------------------------------------- provider
class FakeImage:
    """No network: returns a tiny valid PNG and records prompts."""

    PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

    def __init__(self):
        self.calls: list[str] = []

    def generate(self, prompt: str) -> tuple[bytes, str]:
        self.calls.append(prompt)
        return self.PNG, "image/png"


class GeminiImage:
    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    SAFETY_CATEGORIES = ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                         "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]

    def __init__(self, api_key: str, model: str, aspect: str, safety: str | None = None,
                 opener=urllib.request.urlopen, sleep=time.sleep):
        self.key, self.model, self.aspect, self.safety, self.opener, self.sleep = api_key, model, aspect, safety, opener, sleep

    def generate(self, prompt: str) -> tuple[bytes, str]:
        if not self.key:
            raise ImageError("GEMINI_API_KEY is missing in .env")
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["TEXT", "IMAGE"],
                                     "imageConfig": {"aspectRatio": self.aspect}}}
        if self.safety:
            body["safetySettings"] = [{"category": c, "threshold": self.safety} for c in self.SAFETY_CATEGORIES]
        raw = _with_retries(lambda: _post_json(self.URL.format(model=self.model), body,
                                               {"x-goog-api-key": self.key}, self.opener), self.sleep)
        data = json.loads(raw)
        cand = (data.get("candidates") or [{}])[0]
        parts = (cand.get("content") or {}).get("parts") or []
        part = next((p for p in parts if "inlineData" in p), None)
        if not part:
            said = " ".join(p.get("text", "") for p in parts if "text" in p)[:200]
            raise ImageError(f"no image (finishReason={cand.get('finishReason')!r}, "
                             f"promptFeedback={data.get('promptFeedback')!r}, text={said!r})")
        return base64.b64decode(part["inlineData"]["data"]), part["inlineData"].get("mimeType", "image/png")


def make_provider(cfg: dict):
    if cfg.get("provider") != "gemini":
        raise ImageError(f"unknown image provider {cfg.get('provider')!r}")
    load_env()
    return GeminiImage(os.environ.get("GEMINI_API_KEY", ""), cfg["model"], cfg["aspect_ratio"], cfg.get("safety"))


# ---------------------------------------------------------------- run
def _set_shot_asset(ep: Path, updates: dict[tuple[int, int], str]) -> None:
    """updates: (sentence_no, j) -> asset id, written into cell j of the row's asset_id."""
    path = ep / "shotlist.csv"
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        cols, rows = reader.fieldnames, list(reader)
    for r in rows:
        no = int(r["sentence_no"])
        n = len([t for t in _cells(r["search_terms"]) if t]) or 1
        ids = _cells(r.get("asset_id")) + [""] * n
        changed = False
        for j in range(n):
            if (no, j) in updates:
                ids[j], changed = updates[(no, j)], True
        if changed:
            r["asset_id"] = " | ".join(ids[:n]) if n > 1 else ids[0]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def manifest_row(item: Item, cfg: dict) -> dict:
    return {"asset_id": item.asset_id, "file": item.file, "source": f"gemini ({cfg['model']})",
            "source_url": f"generated:{cfg['model']}", "licence": "AI-generated for this channel (no third-party rights)",
            "credit": "AI illustration (Google Gemini)", "ai_generated": "y",
            "notes": f"class=ai; label={cfg.get('label', 'Illustration')}; prompt_hash={item.hash}; tools/images.py"}


def generate(ep: Path, cfg: dict, provider, go: bool = False, only: set[int] | None = None,
             max_requests: int | None = None, log=print) -> dict:
    ep = Path(ep)
    items = plan(ep, cfg, only)
    todo = [i for i in items if i.status == "todo"]
    if max_requests is not None:
        todo = todo[:max_requests]
    result = {"done": [i.no for i in items if i.status == "done"], "refused": [i.no for i in items if i.status == "refused"],
              "planned": [i.no for i in todo], "made": [], "failed": [], "requests": 0}
    if not go:
        return result
    mpath = ep / "assets" / "manifest.csv"
    for item in todo:
        result["requests"] += 1
        try:
            data, mime = provider.generate(item.prompt)
        except QuotaExhausted as e:
            log(f"#{item.key}: quota used up, stopping ({e})")
            result["failed"].append(item.no)
            break
        except ImageError as e:
            log(f"#{item.key}: {e}")
            result["failed"].append(item.no)
            continue
        if mime not in ("image/png", "image/jpeg", "image/webp"):
            log(f"#{item.key}: unexpected {mime}")
            result["failed"].append(item.no)
            continue
        item.file = f"assets/{item.asset_id}{'.png' if mime == 'image/png' else '.jpg' if mime == 'image/jpeg' else '.webp'}"
        (ep / item.file).parent.mkdir(parents=True, exist_ok=True)
        (ep / item.file).write_bytes(data)
        rows = [r for r in read_manifest(mpath) if r["asset_id"] != item.asset_id] + [manifest_row(item, cfg)]
        write_manifest(mpath, rows)            # saved after every image: a stopped run loses nothing
        _set_shot_asset(ep, {(item.no, item.j): item.asset_id})
        result["made"].append(item.no)
        log(f"#{item.key}: {item.file} ({len(data) // 1024} KB)")
    return result


def check(ep: Path, cfg: dict) -> list[str]:
    """Rights + P3.4 AC: every illustration_ai shot has a labelled AI asset made from a prompt that passed the guard."""
    ep, errs = Path(ep), []
    man = {m["asset_id"]: m for m in read_manifest(ep / "assets" / "manifest.csv")}
    for item in plan(ep, cfg):
        row = man.get(item.asset_id)
        if item.status == "reuse":
            continue
        if item.status == "refused":
            errs.append(f"#{item.key}: prompt refused: {'; '.join(item.reasons)}")
        elif item.status != "done":
            errs.append(f"#{item.key}: no image for the current prompt")
        elif row["ai_generated"] != "y" or f"label={cfg.get('label', 'Illustration')}" not in row["notes"]:
            errs.append(f"#{item.key}: manifest row must have ai_generated=y and the on-screen label")
    for aid, m in man.items():
        if aid.startswith("ai-") and m.get("ai_generated") != "y":
            errs.append(f"{aid}: AI asset without ai_generated=y")
    return errs
