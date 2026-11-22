"""Pre-upload checklist (TASKS P5.4): the style guide's "Checklist ก่อนอัปโหลด" as file checks.

Reads the episode folder, writes <ep>/preflight.json:

    {"passed": bool, "checked_at": ..., "failed": [{id, detail}], "warnings": [...], "manual": [...], "checks": [...]}

Every check returns results with status pass | fail | warn | n/a. `passed` is true only when nothing fails.
`manual` lists what a file cannot prove (adding the end screen in Studio, page numbers in print, ...): it never
blocks, it is the owner's list before approved.yaml. The uploader (pipeline/youtube_upload.py) refuses an
episode whose preflight.json is missing or has passed false.

A check can be waived for one episode in brief.yaml, with a reason that goes into preflight.json:
    preflight_waivers: {end_tail: "reason"}
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "preflight.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def _yaml(p: Path, default=None):
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or default) if p.exists() else default


def _json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    except json.JSONDecodeError:
        return None


def _probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    return {"width": v.get("width"), "height": v.get("height"), "duration": float(d["format"]["duration"]),
            "audio": any(s.get("codec_type") == "audio" for s in d.get("streams", []))}


class Episode:
    """Lazy access to an episode folder's files."""

    def __init__(self, ep: Path, probe=_probe):
        self.ep = Path(ep)
        self.probe = probe
        self._c: dict = {}

    def _get(self, key, fn):
        if key not in self._c:
            self._c[key] = fn()
        return self._c[key]

    @property
    def brief(self) -> dict:
        return self._get("brief", lambda: _yaml(self.ep / "brief.yaml", {}))

    @property
    def meta(self) -> dict:
        return self._get("meta", lambda: _yaml(self.ep / "metadata.yaml", {}))

    @property
    def edl(self) -> dict | None:
        return self._get("edl", lambda: _json(self.ep / "render" / "edl.json"))

    @property
    def timing(self) -> dict | None:
        return self._get("timing", lambda: _json(self.ep / "audio" / "narration_timing.json"))

    @property
    def script(self) -> str:
        return self._get("script", lambda: (self.ep / "script.md").read_text(encoding="utf-8")
                         if (self.ep / "script.md").exists() else "")

    @property
    def factsheet(self) -> str:
        return self._get("fs", lambda: (self.ep / "factsheet.md").read_text(encoding="utf-8")
                         if (self.ep / "factsheet.md").exists() else "")

    @property
    def manifest(self) -> list[dict]:
        def read():
            p = self.ep / "assets" / "manifest.csv"
            return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []
        return self._get("man", read)

    def video(self) -> dict | None:
        def read():
            f = self.meta.get("video_file")
            p = self.ep / f if f else None
            return self.probe(p) if p and p.is_file() else None
        return self._get("video", read)


def R(id_: str, status: str, detail: str) -> dict:
    return {"id": id_, "status": status, "detail": detail}


# ---------------------------------------------------------------- facts
def fact_rows(md: str) -> list[dict]:
    """Rows of the `## Facts` table: #, fact, value, source 1, source 2, checked, disputed."""
    rows, on = [], False
    for line in md.splitlines():
        if line.startswith("## "):
            on = line.strip().lower() == "## facts"
            continue
        if on and re.match(r"^\|\s*\d+\s*\|", line):
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            c += [""] * (7 - len(c))
            rows.append(dict(zip(["no", "fact", "value", "src1", "src2", "checked", "disputed"], c[:7])))
    return rows


def todo_items(md: str) -> list[str]:
    m = re.search(r"^## Still to do[^\n]*\n(.*?)(?=^## |\Z)", md, re.M | re.S)
    return [x[2:].strip() for x in (m.group(1).splitlines() if m else []) if x.startswith("- ")]


