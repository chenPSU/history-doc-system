#!/usr/bin/env python3
"""Pre-upload checklist (TASKS P5.4): run every check on an episode and write <ep>/preflight.json.

  python tools/preflight.py episodes/<ep>          # exit 0 when passed, 1 when any check fails
  python tools/preflight.py episodes/<ep> --all    # also list the checks that passed

The uploader refuses an episode whose preflight.json is missing or has passed false.
Settings: config/preflight.yaml. Waive one check for one episode in brief.yaml: preflight_waivers: {id: reason}.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import preflight as P  # noqa: E402

MARK = {"pass": "ok  ", "fail": "FAIL", "warn": "warn", "n/a": "n/a "}


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--all", action="store_true", help="also print passed checks")
    a = ap.parse_args(argv)
    ep = Path(a.episode)
    pre = ep / "preflight.json"
    if pre.exists() and '"test_stub": true' in pre.read_text(encoding="utf-8"):
        print(f"{pre} is a test-upload stub; not overwritten")
        return 2
    res = P.run(ep)
    out = P.write(ep, res)
    for r in res["checks"]:
        if a.all or r["status"] in ("fail", "warn"):
            print(f"{MARK[r['status']]} {r['id']:<20} {r['detail']}" + (f"  [waived: {r['waived']}]" if r.get("waived") else ""))
    print("\nManual (owner, before approval):")
    for m in res["manual"]:
        print(f"  - {m}")
    n = len(res["checks"])
    print(f"\n{out}: {'PASSED' if res['passed'] else 'FAILED'} "
          f"({n - len(res['failed']) - len(res['warnings'])} ok, {len(res['warnings'])} warn, {len(res['failed'])} fail)")
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
