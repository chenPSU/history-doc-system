"""Episode renderer, Python side (TASKS P4.2): render/edl.json -> a Remotion stage -> render/<name>.mp4.

Remotion (video/src/episode) draws the frames; Python prepares everything it needs so the browser does
little work per frame:
- render/stage_<h>p/   the Remotion public dir: proxies sized for the frame (no 50 MB originals in Chrome),
                       pre-blurred dark backgrounds for 4:3 shots (a CSS blur on a 4K image is slow),
                       map clips, the narration (hard links where possible), a film-grain tile, props.json.
- props: every time in frames, transitions resolved into per-shot opacity ramps:
  * dissolve: the incoming shot starts D/2 early and ramps in on top; the outgoing one runs D/2 longer.
  * fade_black: the outgoing shot fades to black over F/2, the incoming one fades in over F/2.
  * the last shot fades out over the tail.
"""
from __future__ import annotations

import json
import os
import random
import shutil
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

from pipeline.maps.render import REMOTION_CLI, VIDEO, MapError, remotion

MAX_SCALE = 1.10          # the largest Ken Burns scale: proxies keep enough pixels for it
BG_SIZE = (640, 360)      # blurred backgrounds are tiny; the browser scales them up (they are a blur anyway)


class RenderError(RuntimeError):
    pass


def frames(sec: float, fps: int) -> int:
    return int(round(sec * fps))


def _link(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size == src.stat().st_size and dst.stat().st_mtime >= src.stat().st_mtime:
        return
    if dst.exists():
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


GRADED_TYPES = {"location"}   # present-day photos: warmer and muted so they sit with old art (style guide)


def grade(im: Image.Image) -> Image.Image:
    im = ImageEnhance.Color(im).enhance(0.62)
    r, g, b = im.split()
    r = r.point(lambda v: min(255, int(v * 1.04 + 4)))
    b = b.point(lambda v: int(v * 0.90))
    im = Image.merge("RGB", (r, g, b))
    return ImageEnhance.Contrast(ImageEnhance.Brightness(im).enhance(0.93)).enhance(0.94)


def make_proxy(src: Path, dst: Path, fit: str, width: int, height: int, graded: bool = False) -> tuple[int, int]:
    """Resize so the image fills (cover) or fits (contain) the frame at MAX_SCALE; never upscale."""
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        with Image.open(dst) as im:
            return im.size
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        s = (max if fit == "cover" else min)(width / w, height / h) * MAX_SCALE
        if s < 1:
            im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
        if graded:
            im = grade(im)
        dst.parent.mkdir(parents=True, exist_ok=True)
        im.save(dst, "JPEG", quality=90, optimize=True)
        return im.size


def make_background(src: Path, dst: Path) -> None:
    """Dark, heavily blurred, cover-cropped copy for 4:3 / portrait shots (style guide: same for the whole channel)."""
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        tw, th = BG_SIZE
        s = max(tw / w, th / h)
        im = im.resize((max(tw, round(w * s)), max(th, round(h * s))), Image.BILINEAR)
        left, top = (im.width - tw) // 2, (im.height - th) // 2
        im = im.crop((left, top, left + tw, top + th)).filter(ImageFilter.GaussianBlur(18))
        im = ImageEnhance.Brightness(ImageEnhance.Color(im).enhance(0.6)).enhance(0.38)
        dst.parent.mkdir(parents=True, exist_ok=True)
        im.save(dst, "JPEG", quality=85)


def make_grain(dst: Path, size: int = 512, seed: int = 7) -> None:
    if dst.exists():
        return
    rnd = random.Random(seed)
    im = Image.new("L", (size, size))
    im.putdata([max(0, min(255, int(rnd.gauss(128, 40)))) for _ in range(size * size)])
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst)


