"""Shorts (TASKS P5.3): vertical 1080x1920 cuts of the episode, made by the same renderer as the long video.

Spec in metadata.yaml under `shorts:`

    shorts:
      - {slug: ships-over-the-hill, from: 214, to: 225, title: "They dragged 70 ships over a hill", end: "The full story: The Fall of Constantinople"}

`from`/`to` are sentence numbers. The short is the episode's own shots for those sentences, re-framed full-screen
for 9:16 (every picture is cover-cropped on its focus point; maps re-fit), with:
- big word captions (a few words at a time) instead of the long video's small labels: owner wants no text clutter;
- the episode mix for the window, the voice muted after the last sentence so the music carries a short end note
  that points to the long video (no new narration, so no TTS request);
- the last picture held under the end note.
Output: shorts/<n>-<slug>.mp4 and shorts/shorts.yaml (titles/descriptions for upload).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from pipeline import assemble as A
from pipeline import mix as MIX
from pipeline.captions import chunks

W, H, FPS = 1080, 1920, 30
TAIL = 2.8                 # end note under the music
WORDS = 16                 # characters per big caption


def window(timing: dict, first: int, last: int) -> tuple[float, float]:
    s = timing["sentences"]
    return float(s[first - 1]["start"]), float(s[last - 1]["end"]) + 0.35


def words(timing: dict, first: int, last: int, t0: float) -> list[dict]:
    out = []
    for s in timing["sentences"][first - 1:last]:
        text = re.sub(r"\s+", " ", s["text"]).strip()
        parts = chunks(text, WORDS)
        total = sum(len(p) for p in parts)
        a, b = float(s["start"]), float(s["end"])
        t = a
        for p in parts:
            d = (b - a) * len(p) / total
            out.append({"from": round((t - t0) * FPS), "dur": max(1, round(d * FPS)), "text": p})
            t += d
    return out


def slice_shots(shots: list[dict], f0: int, f1: int, tail: int) -> list[dict]:
    """Shots that overlap [f0, f1) in frames, moved to start at 0; the last one is held through the tail."""
    out = []
    for s in shots:
        a, b = s["from"], s["from"] + s["dur"]
        if b <= f0 or a >= f1:
            continue
        n = dict(s)
        n["from"] = max(0, a - f0)
        n["dur"] = min(b, f1) - max(a, f0)
        n["fadeIn"] = s["fadeIn"] if a >= f0 else 0
        n["fadeOut"] = s["fadeOut"] if b <= f1 else 0
        n.pop("caption", None)                       # no small labels in Shorts: big word captions only
        out.append(n)
    if out:
        last = out[-1]
        last["dur"] = (f1 - f0) - last["from"] + tail
        last["fadeOut"] = round(0.8 * FPS)
    return out


def make(ep: Path, n: int, spec: dict, concurrency: int | None = None, log=print) -> Path:
    ep = Path(ep)
    timing = json.loads((ep / "audio" / "narration_timing.json").read_text(encoding="utf-8"))
    edl = json.loads((ep / "render" / "edl.json").read_text(encoding="utf-8"))
    stage = ep / "render" / "stage_vertical"
    props = A.build_props(edl, ep, stage, W, H, log)      # vertical proxies and maps; cached between shorts
    a, b = window(timing, int(spec["from"]), int(spec["to"]))
    if not 15 <= b - a + TAIL <= 60:
        raise ValueError(f"short {spec['slug']}: {b - a + TAIL:.1f} s (Shorts must be 15-60 s)")
    f0, f1, tail = round(a * FPS), round(b * FPS), round(TAIL * FPS)
    audio = f"short_{n}.wav"
    MIX.mix(ep, a, b + TAIL, stage / audio, log=lambda *x: None, voice_until=b, write_report=False)
    short = {**props, "durationInFrames": (f1 - f0) + tail, "audio": audio,
             "shots": slice_shots(props["shots"], f0, f1, tail),
             "words": words(timing, int(spec["from"]), int(spec["to"]), a),
             "endNote": {"from": f1 - f0, "text": spec.get("end", "")}}
    pf = stage / f"short_{n}.json"
    pf.write_text(json.dumps(short), encoding="utf-8")
    out = ep / "shorts" / f"{n}-{spec['slug']}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    args = ["render", "src/index.ts", "Episode", str(out.resolve()), f"--props={pf.resolve()}", f"--public-dir={stage.resolve()}"]
    if concurrency:
        args.append(f"--concurrency={concurrency}")
    A.remotion(args)
    return out


def write_index(ep: Path, specs: list[dict], long_title: str) -> Path:
    items = []
    for n, s in enumerate(specs, 1):
        items.append({"file": f"shorts/{n}-{s['slug']}.mp4", "title": s["title"],
                      "description": f"{s['title']}. The full story: \"{long_title}\" on our channel.\n#Shorts #history",
                      "sentences": [s["from"], s["to"]]})
    out = Path(ep) / "shorts" / "shorts.yaml"
    out.write_text(yaml.safe_dump({"shorts": items}, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
    return out
