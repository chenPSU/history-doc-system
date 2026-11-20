#!/usr/bin/env python3
"""Shot list for an episode (TASKS P3.1): one row per narrated sentence.

  python tools/shotlist.py init episodes/<ep>     # create/refresh rows from script.md, keep filled columns
  python tools/shotlist.py check episodes/<ep>    # validate against the style guide; exit 1 on errors

Columns: sentence_no, section, sentence, visual_type, search_terms, motion, duration_s, asset_id
- search_terms: one shot, or several shots in one sentence separated by " | " (the sentence time is split evenly).
- duration_s: from audio/narration_timing.json when it exists, else words / 150 wpm.

Rules checked (docs/style-guide.md, editing table):
- every narrated sentence has exactly one row, in order, with visual_type, search_terms and motion filled
- visual_type and motion come from the vocabularies below
- no shot longer than 10 s; in the first 30 s every shot <= 3 s (warning above that)
- Ken Burns zooms alternate direction (warning when two zoom shots in a row go the same way)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import voice  # noqa: E402

COLUMNS = ["sentence_no", "section", "sentence", "visual_type", "search_terms", "motion", "duration_s", "asset_id"]
VISUAL_TYPES = {
    "painting",        # public-domain painting (Wikimedia Commons PD-Art)
    "engraving",       # old print, woodcut, book illustration
    "manuscript",      # medieval manuscript page or miniature
    "artefact",        # object photo: coin, cannon, seal, icon
    "map",             # our own animated map (P3.3)
    "location",        # present-day photo or drone shot of the real place
    "archive_photo",   # historical photograph (1840s onward)
    "footage",         # archive film
    "card",            # text card: chapter card, date counter, quote card
    "illustration_ai", # AI painterly image, only where nothing real exists; labelled "Illustration"
}
MOTIONS = {"zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down", "parallax", "map_anim", "static"}
MAX_SHOT, HOOK_WINDOW, HOOK_SHOT = 10.0, 30.0, 3.0


def sentences_from_script(ep: Path) -> list[tuple[str, str]]:
    out, section = [], ""
    for kind, val in voice.parse_events(Path(ep) / "script.md"):
        if kind == "section":
            section = val
        elif kind == "sentence":
            out.append((section, val))
    return out


def durations(ep: Path, sents: list[tuple[str, str]]) -> list[float]:
    tf = Path(ep) / "audio" / "narration_timing.json"
    if tf.exists():
        t = json.loads(tf.read_text(encoding="utf-8"))
        timed = [s for s in t.get("sentences", [])]
        if [s["text"] for s in timed] == [x for _, x in sents]:
            return [round(s["end"] - s["start"], 2) for s in timed]
    return [round(len(x.split()) / voice.WPM * 60, 2) for _, x in sents]


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def init(ep: Path) -> list[dict]:
    ep = Path(ep)
    sents = sentences_from_script(ep)
    durs = durations(ep, sents)
    old = {}
    for r in read_rows(ep / "shotlist.csv"):
        old.setdefault(r.get("sentence", ""), r)  # keep work already done on unchanged sentences
    rows = []
    for i, ((section, text), d) in enumerate(zip(sents, durs), start=1):
        prev = old.get(text, {})
        rows.append({"sentence_no": i, "section": section, "sentence": text,
                     "visual_type": prev.get("visual_type", ""), "search_terms": prev.get("search_terms", ""),
                     "motion": prev.get("motion", ""), "duration_s": d, "asset_id": prev.get("asset_id", "")})
    write_rows(ep / "shotlist.csv", rows)
    return rows


def check(ep: Path) -> tuple[list[str], list[str]]:
    ep = Path(ep)
    errors, warnings = [], []
    sents = sentences_from_script(ep)
    rows = read_rows(ep / "shotlist.csv")
    if [r.get("sentence") for r in rows] != [x for _, x in sents]:
        errors.append(f"rows do not match the script's {len(sents)} sentences in order (have {len(rows)}): run init")
        return errors, warnings
    durs = durations(ep, sents)
    t, last_zoom = 0.0, None
    for r, d in zip(rows, durs):
        n = r["sentence_no"]
        for col in ("visual_type", "search_terms", "motion"):
            if not (r.get(col) or "").strip():
                errors.append(f"#{n}: {col} empty")
        vt, motions = r.get("visual_type", ""), [m.strip() for m in (r.get("motion") or "").split("|")]
        for v in [x.strip() for x in vt.split("|")]:
            if v and v not in VISUAL_TYPES:
                errors.append(f"#{n}: unknown visual_type {v!r}")
        for m in motions:
            if m and m not in MOTIONS:
                errors.append(f"#{n}: unknown motion {m!r}")
        shots = [s for s in (r.get("search_terms") or "").split("|") if s.strip()] or [""]
        each = d / len(shots)
        if each > MAX_SHOT:
            errors.append(f"#{n}: shot of {each:.1f}s (> {MAX_SHOT:.0f}s); split with ' | '")
        if t < HOOK_WINDOW and each > HOOK_SHOT:
            warnings.append(f"#{n}: {each:.1f}s shot inside the first 30 s (aim 2-3 s)")
        for m in motions:
            if m in ("zoom_in", "zoom_out"):
                if m == last_zoom:
                    warnings.append(f"#{n}: two {m} shots in a row; alternate the zoom direction")
                last_zoom = m
        t += d
    if any("illustration_ai" in r.get("visual_type", "") for r in rows):
        warnings.append("illustration_ai used: label 'Illustration' on screen and ai_generated=y in the manifest")
    return errors, warnings


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2 or argv[0] not in ("init", "check"):
        print(__doc__)
        return 2
    cmd, ep = argv[0], Path(argv[1])
    if cmd == "init":
        rows = init(ep)
        filled = sum(bool(r["visual_type"]) for r in rows)
        print(f"{ep.name}: {len(rows)} rows ({filled} already filled) -> shotlist.csv")
        return 0
    errors, warnings = check(ep)
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"{'FAIL' if errors else 'PASS'}: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
