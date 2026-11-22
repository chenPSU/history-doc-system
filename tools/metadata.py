#!/usr/bin/env python3
"""Fill metadata.yaml: chapters, sources and credits from the pipeline's files (TASKS P5.1).

  python tools/metadata.py episodes/<ep>       # writes metadata.yaml, prints the full description and checks limits

Title, description, tags and chapter_titles are edited by hand in metadata.yaml and never overwritten.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import metadata as M  # noqa: E402
from pipeline.youtube_upload import build_description  # noqa: E402


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    meta = M.update(Path(argv[0]))
    desc = build_description(meta)
    print(desc)
    problems = []
    if not (meta.get("title") or "").strip():
        problems.append("title empty")
    if len(meta.get("title") or "") > 100:
        problems.append("title over 100 characters")
    if len(desc.encode("utf-8")) > 5000:
        problems.append(f"description {len(desc.encode('utf-8'))} bytes (> 5000)")
    if len(",".join(meta.get("tags") or [])) > 500:
        problems.append("tags over 500 characters")
    if len(meta.get("chapters") or []) < 3:
        problems.append("fewer than 3 chapters")
    print(f"\n--- title {len(meta.get('title') or '')} chars, description {len(desc.encode('utf-8'))} bytes, "
          f"{len(meta.get('chapters') or [])} chapters, tags {len(','.join(meta.get('tags') or []))} chars")
    for p in problems:
        print("PROBLEM", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
