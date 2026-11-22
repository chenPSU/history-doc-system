#!/usr/bin/env python3
"""Write render/captions.srt from the narration timing (TASKS P4.3).

  python tools/captions.py episodes/<ep>
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import captions as C  # noqa: E402


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    out, n = C.write(Path(argv[0]))
    print(f"{out}: {n} cues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
