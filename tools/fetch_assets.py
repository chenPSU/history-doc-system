#!/usr/bin/env python3
"""Find and download licence-checked images for an episode (TASKS P3.2). Free sources, no API keys.

  python tools/fetch_assets.py search "Zonaro conquest of Constantinople"     # look only, no download
  python tools/fetch_assets.py search "Theodosian walls" --source ia
  python tools/fetch_assets.py episodes/<ep>                     # plan: how many shots need an asset
  python tools/fetch_assets.py episodes/<ep> --go                # search + download, fill asset_id
  python tools/fetch_assets.py episodes/<ep> --go --rows 1-40    # only these sentence numbers
  python tools/fetch_assets.py episodes/<ep> --go --limit 10     # at most 10 shots this run
  python tools/fetch_assets.py review episodes/<ep>              # contact sheet: assets/review.html
  python tools/fetch_assets.py prune episodes/<ep>               # drop files no shot uses (after edits)

Licences allowed, sources per visual_type and image width live in config/assets.yaml.
Every download is logged to assets/manifest.csv (licence, source URL, credit). Unknown licence = skipped.
Shots with no allowed file are listed in assets/misses.csv. Re-running only fetches shots still empty.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.assets import episode as ep_mod  # noqa: E402
from pipeline.assets.common import FetchError, Http  # noqa: E402


def parse_rows(spec: str | None) -> set[int] | None:
    if not spec:
        return None
    out = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out.update(range(int(a), int(b or a) + 1))
    return out


def cmd_search(args, cfg) -> int:
    http = Http(ep_mod.user_agent(cfg) if ep_mod.contact_of(cfg) else f"{cfg.get('bot_name', 'HistoryDocBot/0.1')} (search only)")
    s = ep_mod.Searcher(http, cfg)
    try:
        cands = s.run(args.source, args.query)
    except FetchError as e:
        print("ERROR", e)
        return 1
    for c in cands[: args.n]:
        ok = "OK  " if s.usable(c, args.source) else "SKIP"
        print(f"{ok} [{c.licence_class:8}] {c.licence_name[:22]:22} {c.width}x{c.height} {c.title[:70]}")
        print(f"     {c.page_url}")
    print(f"{len(cands)} results; OK = allowed by config/assets.yaml")
    return 0


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argv = list(sys.argv[1:] if argv is None else argv)
    cfg = ep_mod.load_config()
    if argv and argv[0] == "prune":
        gone = ep_mod.prune(Path(argv[1]))
        print(f"removed {len(gone)} unused assets: {' '.join(gone)}")
        return 0
    if argv and argv[0] == "review":
        from pipeline.assets import review
        out = review.build(Path(argv[1]), tuple(cfg.get("skip_visual_types", [])))
        print(f"wrote {out}")
        return 0
    if argv and argv[0] == "search":
        ap = argparse.ArgumentParser(prog="fetch_assets.py search")
        ap.add_argument("query")
        ap.add_argument("--source", default="commons",
                        choices=["commons", "commons_loc", "commons_nara", "commons_video", "ia", "ia_movies"])
        ap.add_argument("-n", type=int, default=10)
        return cmd_search(ap.parse_args(argv[1:]), cfg)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--go", action="store_true", help="search and download (default: plan only)")
    ap.add_argument("--rows", help="sentence numbers, e.g. 1-40,52")
    ap.add_argument("--limit", type=int, help="at most this many shots this run")
    a = ap.parse_args(argv)
    ep = Path(a.episode)
    if not (ep / "shotlist.csv").exists():
        print(f"{ep}: no shotlist.csv (run tools/shotlist.py init first)")
        return 2
    if a.go and not ep_mod.contact_of(cfg):
        print("ASSETS_CONTACT is not set in .env. Wikimedia requires contact information in the "
              "User-Agent of download scripts; ask the owner what to put there.")
        return 2
    s = ep_mod.fetch_episode(ep, cfg, go=a.go, only=parse_rows(a.rows), limit=a.limit)
    print(f"{ep.name}: {s['shots_to_fetch']} shots to fetch, {s['already_have']} already have an asset")
    if not a.go:
        print("plan only: add --go to search and download (free, no API keys)")
        return 0
    print(f"fetched {s['fetched']}, reused {s['reused']}, missed {s['missed']}, http calls {s.get('http_calls', 0)}")
    if s.get("stopped"):
        print(f"STOPPED: rate limited by the server; work so far is saved. Re-run later. ({s['stopped']})")
    if s["missed"]:
        print(f"misses listed in {ep / 'assets' / 'misses.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
