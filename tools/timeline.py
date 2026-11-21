#!/usr/bin/env python3
"""Build the edit decision list for an episode (TASKS P4.1).

  python tools/timeline.py episodes/<ep>        # -> render/edl.json, prints pacing stats; exit 1 on errors

Inputs: audio/narration_timing.json, shotlist.csv, assets/manifest.csv (+ asset files), script.md cues.
Re-run after any change to those; the renderer (P4.2) reads only render/edl.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import timeline as T  # noqa: E402


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    ep = Path(argv[0])
    try:
        edl = T.build(ep)
    except T.TimelineError as e:
        print("ERROR", e)
        return 1
    out = T.write(ep, edl)
    st = edl["stats"]
    m, s = divmod(edl["duration"], 60)
    print(f"{out}: {st['shots']} shots, {int(m)}:{s:04.1f}, kinds {st['kinds']}")
    f, a = st["first_30s"], st["after_30s"]
    print(f"first 30 s: {f['shots']} shots, mean {f['mean']} s, {f['over_3s']} over 3 s")
    print(f"after 30 s: {a['shots']} shots, mean {a['mean']} s (aim 3-4 s); under 2 s: {a['under_2s']}, "
          f"over 7 s: {a['over_7s']}")
    print(f"4:3/portrait on blurred background: {st['contain_blur']}; AI labelled: {st['labelled_ai']}; "
          f"cues: {len(edl['cues'])}; chapters: {len(edl['chapters'])}")
    if edl["placeholders"]:
        reasons: dict[str, int] = {}
        for sh in edl["shots"]:
            if sh["kind"] == "placeholder":
                reasons[sh["reason"]] = reasons.get(sh["reason"], 0) + 1
        print(f"placeholders: {len(edl['placeholders'])} ({', '.join(f'{k}: {v}' for k, v in reasons.items())})")
    for w in edl["warnings"]:
        print("WARN ", w)
    for e in edl["errors"]:
        print("ERROR", e)
    print("FAIL" if edl["errors"] else "PASS")
    return 1 if edl["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
