"""Captions (TASKS P4.3): audio/narration_timing.json -> render/captions.srt (the file metadata.yaml points at).

The text is the script's own sentence (correct spelling, not the pronunciation lexicon). Each sentence becomes one
or more cues: at most 2 lines of at most 42 characters (Netflix/YouTube reading norms), cut at word boundaries,
timed in proportion to the characters inside the sentence's own start/end. Thai has no spaces between words, so
Thai text is cut at spaces when there are any, else by length.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

LINE, LINES = 42, 2


def _ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def chunks(text: str, limit: int = LINE * LINES) -> list[str]:
    """Split a sentence into pieces of at most `limit` characters at word boundaries, keeping them even."""
    if " " not in text:                             # no spaces (Thai): even pieces by length
        n = max(1, -(-len(text) // limit))
        size = -(-len(text) // n)
        return [text[i:i + size] for i in range(0, len(text), size)]
    words = text.split()
    total = len(" ".join(words))
    n = max(1, -(-total // limit))
    target = total / n
    out, cur = [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if cur and (len(cand) > limit or (len(cur) >= target and len(out) < n - 1)):
            out.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        out.append(cur)
    return out


def two_lines(piece: str) -> str:
    if len(piece) <= LINE:
        return piece
    if " " not in piece:
        half = -(-len(piece) // 2)
        return piece[:half] + "\n" + piece[half:]
    words = piece.split()
    best, cut = None, 1
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        score = max(len(a), len(b))
        if best is None or score < best:
            best, cut = score, i
    return " ".join(words[:cut]) + "\n" + " ".join(words[cut:])


def build(timing: dict) -> list[tuple[float, float, str]]:
    cues = []
    for s in timing["sentences"]:
        text = re.sub(r"\s+", " ", s["text"]).strip()
        a, b = float(s["start"]), float(s["end"])
        parts = []
        for piece in chunks(text):          # a piece that cannot make two short lines becomes one-line cues
            fits = all(len(line) <= LINE for line in two_lines(piece).split("\n"))
            parts += [piece] if fits else chunks(piece, LINE)
        total = sum(len(p) for p in parts)
        t = a
        for p in parts:
            d = (b - a) * len(p) / total
            cues.append((t, t + d, two_lines(p)))
            t += d
    return cues


def to_srt(cues: list[tuple[float, float, str]]) -> str:
    return "\n".join(f"{i}\n{_ts(a)} --> {_ts(b)}\n{text}\n" for i, (a, b, text) in enumerate(cues, 1))


def write(ep: Path) -> tuple[Path, int]:
    ep = Path(ep)
    timing = json.loads((ep / "audio" / "narration_timing.json").read_text(encoding="utf-8"))
    cues = build(timing)
    out = ep / "render" / "captions.srt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_srt(cues), encoding="utf-8")
    return out, len(cues)
