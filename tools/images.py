#!/usr/bin/env python3
"""AI illustrations for illustration_ai shots (TASKS P3.4, D7). Paid: the owner approves each --go run.

  python tools/images.py init episodes/<ep>          # write/extend assets/ai_prompts.yaml from the shot list
  python tools/images.py episodes/<ep>               # dry run: prompts, request count, cost; nothing is sent
  python tools/images.py episodes/<ep> --show 82     # the full prompt of one shot
  python tools/images.py episodes/<ep> --go [--rows 82,172] [--max 3]
  python tools/images.py check episodes/<ep>         # every AI shot has a labelled image from a guarded prompt

An image whose prompt has not changed is never requested again. Edit a `subject` and that shot is redone.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import images as I  # noqa: E402


def _rows(spec: str | None) -> set[int] | None:
    if not spec:
        return None
    out: set[int] = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out |= set(range(int(a), int(b or a) + 1))
    return out


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argv = list(sys.argv[1:] if argv is None else argv)
    cfg = I.load_config()
    if argv and argv[0] == "init":
        p, added = I.init_prompts(Path(argv[1]), cfg)
        print(f"{p}: {added} new shot(s)")
        return 0
    if argv and argv[0] == "check":
        errs = I.check(Path(argv[1]), cfg)
        print("\n".join(errs) if errs else "PASS: every AI shot has a labelled image from a guarded prompt")
        return 1 if errs else 0
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--go", action="store_true", help="send the requests (costs money/quota)")
    ap.add_argument("--rows", help="only these sentence numbers, e.g. 82,172-173")
    ap.add_argument("--max", type=int, help="send at most this many requests")
    ap.add_argument("--show", type=int, help="print the full prompt of one shot")
    a = ap.parse_args(argv)
    ep = Path(a.episode)
    try:
        items = I.plan(ep, cfg, _rows(a.rows))
    except I.ImageError as e:
        print(e)
        return 2
    if a.show is not None:
        it = next((i for i in items if i.no == a.show), None)
        print(it.prompt if it else f"no AI shot #{a.show}")
        return 0 if it else 2
    for i in items:
        mark = {"done": "done   ", "todo": "todo   ", "refused": "REFUSED"}[i.status]
        subject = i.prompt.split("Scene: ", 1)[1].split("\n", 1)[0]
        print(f"{mark} #{i.no:>3} {subject[:100]}")
        for r in i.reasons:
            print(f"          ! {r}")
    todo = [i for i in items if i.status == "todo"][: a.max] if a.max else [i for i in items if i.status == "todo"]
    cost = len(todo) * float(cfg.get("cost_per_image_usd", 0))
    print(f"\n{cfg['model']}, {cfg['aspect_ratio']}: {len(todo)} request(s) to send, about ${cost:.2f}; "
          f"{sum(i.status == 'done' for i in items)} done, {sum(i.status == 'refused' for i in items)} refused")
    if not a.go:
        print("dry run: nothing sent. Add --go after the owner approves.")
        return 1 if any(i.status == "refused" for i in items) else 0
    res = I.generate(ep, cfg, I.make_provider(cfg), go=True, only=_rows(a.rows), max_requests=a.max)
    print(f"sent {res['requests']} request(s): made {len(res['made'])}, failed {res['failed'] or 'none'}")
    return 1 if res["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
