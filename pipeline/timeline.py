"""Timeline builder (TASKS P4.1): narration timing + shot list + manifest -> render/edl.json.

The edit decision list (EDL) is what the renderer (P4.2) draws, second by second:
- shots: one item per sub-shot (a sentence's " | " cells split its time evenly). Shots touch end to end
  from 0 to the end of the narration plus a short tail, so the picture never goes black by accident.
  A shot runs from its sentence start to the next sentence start, so pauses keep the last picture.
- kind: image | video | card | placeholder (map clips not rendered yet, or a missing file).
- fit: "cover" for wide images; "contain_blur" for 4:3 and portrait (centred on a dark blurred copy).
- motion: Ken Burns 5-10% (bigger for longer shots), pans with the same slack; cards are static.
- transition_in: fade_black at chapter starts, dissolve after a scripted pause, otherwise cut.
- label: "Illustration" on every ai_generated=y asset (P3.4).
- cues: MUSIC / SFX / J-CUT / L-CUT / SOUND BRIDGE / MIX from script.md, at the time they apply
  (J-cuts and sound bridges start before the cut). The mix stage reads them.
- chapters: section starts with the chapter-card text (YouTube chapters, P5.1).
- stats + errors/warnings: the P4.2 pacing rules checked on the real timeline.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from pipeline import voice
from pipeline.assets.common import read_manifest

FPS, WIDTH, HEIGHT = 30, 3840, 2160
TAIL = 2.0                     # seconds of picture after the last word (sign-off), faded out
FADE_BLACK, DISSOLVE = 1.0, 0.8
PAUSE_FOR_DISSOLVE = 1.0       # a gap this long before a sentence (a [PAUSE]) gets a dissolve
WIDE = 1.5                     # aspect at or above this fills the frame; below it sits on a blurred copy
HOOK_WINDOW, HOOK_MAX, PACE, MAX_SHOT = 30.0, 3.0, (4.0, 7.0), 10.0
CHAPTER_SECTIONS = re.compile(r"^(CONTEXT|CHAPTER \d+|TURNING POINT|CLOSE)$")
AUDIO_CUES = ("MUSIC", "SFX", "J-CUT", "L-CUT", "SOUND BRIDGE", "MIX")
LEAD_CUES = ("J-CUT", "SOUND BRIDGE")   # sound of the next scene starts before its picture
LEAD = 1.0


class TimelineError(ValueError):
    pass


def split_cell(v: str | None) -> list[str]:
    return [x.strip() for x in (v or "").split("|")]


def _cell(cells: list[str], j: int) -> str:
    if len(cells) == 1:
        return cells[0]
    return cells[j] if j < len(cells) else ""


# ---------------------------------------------------------------- inputs
def load_timing(ep: Path) -> dict:
    p = ep / "audio" / "narration_timing.json"
    if not p.exists():
        raise TimelineError(f"{p} missing: run the narration stage (P2.1) first")
    return json.loads(p.read_text(encoding="utf-8"))


def load_shots(ep: Path) -> list[dict]:
    with (ep / "shotlist.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def script_cues(script: Path) -> list[tuple[int, str, str, str]]:
    """(index of the next narrated sentence, section, cue type, text) for every audio cue, in order.
    Sentences are counted exactly as pipeline/voice.parse_events counts them."""
    out, section, n, started = [], "", 0, False
    for raw in Path(script).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or re.match(r"^(TITLE|THUMB|SIGNOFF):", line):
            continue
        if line.startswith("## "):
            section, started = line[3:].strip().upper(), True
            continue
        if not started:
            continue
        if line.startswith("["):
            m = re.match(r"^\[([A-Z -]+?)\s*:\s*(.*?)\]?$", line)
            if m and m.group(1).strip() in AUDIO_CUES:
                out.append((n, section, m.group(1).strip(), m.group(2).strip()))
            continue
        n += sum(1 for s in voice.SENT_SPLIT.split(line) if s.strip())
    return out


def media_info(path: Path, probe=None) -> dict:
    """width, height (and duration for video) of an asset file."""
    ext = path.suffix.lower()
    if ext in (".mp4", ".webm", ".ogv", ".mov"):
        return (probe or ffprobe)(path)
    from PIL import Image
    with Image.open(path) as im:
        return {"width": im.width, "height": im.height}


def ffprobe(path: Path) -> dict:
    exe = shutil.which("ffprobe")
    if not exe:
        raise TimelineError("ffprobe not found (needed for video assets)")
    r = subprocess.run([exe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    s = d["streams"][0]
    return {"width": s["width"], "height": s["height"], "duration": float(d["format"]["duration"])}


# ---------------------------------------------------------------- pieces
def ken_burns(motion: str, dur: float) -> dict:
    """5-10% movement, more for longer shots. Scales are relative to the fitted frame."""
    amount = round(min(0.10, max(0.05, 0.05 + 0.01 * (dur - 3))), 3)
    if motion == "zoom_in":
        return {"type": "zoom", "scale": [1.0, 1 + amount]}
    if motion == "zoom_out":
        return {"type": "zoom", "scale": [1 + amount, 1.0]}
    if motion in ("pan_left", "pan_right", "pan_up", "pan_down"):
        # Scaled up by `amount`, then slide across the spare edge: x/y are fractions of that slack (-1..1).
        a, b = (-1, 1) if motion in ("pan_right", "pan_down") else (1, -1)
        axis = "x" if motion in ("pan_left", "pan_right") else "y"
        return {"type": "pan", "scale": 1 + amount, axis: [a, b]}
    if motion == "parallax":   # 2.5D not built yet: a slow push in
        return {"type": "zoom", "scale": [1.0, 1 + amount], "note": "parallax requested"}
    return {"type": "static"}


def card_of(term: str) -> dict:
    """card: / quote card: / end card: cells -> what the card shows.
    chapter = "<when> · <where>"; quote = words + (source); end = the sign-off, or blank under YouTube's end
    screen when the cell is only a production note (no closing punctuation, e.g. "series playlist")."""
    m = re.match(r"^\s*(quote |end )?card\s*:\s*(.*)$", term, flags=re.I)
    kind, text = ((m.group(1) or "").strip().lower(), m.group(2).strip()) if m else ("", term.strip())
    if kind == "quote":
        q = re.match(r'^(.*?)\s*\(([^()]*)\)\s*$', text)
        words, source = (q.group(1), q.group(2)) if q else (text, "")
        return {"text": words.strip().strip('"').strip("“”"), "source": source, "style": "quote"}
    if kind == "end":
        return {"text": text if re.search(r"[.!?]$", text) else "", "style": "end"}
    return {"text": text, "style": "chapter" if " · " in text else "fact"}


@dataclass
class Sub:
    no: int
    section: str
    j: int
    n: int
    vt: str
    term: str
    motion: str
    asset_id: str


def _subs(row: dict) -> list[Sub]:
    terms = [t for t in split_cell(row["search_terms"]) if t] or [""]
    vts, mots, ids = split_cell(row["visual_type"]), split_cell(row["motion"]), split_cell(row.get("asset_id"))
    def aid(j: int) -> str:     # one id for several shots belongs to the first (asset cells are positional)
        return ids[j] if j < len(ids) else ""
    return [Sub(int(row["sentence_no"]), row["section"], j, len(terms), _cell(vts, j), t, _cell(mots, j), aid(j))
            for j, t in enumerate(terms)]


# ---------------------------------------------------------------- build
def build(ep: Path, probe=None) -> dict:
    ep = Path(ep)
    timing, rows = load_timing(ep), load_shots(ep)
    sents = timing.get("sentences", [])
    if [s["text"] for s in sents] != [r["sentence"] for r in rows]:
        raise TimelineError("shotlist.csv and narration_timing.json disagree on the sentences: "
                            "re-run `python tools/shotlist.py init` after the narration")
    total = float(timing["total_seconds"])
    end_all = round(total + TAIL, 3)
    manifest = {m["asset_id"]: m for m in read_manifest(ep / "assets" / "manifest.csv")}
    info_cache: dict[str, dict] = {}
    shots, errors, warnings, missing = [], [], [], []

    for i, (row, sent) in enumerate(zip(rows, sents)):
        start = 0.0 if i == 0 else float(sent["start"])
        end = float(sents[i + 1]["start"]) if i + 1 < len(sents) else end_all
        gap_before = 0.0 if i == 0 else float(sent["start"]) - float(sents[i - 1]["end"])
        new_section = i > 0 and row["section"] != rows[i - 1]["section"]
        subs = _subs(row)
        step = (end - start) / len(subs)
        for sub in subs:
            s0 = round(start + step * sub.j, 3)
            s1 = round(end if sub.j == sub.n - 1 else start + step * (sub.j + 1), 3)
            dur = round(s1 - s0, 3)
            item = {"id": f"s{sub.no:03d}.{sub.j + 1}", "sentence_no": sub.no, "section": sub.section,
                    "start": s0, "end": s1, "duration": dur, "visual_type": sub.vt, "transition_in": "cut"}
            if sub.j == 0 and new_section:
                chapter = CHAPTER_SECTIONS.match(row["section"])
                item["transition_in"] = "fade_black" if chapter else "dissolve"
                item["transition_s"] = FADE_BLACK if chapter else DISSOLVE
            elif sub.j == 0 and gap_before >= PAUSE_FOR_DISSOLVE:
                item["transition_in"], item["transition_s"] = "dissolve", DISSOLVE
            if sub.vt == "card":
                item.update(kind="card", card=card_of(sub.term), motion={"type": "static"})
            elif sub.asset_id and sub.asset_id in manifest:
                m = manifest[sub.asset_id]
                path = ep / m["file"]
                if not path.exists():
                    item.update(kind="placeholder", text=sub.term, reason=f"file missing: {m['file']}")
                    missing.append(item["id"])
                else:
                    info = info_cache.get(m["file"]) or info_cache.setdefault(m["file"], media_info(path, probe))
                    video = "duration" in info
                    aspect = info["width"] / info["height"]
                    item.update(kind="video" if video else "image", asset_id=sub.asset_id, file=m["file"],
                                size=[info["width"], info["height"]],
                                fit="cover" if aspect >= WIDE else "contain_blur",
                                motion={"type": "play"} if video else ken_burns(sub.motion, dur))
                    if video:
                        item["clip_s"] = info["duration"]
                        if info["duration"] < dur:
                            item["hold_last"] = True
                    if m.get("ai_generated") == "y":
                        item["label"] = "Illustration"
            else:
                reason = "map clip not made yet" if sub.vt == "map" else ("no asset" if not sub.asset_id
                                                                         else f"{sub.asset_id} not in manifest")
                item.update(kind="placeholder", text=sub.term, reason=reason, motion={"type": "static"})
                missing.append(item["id"])
            shots.append(item)

    shots[-1]["fade_out_s"] = TAIL
    # pacing, on the real timeline (P4.2 AC)
    hook_long = [s["id"] for s in shots if s["start"] < HOOK_WINDOW and s["duration"] > HOOK_MAX]
    if hook_long:
        warnings.append(f"{len(hook_long)} shot(s) over {HOOK_MAX:.0f}s in the first 30s: {', '.join(hook_long)}")
    too_long = [f"{s['id']} ({s['duration']:.1f}s)" for s in shots if s["duration"] > MAX_SHOT]
    if too_long:
        errors.append(f"shot(s) over {MAX_SHOT:.0f}s: {', '.join(too_long)}")
    body = [s["duration"] for s in shots if s["start"] >= HOOK_WINDOW]
    in_pace = sum(PACE[0] <= d <= PACE[1] for d in body)
    for a, b in zip(shots, shots[1:]):
        if abs(a["end"] - b["start"]) > 1e-6:
            errors.append(f"gap or overlap between {a['id']} and {b['id']}")
    if shots[0]["start"] != 0 or abs(shots[-1]["end"] - end_all) > 1e-6:
        errors.append("shots do not cover the whole narration")

    # audio cues and chapters
    cues = []
    for n, section, kind, text in script_cues(ep / "script.md"):
        t = float(sents[n]["start"]) if n < len(sents) else total
        if kind in LEAD_CUES:
            t = max(0.0, t - LEAD)
        cues.append({"t": round(t, 3), "type": kind, "section": section, "text": text})
    chapters = []
    for s in shots:
        if not chapters or s["section"] != chapters[-1]["section"]:
            chapters.append({"section": s["section"], "start": s["start"], "title": ""})
        if s["kind"] == "card" and s["card"]["style"] == "chapter" and not chapters[-1]["title"]:
            chapters[-1]["title"] = s["card"]["text"]

    kinds: dict[str, int] = {}
    for s in shots:
        kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
    stats = {"shots": len(shots), "kinds": kinds, "duration": end_all,
             "first_30s": {"shots": sum(s["start"] < HOOK_WINDOW for s in shots),
                           "mean": round(sum(s["duration"] for s in shots if s["start"] < HOOK_WINDOW)
                                         / max(1, sum(s["start"] < HOOK_WINDOW for s in shots)), 2),
                           "over_3s": len(hook_long)},
             "after_30s": {"shots": len(body), "mean": round(sum(body) / max(1, len(body)), 2),
                           "in_4_to_7s": in_pace, "under_4s": sum(d < PACE[0] for d in body),
                           "over_7s": sum(d > PACE[1] for d in body)},
             "contain_blur": sum(s.get("fit") == "contain_blur" for s in shots),
             "labelled_ai": sum("label" in s for s in shots),
             "placeholders": len(missing)}
    return {"episode": ep.name, "fps": FPS, "width": WIDTH, "height": HEIGHT, "duration": end_all,
            "audio": {"narration": timing.get("audio", "audio/narration.wav"), "start": 0.0},
            "shots": shots, "cues": cues, "chapters": chapters, "stats": stats,
            "errors": errors, "warnings": warnings, "placeholders": missing}


def write(ep: Path, edl: dict) -> Path:
    out = Path(ep) / "render" / "edl.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(edl, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
