#!/usr/bin/env python3
"""Render an episode from render/edl.json with Remotion (TASKS P4.2).

  python tools/assemble.py episodes/<ep>                          # full 4K -> render/<ep>.mp4
  python tools/assemble.py episodes/<ep> --1080 --from 0 --to 60  # quick preview of a time range
  python tools/assemble.py episodes/<ep> --stage-only             # proxies + props, no render

Run tools/timeline.py first. Local only: no network, no paid services.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import assemble as A  # noqa: E402


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--1080", dest="hd", action="store_true", help="1920x1080 instead of 4K")
    ap.add_argument("--from", dest="start", type=float, help="seconds")
    ap.add_argument("--to", dest="end", type=float, help="seconds")
    ap.add_argument("--out")
    ap.add_argument("--concurrency", type=int)
    ap.add_argument("--stage-only", action="store_true")
    a = ap.parse_args(argv)
    ep = Path(a.episode)
    height = 1080 if a.hd else 2160
    t0 = time.time()
    try:
        if a.stage_only:
            stage, pf = A.stage_episode(ep, height)
            print(f"staged {stage} ({time.time() - t0:.0f} s)")
            return 0
        part = "" if a.start is None and a.end is None else f"_{int(a.start or 0)}-{int(a.end) if a.end else 'end'}"
        out = Path(a.out) if a.out else ep / "render" / f"{ep.name}_{height}p{part}.mp4"
        A.render(ep, out, height, a.start, a.end, a.concurrency)
    except A.RenderError as e:
        print("ERROR", e)
        return 1
    print(f"{out} ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
