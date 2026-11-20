#!/usr/bin/env python3
"""Score gate: run the scorer on <episode>/script.md and write <episode>/score.json.

  python tools/check_episode.py episodes/2026-12-14-en-constantinople

Gate: every round >= 85, mean >= 90, no metric at 0 unless waived.
Waivers: keep a "waivers" list in an existing score.json: [{"metric": "...", "reason": "..."}].
English only for now (Thai scorer: TASKS P1.5).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import score  # noqa: E402

ROUNDS = [1, 2, 3, 4, 5]
ROUND_MIN, MEAN_MIN = 85, 90


def check(ep: Path) -> dict:
    ep = Path(ep)
    out_path = ep / "score.json"
    old = json.loads(out_path.read_text()) if out_path.exists() else {}
    waived = {w["metric"] for w in old.get("waivers", [])}
    r = score.run(str(ep / "script.md"), ROUNDS)
    rounds = {k: r["rounds"][k]["score"] for k in ROUNDS}
    mean = round(sum(rounds.values()) / len(ROUNDS), 1)
    zeros = [x["metric"] for k in ROUNDS for x in r["rounds"][k]["rows"] if x["score"] == 0 and x["metric"] not in waived]
    passed = all(v >= ROUND_MIN for v in rounds.values()) and mean >= MEAN_MIN and not zeros
    res = {"rounds": rounds, "mean": mean, "zero_metrics": zeros, "gate_passed": passed,
           "waivers": old.get("waivers", []), "detail": r}
    out_path.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    res = check(Path(sys.argv[1]))
    print(f"rounds={res['rounds']} mean={res['mean']} zero={res['zero_metrics']} -> {'PASS' if res['gate_passed'] else 'FAIL'}")
    sys.exit(0 if res["gate_passed"] else 1)
