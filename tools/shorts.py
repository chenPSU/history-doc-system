#!/usr/bin/env python3
"""Cut vertical Shorts from the episode (TASKS P5.3), as listed under `shorts:` in metadata.yaml.

  python tools/shorts.py episodes/<ep>            # all shorts
  python tools/shorts.py episodes/<ep> --only 1   # one short (1-based)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import shorts as S  # noqa: E402


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--only", type=int)
    ap.add_argument("--concurrency", type=int, default=10)
    a = ap.parse_args(argv)
    ep = Path(a.episode)
    meta = yaml.safe_load((ep / "metadata.yaml").read_text(encoding="utf-8")) or {}
    specs = meta.get("shorts") or []
    if not specs:
        print("no `shorts:` in metadata.yaml")
        return 2
    for n, spec in enumerate(specs, 1):
        if a.only and n != a.only:
            continue
        t0 = time.time()
        out = S.make(ep, n, spec, a.concurrency)
        print(f"{out} ({time.time() - t0:.0f} s)")
    print(S.write_index(ep, specs, meta.get("title", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
