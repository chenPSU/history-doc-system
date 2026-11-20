#!/usr/bin/env python3
"""Upload episodes to YouTube under config/upload_policy.yaml.

  python tools/upload.py episodes/2026-12-14-en-constantinople          # dry run: shows what would be sent
  python tools/upload.py episodes/2026-12-14-en-constantinople --go     # really upload
  python tools/upload.py --queue --go                                   # every episode that passes all gates

--queue is what a scheduled job (cron / launchd / Task Scheduler) runs, e.g. every day at 09:00.
Episodes that fail a gate are skipped and listed with the reasons.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import youtube_upload as yu  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("episode", nargs="?")
    ap.add_argument("--queue", action="store_true")
    ap.add_argument("--go", action="store_true", help="really upload (default is a dry run)")
    a = ap.parse_args(argv)
    policy = yu.load_policy()
    eps = sorted(p for p in (ROOT / "episodes").iterdir() if p.is_dir()) if a.queue else [Path(a.episode)]
    if not a.queue and not a.episode:
        ap.error("give an episode folder or --queue")
    code = 0
    for ep in eps:
        try:
            yu.upload_episode(ep, policy, go=a.go)
        except yu.GateError as e:
            print(f"SKIP {ep.name}:\n  - " + "\n  - ".join(e.failures))
            code = code if a.queue else 2
        except Exception as e:
            print(f"ERROR {ep.name}: {e}")
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
