#!/usr/bin/env python3
"""Render an animated map clip with Remotion (TASKS P3.3).

  python tools/map.py data/maps/constantinople.yaml                       # list clips
  python tools/map.py data/maps/constantinople.yaml overview_10s --still 9 --out x.png   # one frame
  python tools/map.py data/maps/constantinople.yaml overview_10s --out episodes/<ep>/render/maps/overview.mp4
  ... --4k            3840x2160 (final export); default 1920x1080
  ... --palette slate parchment | slate | sepia (rotate between consecutive videos)

A render inside an episode folder is logged to that episode's assets/manifest.csv with the map-data credit.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.maps import render as R  # noqa: E402


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("library")
    ap.add_argument("clip", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--still", type=float, help="render one frame at this second (PNG)")
    ap.add_argument("--4k", dest="uhd", action="store_true")
    ap.add_argument("--palette", default="parchment")
    a = ap.parse_args(argv)
    lib = R.load_library(Path(a.library))
    if not a.clip:
        for name, c in lib.get("clips", {}).items():
            print(f"{name}: {c['duration']} s, {len(c.get('show', []))} features")
        return 0
    w, h = (3840, 2160) if a.uhd else (1920, 1080)
    try:
        props = R.build_props(lib, a.clip, w, h, palette=a.palette)
        pf = R.write_props(props, a.clip)
        out = Path(a.out or ROOT / "video" / "out" / f"{a.clip}.{'png' if a.still is not None else 'mp4'}")
        R.render(pf, out, a.still)
    except R.MapError as e:
        print("ERROR", e)
        return 1
    print(f"wrote {out}")
    if a.still is None and R.log_to_manifest(out, a.clip, props.get("_credit_full", "")):
        print("logged to the episode manifest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