def build_props(edl: dict, ep: Path, stage: Path, width: int, height: int, log=print) -> dict:
    fps = int(edl["fps"])
    shots = edl["shots"]
    items = []
    for i, s in enumerate(shots):
        f0, f1 = frames(s["start"], fps), frames(s["end"], fps)
        nxt = shots[i + 1] if i + 1 < len(shots) else None
        start, end, fade_in, fade_out = f0, f1, 0, 0
        if s["transition_in"] == "dissolve":
            d = frames(s["transition_s"], fps)
            start, fade_in = f0 - d // 2, d
        elif s["transition_in"] == "fade_black":
            fade_in = frames(s["transition_s"], fps) // 2
        if nxt and nxt["transition_in"] == "dissolve":
            end = f1 + frames(nxt["transition_s"], fps) - frames(nxt["transition_s"], fps) // 2
        elif nxt and nxt["transition_in"] == "fade_black":
            fade_out = frames(nxt["transition_s"], fps) // 2
        if s.get("fade_out_s"):
            fade_out = frames(s["fade_out_s"], fps)
        item = {"id": s["id"], "kind": s["kind"], "from": max(0, start), "dur": end - max(0, start),
                "fadeIn": fade_in, "fadeOut": fade_out, "motion": s.get("motion", {"type": "static"})}
        if s["kind"] == "image":
            src = ep / s["file"]
            aid = s["asset_id"]
            graded = s.get("visual_type") in GRADED_TYPES
            name = f"{aid}{'_g' if graded else ''}.jpg"
            make_proxy(src, stage / "p" / name, s["fit"], width, height, graded)
            item.update(src=f"p/{name}", fit=s["fit"])
            if s["fit"] == "contain_blur":
                make_background(src, stage / "bg" / f"{aid}.jpg")
                item["bg"] = f"bg/{aid}.jpg"
        elif s["kind"] == "video":
            rel = f"v/{Path(s['file']).name}"
            _link(ep / s["file"], stage / rel)
            item.update(src=rel, clipFrames=frames(s["clip_s"], fps), holdLast=bool(s.get("hold_last")))
        elif s["kind"] == "card":
            item["card"] = s["card"]
        else:
            item["text"] = s.get("text", "")
            item["reason"] = s.get("reason", "")
        if s.get("label"):
            item["label"] = s["label"]
        items.append(item)
    narration = ep / edl["audio"]["narration"]
    _link(narration, stage / "narration.wav")
    make_grain(stage / "grain.png")
    return {"fps": fps, "width": width, "height": height, "durationInFrames": frames(edl["duration"], fps),
            "audio": "narration.wav", "grain": "grain.png", "shots": items}


def stage_episode(ep: Path, height: int = 2160, log=print) -> tuple[Path, Path]:
    ep = Path(ep)
    edl_path = ep / "render" / "edl.json"
    if not edl_path.exists():
        raise RenderError(f"{edl_path} missing: run `python tools/timeline.py {ep}` first")
    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    if edl.get("errors"):
        raise RenderError(f"edl.json has errors: {edl['errors'][:3]}")
    width = round(height * 16 / 9)
    stage = ep / "render" / f"stage_{height}p"
    props = build_props(edl, ep, stage, width, height, log)
    pf = stage / "props.json"
    pf.write_text(json.dumps(props), encoding="utf-8")
    return stage, pf


def render(ep: Path, out: Path, height: int = 2160, start: float | None = None, end: float | None = None,
           concurrency: int | None = None, log=print) -> Path:
    if not REMOTION_CLI.exists():
        raise RenderError("Remotion is not installed: run `npm install` in video/")
    stage, pf = stage_episode(ep, height, log)
    props = json.loads(pf.read_text(encoding="utf-8"))
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    args = ["render", "src/index.ts", "Episode", str(out), f"--props={pf.resolve()}",
            f"--public-dir={stage.resolve()}"]
    if start is not None or end is not None:
        a = frames(start or 0, props["fps"])
        b = min(props["durationInFrames"], frames(end, props["fps"])) - 1 if end is not None else props["durationInFrames"] - 1
        args.append(f"--frames={a}-{b}")
    if concurrency:
        args.append(f"--concurrency={concurrency}")
    try:
        remotion(args)
    except MapError as e:
        raise RenderError(str(e)) from e
    return out


__all__ = ["render", "stage_episode", "build_props", "make_proxy", "make_background", "RenderError", "VIDEO"]