def narration(script: str) -> list[str]:
    """Narrated lines of a scorer-format script (no headers, cues, or VOICE lines)."""
    out = []
    for line in script.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", "[", "TITLE:", "THUMB:", "SIGNOFF:", "VOICE")):
            continue
        out.append(s)
    return out


def _num(s: str) -> str:
    return s.replace(",", "").rstrip(".")


def check_facts(e: Episode, cfg: dict) -> list[dict]:
    md = e.factsheet
    if not md:
        return [R("facts", "fail", "factsheet.md missing")]
    rows = fact_rows(md)
    out = []
    if not rows:
        return [R("facts", "fail", "factsheet.md has no `## Facts` table rows")]
    empty = lambda v: not v or v in ("—", "-", "?")
    one = [r["no"] for r in rows if empty(r["src1"]) or empty(r["src2"])]
    out.append(R("facts.two_sources", "fail" if one else "pass",
                 f"rows without 2 sources: {', '.join(one)}" if one else f"{len(rows)} facts, each with 2 sources"))
    open_ = [r["no"] for r in rows if r["checked"].lower().startswith("open")]
    out.append(R("facts.open", "fail" if open_ else "pass",
                 f"rows still open: {', '.join(open_)}" if open_ else "no fact marked open"))
    # every figure written in digits in the narration is in the fact sheet
    flat = md.replace(",", "")
    miss = sorted({_num(n) for line in narration(e.script) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", line)
                   if not re.search(rf"(?<!\d){re.escape(_num(n))}(?!\d)", flat)}, key=lambda x: (len(x), x))
    out.append(R("facts.numbers", "fail" if miss else "pass",
                 f"numbers in the script missing from the fact sheet: {', '.join(miss)}" if miss
                 else "every number in the narration appears in the fact sheet"))
    todo = todo_items(md)
    if todo:
        out.append(R("facts.todo", "warn", f"{len(todo)} open note(s) in 'Still to do': " + " | ".join(t[:90] for t in todo)))
    return out


def check_quotes(e: Episode, cfg: dict) -> list[dict]:
    voices = re.findall(r'^VOICE\s*\(([^)]*)\)\s*:\s*"(.+)"', e.script, re.M)
    if not voices:
        return [R("quotes", "pass", "no VOICE lines")]
    m = re.search(r"^## First-person quotes[^\n]*\n(.*?)(?=^## |\Z)", e.factsheet, re.M | re.S)
    table = [[c.strip() for c in l.strip().strip("|").split("|")] for l in (m.group(1).splitlines() if m else [])
             if l.startswith("|") and not re.match(r"^\|\s*-", l) and "Speaker" not in l]
    bad = []
    for who, q in voices:
        row = next((t for t in table if len(t) >= 4 and t[0].lower() == who.strip().lower()
                    and q[:30].lower() in t[1].lower()), None)
        if not row or not row[2] or not row[3]:
            bad.append(f"{who}: \"{q[:40]}...\"")
    return [R("quotes", "fail" if bad else "pass",
              "VOICE lines without a primary source and translation in the fact sheet: " + "; ".join(bad) if bad
              else f"{len(voices)} VOICE line(s), each with source and translation")]


# ---------------------------------------------------------------- score
def check_score(e: Episode, cfg: dict) -> list[dict]:
    s = _json(e.ep / "score.json")
    if not s:
        return [R("score", "fail", "score.json missing: run tools/check_episode.py")]
    if not s.get("gate_passed"):
        return [R("score", "fail", f"score gate failed: rounds {s.get('rounds')}, mean {s.get('mean')}, zero {s.get('zero_metrics')}")]
    if (e.ep / "script.md").stat().st_mtime > (e.ep / "score.json").stat().st_mtime + 1:
        return [R("score", "fail", "script.md changed after score.json: re-run tools/check_episode.py")]
    w = s.get("waivers") or []
    return [R("score", "pass", f"mean {s.get('mean')}, rounds {s.get('rounds')}" + (f", {len(w)} waiver(s)" if w else ""))]


# ---------------------------------------------------------------- rights
def _licence_ok(lic: str, cfg: dict) -> bool:
    l = f" {lic.strip().lower()} "
    if any(x in l for x in cfg.get("licences_refused", [])):
        return False
    return any(x in l for x in cfg.get("licences_allowed", []))


def used_assets(edl: dict) -> list[str]:
    return [s["asset_id"] for s in (edl or {}).get("shots", []) if s.get("asset_id")]


def check_rights(e: Episode, cfg: dict) -> list[dict]:
    man = e.manifest
    if not man:
        return [R("rights", "fail", "assets/manifest.csv missing or empty")]
    by = {m["asset_id"]: m for m in man}
    plan = _yaml(e.ep / "audio" / "mix_plan.yaml", {}) or {}
    used = set(used_assets(e.edl)) | {x["asset"] for x in (plan.get("music") or []) + (plan.get("sfx") or [])}
    out = []
    unknown = sorted(a for a in used if a not in by)
    out.append(R("rights.logged", "fail" if unknown else "pass",
                 f"used but not in the manifest: {', '.join(unknown[:8])}" if unknown
                 else f"all {len(used)} assets in the video and mix are in the manifest"))
    rows = [by[a] for a in sorted(used) if a in by]
    missing = [r["asset_id"] for r in rows if not (r.get("licence") and r.get("source_url") and r.get("credit"))]
    out.append(R("rights.fields", "fail" if missing else "pass",
                 f"no licence/source/credit: {', '.join(missing[:8])}" if missing else "every used asset has licence, source and credit"))
    bad = [f"{r['asset_id']} ({r['licence']})" for r in rows if r.get("licence") and not _licence_ok(r["licence"], cfg)]
    out.append(R("rights.licence", "fail" if bad else "pass",
                 f"licence not allowed: {', '.join(bad[:8])}" if bad else "every licence allows commercial use and editing"))
    gone = [r["asset_id"] for r in rows if "#" not in r.get("file", "") and not (e.ep / r.get("file", "")).is_file()]
    out.append(R("rights.files", "fail" if gone else "pass",
                 f"files missing on disk: {', '.join(gone[:8])}" if gone else "every used asset file is on disk"))
    return out


# ---------------------------------------------------------------- AI
def check_ai(e: Episode, cfg: dict) -> list[dict]:
    from pipeline import images as IMG
    ai_rows = [m for m in e.manifest if m.get("ai_generated") == "y"]
    used = set(used_assets(e.edl))
    ai_used = [m for m in ai_rows if m["asset_id"] in used]
    out = []
    if not ai_used:
        out.append(R("ai", "pass", "no AI images in the video"))
    else:
        icfg = IMG.load_config()
        errs = IMG.check(e.ep, icfg) if (e.ep / "assets" / "ai_prompts.yaml").exists() else ["assets/ai_prompts.yaml missing"]
        out.append(R("ai.prompts", "fail" if errs else "pass",
                     "; ".join(errs[:5]) if errs else f"{len(ai_used)} AI images, every prompt passed the guard (no real person, no portrait, print style)"))
        label = icfg.get("label", "Illustration")
        ai_ids = {m["asset_id"] for m in ai_used}
        unlabelled = [s["id"] for s in e.edl["shots"] if s.get("asset_id") in ai_ids and s.get("label") != label]
        out.append(R("ai.label", "fail" if unlabelled else "pass",
                     f"AI shots without the on-screen '{label}' label: {', '.join(unlabelled[:8])}" if unlabelled
                     else f"every AI shot carries the '{label}' label"))
        people = (_yaml(e.ep / "assets" / "ai_prompts.yaml", {}) or {}).get("real_people") or []
        if not people:
            out.append(R("ai.real_people", "warn", "ai_prompts.yaml has no real_people list: names are not blocked in prompts"))
    # YouTube "altered or synthetic content": needed for realistic AI imagery; old-print illustrations are not realistic
    realistic = [m["asset_id"] for m in ai_used if "realistic=y" in (m.get("notes") or "")
                 or (m.get("file") or "").lower().endswith((".mp4", ".mov", ".webm"))]
    flag = bool(e.meta.get("altered_or_synthetic_disclosure"))
    if realistic and not flag:
        out.append(R("ai.disclosure", "fail", f"realistic AI media ({', '.join(realistic[:5])}) but altered_or_synthetic_disclosure is false"))
    else:
        out.append(R("ai.disclosure", "pass", f"disclosure {'on' if flag else 'off'}: "
                     + ("realistic AI media present" if realistic else "AI images are old-print illustrations, labelled on screen")))
    return out


# ---------------------------------------------------------------- picture and hook
def check_picture(e: Episode, cfg: dict) -> list[dict]:
    edl = e.edl
    if not edl:
        return [R("picture", "fail", "render/edl.json missing: run tools/timeline.py")]
    out = []
    if edl.get("errors"):
        out.append(R("picture.edl", "fail", "; ".join(edl["errors"])))
    if edl.get("placeholders"):
        out.append(R("picture.placeholders", "fail", f"{len(edl['placeholders'])} shots without a picture: {', '.join(edl['placeholders'][:8])}"))
    lim = float(cfg.get("max_still_s", 10))
    shots = edl["shots"]
    last_word = float((e.timing or {}).get("sentences", [{}])[-1].get("end", edl["duration"]))
    # the end-screen tail after the sign-off is exempt: YouTube's end screen covers it
    long_ = [f"{s['id']} ({s['duration']:.1f}s)" for s in shots
             if s.get("kind") != "video" and min(s["end"], last_word + 1.0) - s["start"] > lim]
    out.append(R("picture.still", "fail" if long_ else "pass",
                 f"pictures held over {lim:.0f}s: {', '.join(long_)}" if long_
                 else f"{len(shots)} shots, longest {max(s['duration'] for s in shots):.1f}s"))
    for w in edl.get("warnings") or []:
        out.append(R("picture.pace", "warn", w))
    return out


def check_hook(e: Episode, cfg: dict) -> list[dict]:
    win = float(cfg.get("hook_window_s", 30))
    heads = re.findall(r"^##\s+(.+?)\s*$", e.script, re.M)
    if not heads or heads[0].strip().upper() != "HOOK":
        return [R("hook", "fail", "the script does not open with ## HOOK")]
    sents = (e.timing or {}).get("sentences") or []
    q = next((s for s in sents if "?" in s["text"]), None)
    if not q or float(q["start"]) > win:
        return [R("hook", "fail", f"no question in the first {win:.0f}s" + (f" (first at {q['start']:.0f}s)" if q else ""))]
    return [R("hook", "pass", f"opens with HOOK; first question at {float(q['start']):.0f}s: \"{q['text'][:60]}\"")]


# ---------------------------------------------------------------- metadata, captions, end screen
def _secs(t: str) -> int:
    p = [int(x) for x in str(t).split(":")]
    return sum(v * 60 ** i for i, v in enumerate(reversed(p)))


def check_metadata(e: Episode, cfg: dict) -> list[dict]:
    from pipeline.youtube_upload import build_description
    m, out = e.meta, []
    if not m:
        return [R("metadata", "fail", "metadata.yaml missing: run tools/metadata.py")]
    title = (m.get("title") or "").strip()
    desc = build_description(m)
    probs = []
    if not title:
        probs.append("title empty")
    if len(title) > 100:
        probs.append(f"title {len(title)} chars (> 100)")
    if re.search(r"[<>]", title + desc):
        probs.append("< or > in title or description")
    if len(desc.encode("utf-8")) > 5000:
        probs.append(f"description {len(desc.encode('utf-8'))} bytes (> 5000)")
    if len(",".join(m.get("tags") or [])) > 500:
        probs.append("tags over 500 characters")
    if not m.get("sources"):
        probs.append("no sources")
    if not m.get("footage_credits"):
        probs.append("no footage credits")
    if "4k" in title.lower():
        probs.append("'4K' in the title (export is 1080p, D4)")
    out.append(R("metadata.limits", "fail" if probs else "pass", "; ".join(probs) if probs
                 else f"title {len(title)} chars, description {len(desc.encode('utf-8'))} bytes, {len(m.get('tags') or [])} tags"))
    # chapters: YouTube needs >= 3, the first at 0:00, each >= 10 s
    ch = m.get("chapters") or []
    t = [_secs(c["time"]) for c in ch]
    v = e.video()
    dur = v["duration"] if v else (e.edl or {}).get("duration", 0)
    cp = []
    if len(ch) < 3:
        cp.append(f"{len(ch)} chapters (YouTube needs 3+)")
    if t and t[0] != 0:
        cp.append("first chapter not at 0:00")
    gaps = [b - a for a, b in zip(t, t[1:] + [dur])]
    short = [ch[i]["time"] for i, g in enumerate(gaps) if g < cfg.get("chapter_min_s", 10)]
    if short:
        cp.append(f"chapters under {cfg.get('chapter_min_s', 10)}s: {', '.join(short)}")
    if t != sorted(t):
        cp.append("chapters out of order")
    out.append(R("metadata.chapters", "fail" if cp else "pass", "; ".join(cp) if cp else f"{len(ch)} chapters"))
    return out


def check_video(e: Episode, cfg: dict) -> list[dict]:
    f = e.meta.get("video_file")
    p = e.ep / f if f else None
    if not p or not p.is_file():
        return [R("video", "fail", f"video_file not found: {f}")]
    v = e.video()
    out, probs = [], []
    if not v["audio"]:
        probs.append("no audio track")
    if (v["height"] or 0) < cfg.get("min_video_height", 1080):
        probs.append(f"{v['width']}x{v['height']} (< {cfg.get('min_video_height', 1080)}p)")
    if v["width"] and v["height"] and abs(v["width"] / v["height"] - 16 / 9) > 0.01:
        probs.append("not 16:9")
    edl_d = (e.edl or {}).get("duration")
    if edl_d and abs(v["duration"] - edl_d) > 0.5:
        probs.append(f"video {v['duration']:.1f}s but the edit is {edl_d:.1f}s: re-render")
    out.append(R("video.file", "fail" if probs else "pass", "; ".join(probs) if probs
                 else f"{f}: {v['width']}x{v['height']}, {v['duration'] / 60:.1f} min"))
    edl_p = e.ep / "render" / "edl.json"
    if edl_p.exists() and edl_p.stat().st_mtime > p.stat().st_mtime + 1:
        out.append(R("video.stale", "warn", "edl.json is newer than the video: check that the render is current"))
    # end screen: YouTube puts it on the last 5-20 s; the style guide wants a 10-20 s music tail after the sign-off
    lo, hi = cfg.get("end_tail_s", [10, 20])
    sents = (e.timing or {}).get("sentences") or []
    if sents:
        tail = v["duration"] - float(sents[-1]["end"])
        ok = lo <= tail <= hi + 1
        out.append(R("end_tail", "pass" if ok else "fail",
                     f"{tail:.1f}s after the sign-off" + ("" if ok else f" (need {lo}-{hi}s of music tail for the end screen)")))
    return out


def check_captions(e: Episode, cfg: dict) -> list[dict]:
    f = e.meta.get("captions_file")
    p = e.ep / f if f else None
    if not p or not p.is_file():
        return [R("captions", "fail", f"captions_file not found: {f}")]
    text = p.read_text(encoding="utf-8-sig")
    ends = re.findall(r"--> (\d+):(\d+):(\d+)[,.](\d+)", text)
    if not ends:
        return [R("captions", "fail", f"{f} has no cues")]
    last = max(int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000 for h, m, s, ms in ends)
    v = e.video()
    if v and last > v["duration"] + 1:
        return [R("captions", "fail", f"captions run to {last:.0f}s, past the video end ({v['duration']:.0f}s)")]
    src = e.ep / "audio" / "narration_timing.json"
    if src.exists() and src.stat().st_mtime > p.stat().st_mtime + 1:
        return [R("captions", "fail", "narration_timing.json is newer than the captions: re-run tools/captions.py")]
    return [R("captions", "pass", f"{len(ends)} cues")]


# ---------------------------------------------------------------- thumbnail and variety
def ahash(path: Path) -> int:
    from PIL import Image
    im = Image.open(path).convert("L").resize((8, 8), Image.LANCZOS)
    px = list(im.tobytes())
    avg = sum(px) / 64
    return sum(1 << i for i, x in enumerate(px) if x > avg)


def check_thumbnail(e: Episode, cfg: dict) -> list[dict]:
    from PIL import Image
    from pipeline.thumbnail import check_text
    f = e.meta.get("thumbnail_file")
    p = e.ep / f if f else None
    if not p or not p.is_file():
        return [R("thumbnail", "fail", f"thumbnail_file not found: {f}")]
    probs = []
    w, h = Image.open(p).size
    if [w, h] != list(cfg.get("thumb_size", [1280, 720])):
        probs.append(f"{w}x{h} (need {cfg.get('thumb_size')})")
    if p.stat().st_size > cfg.get("thumb_max_bytes", 2 * 1024 * 1024):
        probs.append(f"{p.stat().st_size // 1024} KB (> 2 MB)")
    if p.suffix.lower() not in (".jpg", ".jpeg", ".png"):
        probs.append("not JPG/PNG")
    for spec in e.meta.get("thumbnails") or []:
        if spec.get("file") == f:
            probs += [f"text '{spec.get('text')}': {x}" for x in check_text(spec.get("text", ""), e.meta.get("title", ""))]
    return [R("thumbnail", "fail" if probs else "pass", "; ".join(probs) if probs else f"{f}: {w}x{h}, {p.stat().st_size // 1024} KB")]


def previous_videos(e: Episode, n: int) -> list[Path]:
    """The last n uploaded episodes in the same language (upload.json with a video_id; test uploads skipped)."""
    lang = e.brief.get("language")
    done = []
    for d in sorted(e.ep.parent.iterdir()):
        if d == e.ep or not d.is_dir():
            continue
        b = _yaml(d / "brief.yaml", {}) or {}
        u = _json(d / "upload.json") or {}
        if b.get("language") == lang and not b.get("test_upload") and u.get("video_id"):
            done.append((str(u.get("publish_at") or u.get("uploaded_at") or d.name), d))
    return [d for _, d in sorted(done)[-n:]]


def check_variety(e: Episode, cfg: dict) -> list[dict]:
    prev = previous_videos(e, int(cfg.get("previous_videos", 3)))
    if not prev:
        return [R("variety", "pass", f"first {e.brief.get('language', '?').upper()} video on the channel: nothing to compare")]
    out = []
    formula = e.brief.get("title_formula")
    same = [d.name for d in prev if formula and (_yaml(d / "brief.yaml", {}) or {}).get("title_formula") == formula]
    out.append(R("variety.title", "fail" if same else "pass",
                 f"title formula '{formula}' also used by {', '.join(same)}" if same else f"title formula '{formula}' differs from the last {len(prev)}"))
    mine = e.ep / (e.meta.get("thumbnail_file") or "")
    close = []
    if mine.is_file():
        h = ahash(mine)
        for d in prev:
            t = d / ((_yaml(d / "metadata.yaml", {}) or {}).get("thumbnail_file") or "")
            if t.is_file():
                dist = bin(h ^ ahash(t)).count("1")
                if dist < cfg.get("thumb_min_distance", 12):
                    close.append(f"{d.name} (distance {dist})")
    out.append(R("variety.thumbnail", "fail" if close else "pass",
                 f"thumbnail looks like: {', '.join(close)}" if close else "thumbnail differs from the last videos"))
    style = (_yaml(e.ep / "assets" / "ai_prompts.yaml", {}) or {}).get("style")
    last_style = (_yaml(prev[-1] / "assets" / "ai_prompts.yaml", {}) or {}).get("style")
    if style and style == last_style:
        out.append(R("variety.ai_style", "warn", f"AI style '{style}' same as {prev[-1].name}: rotate styles"))
    return out


# ---------------------------------------------------------------- Thai channel
def check_thai(e: Episode, cfg: dict) -> list[dict]:
    if e.brief.get("language") != "th":
        return [R("thai", "n/a", "English channel")]
    t = cfg.get("thai") or {}
    m = e.meta
    text = "\n".join([e.script, m.get("title") or "", m.get("description") or "", " ".join(m.get("tags") or [])]).lower()
    hit = lambda words: sorted({w for w in words if w.lower() in text})
    out = []
    mon = hit(t.get("monarchy", []))
    out.append(R("thai.monarchy", "fail" if mon else "pass", f"monarchy terms: {', '.join(mon)}" if mon else "no Thai-monarchy terms"))
    kh = hit(t.get("khmer", []))
    if kh and not e.brief.get("tone_checked"):
        out.append(R("thai.khmer", "fail", f"Khmer topic ({', '.join(kh)}): needs a tone check (brief.yaml tone_checked: true)"))
    else:
        out.append(R("thai.khmer", "pass", "tone checked" if kh else "no Khmer topic"))
    inf = hit(t.get("inflammatory", []))
    out.append(R("thai.tone", "fail" if inf else "pass", f"inflammatory wording: {', '.join(inf)}" if inf else "no inflammatory wording"))
    return out


# ---------------------------------------------------------------- shorts
def check_shorts(e: Episode, cfg: dict) -> list[dict]:
    idx = _yaml(e.ep / "shorts" / "shorts.yaml", {}) or {}
    items = idx.get("shorts") or []
    if not items:
        return [R("shorts", "warn", "no Shorts yet (style guide: 3-5 per long video)")]
    probs = []
    for s in items:
        p = e.ep / s["file"]
        if not p.is_file():
            probs.append(f"{s['file']} missing")
            continue
        v = e.probe(p)
        if not 15 <= v["duration"] <= 60:
            probs.append(f"{s['file']}: {v['duration']:.0f}s")
        if v["width"] and v["height"] and v["width"] * 16 != v["height"] * 9:
            probs.append(f"{s['file']}: not 9:16")
    return [R("shorts", "fail" if probs else "pass", "; ".join(probs) if probs else f"{len(items)} Shorts, 15-60 s, 9:16")]


# ---------------------------------------------------------------- manual items
def manual_items(e: Episode) -> list[str]:
    out = ["Add the end screen in YouTube Studio (the API cannot): subscribe + the next episode in the series, over the music tail."]
    book = [r["no"] for r in fact_rows(e.factsheet) if r["checked"].lower().startswith("book")]
    if book:
        out.append(f"{len(book)} fact rows are checked against the cited books' standard account only (`book`), not opened in print: add page numbers when a copy is at hand.")
    approx = 0
    for lib in sorted((ROOT / "data" / "maps").glob("*.yaml")):
        txt = lib.read_text(encoding="utf-8")
        if e.ep.name in txt or e.brief.get("slug", "\0") in lib.stem:
            approx += len(re.findall(r"^\s+approximate:\s*true", txt, re.M))
    if approx:
        out.append(f"{approx} map clips draw hand-made regional borders (`approximate: true`): spot-check them against an atlas.")
    out.append("Watch the final render once, start to end (picture, sound, captions).")
    return out


CHECKS = [check_score, check_facts, check_quotes, check_rights, check_ai, check_picture, check_hook,
          check_metadata, check_video, check_captions, check_thumbnail, check_variety, check_thai, check_shorts]


def run(ep: Path, cfg: dict | None = None, probe=_probe) -> dict:
    cfg = cfg or load_config()
    e = Episode(ep, probe)
    results = []
    for fn in CHECKS:
        try:
            results += fn(e, cfg)
        except Exception as ex:   # a broken check is a failed check, never a silent pass
            results.append(R(fn.__name__.replace("check_", ""), "fail", f"check crashed: {type(ex).__name__}: {ex}"))
    waivers = (e.brief.get("preflight_waivers") or {})
    for r in results:
        if r["status"] == "fail" and r["id"] in waivers:
            r["status"], r["waived"] = "warn", str(waivers[r["id"]])
    failed = [r for r in results if r["status"] == "fail"]
    return {"passed": not failed, "episode": Path(ep).name,
            "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "failed": [{"id": r["id"], "detail": r["detail"]} for r in failed],
            "warnings": [{"id": r["id"], "detail": r["detail"], **({"waived": r["waived"]} if "waived" in r else {})}
                         for r in results if r["status"] == "warn"],
            "manual": manual_items(e), "checks": results}


def write(ep: Path, res: dict) -> Path:
    p = Path(ep) / "preflight.json"
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return p
