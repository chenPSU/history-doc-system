#!/usr/bin/env python3
"""Make the thumbnails listed under `thumbnails:` in metadata.yaml (TASKS P5.2).

  python tools/thumbnail.py episodes/<ep>
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import thumbnail as T  # noqa: E402


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    ep = Path(argv[0])
    meta = yaml.safe_load((ep / "metadata.yaml").read_text(encoding="utf-8")) or {}
    specs = meta.get("thumbnails") or []
    if not specs:
        print("no `thumbnails:` in metadata.yaml")
        return 2
    bad = 0
    for spec in specs:
        out, problems = T.make(ep, spec, meta.get("title", ""))
        print(f"{out}: {spec['text']!r} ({out.stat().st_size // 1024} KB)")
        for p in problems:
            print("  PROBLEM", p)
            bad += 1
    if specs[0]["file"] != meta.get("thumbnail_file"):
        print(f"note: thumbnail_file is {meta.get('thumbnail_file')!r}; the first variant is {specs[0]['file']!r}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
