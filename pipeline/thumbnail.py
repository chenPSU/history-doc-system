"""Thumbnails (TASKS P5.2): one strong picture + at most 4 words, sepia + one accent colour, 1280x720.

A spec per variant lives in metadata.yaml under `thumbnails:`

    thumbnails:
      - {file: render/thumbnail.jpg,   asset: wm-147845, focus: [0.42, 0.33], zoom: 1.6, text: "HE WAS 21", accent: red, side: right}
      - {file: render/thumbnail_b.jpg, asset: ai-222,    focus: [0.5, 0.45],  zoom: 1.1, text: "SHIPS OVER A HILL", accent: gold}

The first one is what the uploader sets (`thumbnail_file`); the others are for YouTube's Test & Compare.
Rules checked: ≤ 4 words, the words are not already in the title, 1280x720, under YouTube's 2 MB limit.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from pipeline.assets.common import read_manifest

W, H = 1280, 720
ACCENT = {"red": (142, 27, 27), "gold": (201, 164, 92)}
INK = (239, 230, 210)
FONT = Path("C:/Windows/Fonts/georgiab.ttf")      # system serif bold; swap for an OFL font when on another OS
MAX_BYTES = 2 * 1024 * 1024


class ThumbError(ValueError):
    pass


def check_text(text: str, title: str) -> list[str]:
    out = []
    words = text.split()
    if len(words) > 4:
        out.append(f"{len(words)} words (max 4)")
    tw = {w.lower().strip(".,:;!?") for w in re.findall(r"[\w']+", title)}
    rep = [w for w in words if w.lower().strip(".,:;!?") in tw and len(w) > 2]
    if len(rep) >= 2 or (rep and len(words) <= 2):
        out.append(f"repeats the title: {' '.join(rep)}")
    return out


def frame(im: Image.Image, focus, zoom: float, size: tuple[int, int] = (W, H)) -> Image.Image:
    """Cover-crop to `size` (default 1280x720) around the focus point, then zoom in by `zoom`."""
    im = im.convert("RGB")
    sw, sh = im.size
    tw, th = size
    cw = min(sw, sh * tw / th) / zoom
    ch = cw * th / tw
    fx, fy = focus
    left = min(max(0, fx * sw - cw / 2), sw - cw)
    top = min(max(0, fy * sh - ch / 2), sh - ch)
    return im.crop((round(left), round(top), round(left + cw), round(top + ch))).resize((tw, th), Image.LANCZOS)


def sepia(im: Image.Image) -> Image.Image:
    g = ImageOps.autocontrast(im.convert("L"), cutoff=1)
    g = ImageEnhance.Contrast(g).enhance(1.25)
    return ImageOps.colorize(g, black=(28, 20, 12), white=(246, 232, 205), mid=(150, 118, 80))


def vignette(im: Image.Image, strength: float = 0.55) -> Image.Image:
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((-W * 0.15, -H * 0.2, W * 1.15, H * 1.2), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(120))
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    return Image.composite(im, Image.blend(im, dark, strength), mask)


def text_block(im: Image.Image, text: str, accent: str, side: str = "left") -> Image.Image:
    d = ImageDraw.Draw(im)
    words = text.split()
    for size in (150, 136, 122, 110):                    # biggest size that keeps one line in half the width
        font = ImageFont.truetype(str(FONT), size)
        one = d.textbbox((0, 0), text, font=font, stroke_width=6)
        if one[2] - one[0] <= W * 0.56:
            break
    if one[2] - one[0] <= W * 0.56 or len(words) < 2:
        lines = [text]                                   # one line when it fits in ~60% of the width
    else:
        cut = max(1, len(words) // 2 + len(words) % 2)
        lines = [" ".join(words[:cut]), " ".join(words[cut:])]
    boxes = [d.textbbox((0, 0), l, font=font, stroke_width=6) for l in lines]
    bw = max(b[2] - b[0] for b in boxes)
    lh = max(b[3] - b[1] for b in boxes)
    margin = 64
    x0 = margin if side == "left" else W - margin - bw
    y = H - margin - len(lines) * (lh + 12) - 18
    col = ACCENT[accent]
    d.rectangle((x0, y - 26, x0 + min(bw, 220), y - 14), fill=col)          # the accent rule above the words
    for l, b in zip(lines, boxes):
        d.text((x0 - b[0], y - b[1]), l, font=font, fill=INK, stroke_width=6, stroke_fill=(15, 10, 6))
        y += lh + 12
    return im


def make(ep: Path, spec: dict, title: str) -> tuple[Path, list[str]]:
    ep = Path(ep)
    problems = check_text(spec["text"], title)
    man = {m["asset_id"]: m for m in read_manifest(ep / "assets" / "manifest.csv")}
    if spec["asset"] not in man:
        raise ThumbError(f"{spec['asset']} not in the manifest")
    with Image.open(ep / man[spec["asset"]]["file"]) as src:
        im = frame(src, spec.get("focus", [0.5, 0.5]), float(spec.get("zoom", 1.0)))
    if spec.get("asset2"):            # two pictures that tell the story together: left panel fades into the right one
        if spec["asset2"] not in man:
            raise ThumbError(f"{spec['asset2']} not in the manifest")
        split = float(spec.get("split", 0.45))
        lw = int(W * (split + 0.1))
        with Image.open(ep / man[spec["asset"]]["file"]) as src:
            left = frame(src, spec.get("focus", [0.5, 0.5]), float(spec.get("zoom", 1.0)), (lw, H))
        with Image.open(ep / man[spec["asset2"]]["file"]) as src2:
            im = frame(src2, spec.get("focus2", [0.5, 0.5]), float(spec.get("zoom2", 1.0)))
        fade = int(W * 0.12)
        mask = Image.new("L", (lw, H), 255)
        for x in range(lw - fade, lw):
            mask.paste(int(255 * (lw - x) / fade), (x, 0, x + 1, H))
        im.paste(left, (0, 0), mask)
    im = vignette(sepia(im))
    im = text_block(im, spec["text"], spec.get("accent", "red"), spec.get("side", "left"))
    out = ep / spec["file"]
    out.parent.mkdir(parents=True, exist_ok=True)
    for q in (92, 85, 78):
        im.save(out, "JPEG", quality=q, optimize=True)
        if out.stat().st_size <= MAX_BYTES:
            break
    if out.stat().st_size > MAX_BYTES:
        problems.append("over 2 MB")
    return out, problems
