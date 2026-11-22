"""Episode metadata (TASKS P5.1): chapters, sources and credits for metadata.yaml, from files the pipeline made.

- chapters: section starts from render/edl.json. Titles come from `chapter_titles` in metadata.yaml when given,
  else from the chapter card ("1452 · The Bosphorus" -> "The Bosphorus, 1452"). Sections shorter than
  10 s are folded into the one before (YouTube's rule); the first chapter is 0:00.
- sources: the fact sheet's source table (works used only to locate others are left out).
- footage_credits: what the licences require, grouped to fit YouTube's 5,000-byte description:
  CC BY / BY-SA authors by licence, map data (OpenStreetMap ODbL), each music track in the composer's
  requested form, sound effects that need credit, one line for public-domain/CC0 sources, one for AI scenes.
Title, description and tags are the owner's words: written only when empty, never overwritten.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import yaml

from pipeline.assets.common import read_manifest

SKIP_SOURCE_KEYS = {"WK"}            # Wikipedia, used only to find the real sources
MIN_CHAPTER = 10.0


def _mmss(sec: float) -> str:
    sec = int(sec)
    h, rest = divmod(sec, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def card_title(text: str) -> str:
    if " · " in text:
        when, where = text.split(" · ", 1)
        return f"{where}, {when}"
    return text


def chapters(edl: dict, titles: dict | None = None) -> list[dict]:
    titles = titles or {}
    out = []
    raw = edl.get("chapters") or []
    ends = [c["start"] for c in raw[1:]] + [edl["duration"]]
    for c, end in zip(raw, ends):
        title = titles.get(c["section"]) or (card_title(c["title"]) if c["title"] else c["section"].title())
        if out and end - c["start"] < MIN_CHAPTER:
            continue                                   # too short for YouTube: part of the chapter before
        out.append({"time": "0:00" if not out else _mmss(c["start"]), "title": title, "_start": c["start"]})
    # a chapter that a short one was folded into must itself last 10 s; drop helper keys
    return [{k: v for k, v in c.items() if not k.startswith("_")} for c in out]


def sources(factsheet: Path) -> list[str]:
    text = Path(factsheet).read_text(encoding="utf-8")
    block = text.split("## Sources", 1)[1].split("\n## ", 1)[0]
    out = []
    for line in block.splitlines():
        m = re.match(r"^\|\s*([A-Z]+)\s*\|\s*(.+?)\s*\|\s*$", line)
        if not m or m.group(1) in ("Key",) or m.group(1) in SKIP_SOURCE_KEYS:
            continue
        out.append(m.group(2).replace("*", "").strip())
    return out


def _cls(row: dict) -> str:
    m = re.search(r"class=([\w-]+)", row.get("notes", ""))
    return m.group(1) if m else ""


def _title(row: dict) -> str:
    m = re.search(r"title=([^;]+)", row.get("notes", ""))
    t = m.group(1) if m else row["asset_id"]
    t = re.sub(r"\s*\(ISRC [^)]*\)|\.(mp3|ogg|oga|wav|jpg|png)$", "", t.replace("File:", ""))
    return re.sub(r"\s*\(MacLeod, Kevin\s*\)", "", t).strip()


def credits(ep: Path, edl: dict, mix_plan: dict | None) -> list[str]:
    ep = Path(ep)
    man = {m["asset_id"]: m for m in read_manifest(ep / "assets" / "manifest.csv")}
    used = {s["asset_id"] for s in edl["shots"] if s.get("asset_id")}
    audio = {x["asset"] for x in ((mix_plan or {}).get("music") or []) + ((mix_plan or {}).get("sfx") or [])}
    lines: list[str] = []
    by_licence: dict[str, set[str]] = defaultdict(set)
    pd_sources, osm, ai = set(), False, False
    for aid in sorted(used):
        m = man.get(aid)
        if not m:
            continue
        cls = _cls(m)
        if cls == "ai":
            ai = True
        elif cls == "own":
            osm = osm or "OpenStreetMap" in m.get("credit", "")
        elif cls in ("cc-by", "cc-by-sa"):
            author = re.sub(r",\s*(CC BY[^,]*|via Wikimedia Commons)", "", m["credit"])
            author = re.sub(r"\s*:?\s*https?://\S+|,?\s*\d{4}-\d{2}-\d{2}[\d: ]*", "", author).strip(" ,:")   # no links/dates
            by_licence[m["licence"]].add(author or "unknown author")
        else:
            pd_sources.add("Wikimedia Commons" if m.get("source", "").startswith("commons") else m.get("source", ""))
    for lic in sorted(by_licence):
        lines.append(f"{lic} (via Wikimedia Commons): " + "; ".join(sorted(by_licence[lic], key=str.lower)))
    if osm:
        lines.append("Map data © OpenStreetMap contributors (ODbL); maps drawn for this channel, with Natural Earth data.")
    if pd_sources:
        lines.append("Other pictures: public domain or CC0, via " + ", ".join(sorted(s for s in pd_sources if s)) + ".")
    music, music_lic, sfx = [], set(), []
    for aid in sorted(audio):
        m = man.get(aid)
        if not m:
            continue
        if "MacLeod" in m.get("credit", "") or "macleod" in m.get("notes", "").lower():
            music_lic.add(m["licence"].replace(" us", ""))
            music.append(f'"{_title(m)}"')
        elif _cls(m) in ("cc-by", "cc-by-sa"):
            sfx.append(f"{_title(m)}: {m['credit']}")
    if music:                       # the composer's requested credit, once for all his tracks
        lines.append(f"Music: {', '.join(sorted(set(music)))} by Kevin MacLeod (incompetech.com), "
                     f"licensed under Creative Commons {' / '.join(sorted(music_lic))} (creativecommons.org/licenses/by/3.0)")
    lines += [f"Sound: {x}" for x in sorted(set(sfx))]
    if ai:
        lines.append('Scenes marked "Illustration" are AI-generated in an old-print style, for moments no real picture shows.')
    return lines


def update(ep: Path, defaults: dict | None = None) -> dict:
    ep = Path(ep)
    path = ep / "metadata.yaml"
    meta = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    edl = json.loads((ep / "render" / "edl.json").read_text(encoding="utf-8"))
    plan_p = ep / "audio" / "mix_plan.yaml"
    plan = yaml.safe_load(plan_p.read_text(encoding="utf-8")) if plan_p.exists() else None
    meta["chapters"] = chapters(edl, meta.get("chapter_titles"))
    meta["sources"] = sources(ep / "factsheet.md")
    meta["footage_credits"] = credits(ep, edl, plan)
    for k, v in (defaults or {}).items():
        if not meta.get(k):
            meta[k] = v
    path.write_text("# Episode metadata (tools/metadata.py fills chapters, sources, footage_credits; title, description,\n"
                    "# tags and chapter_titles are edited by hand and kept). The uploader builds the description from\n"
                    "# description + chapters + sources + footage_credits (pipeline/youtube_upload.py).\n"
                    + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
    return meta
