#!/usr/bin/env python3
"""Create episode folders from templates/episode/.

One episode:
  python tools/new_episode.py --date 2026-12-07 --lang en --slug korea --title "The Entire History of Korea"
All Phase-1 episodes (EN + TH) from data/episodes.csv:
  python tools/new_episode.py --from-csv data/episodes.csv
Existing folders are never overwritten.
"""
import argparse
import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "episode"
EPISODES = ROOT / "episodes"
FILLED = {"brief.yaml", "factsheet.md", "script.md"}


def yaml_str(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


def create(date, lang, slug, title, cluster="0", th_only="false", hook="", key_visual="", root=EPISODES):
    if lang not in ("en", "th"):
        raise ValueError("lang must be en or th")
    dest = Path(root) / f"{date}-{lang}-{slug}"
    if dest.exists():
        return dest, False
    shutil.copytree(TEMPLATE, dest)
    values = {"date": date, "lang": lang, "slug": slug, "title": yaml_str(title), "cluster": cluster or "0",
              "th_only": th_only, "hook": yaml_str(hook), "key_visual": yaml_str(key_visual)}
    for name in FILLED:
        p = dest / name
        text = p.read_text(encoding="utf-8")
        for k, v in values.items():
            text = text.replace("{" + k + "}", str(v))
        p.write_text(text, encoding="utf-8")
    return dest, True


def from_csv(path, root=EPISODES):
    made = []
    for r in csv.DictReader(open(path, encoding="utf-8")):
        th_only = r["th_only"].strip().lower() == "yes"  # TH episode has its own topic; the EN episode still exists
        made.append(create(r["week_start"], "en", r["en_slug"], r["en_title"], r["en_cluster"], "false",
                           r["en_hook_th"], r["en_key_visual_th"], root))
        made.append(create(r["week_start"], "th", r["th_slug"], r["th_title"], r["th_cluster"],
                           "true" if th_only else "false", r["th_hook_th"], r["th_key_visual_th"], root))
    return made


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-csv")
    ap.add_argument("--date")
    ap.add_argument("--lang", choices=["en", "th"])
    ap.add_argument("--slug")
    ap.add_argument("--title", default="")
    ap.add_argument("--cluster", default="0")
    a = ap.parse_args(argv)
    if a.from_csv:
        res = from_csv(a.from_csv)
    elif a.date and a.lang and a.slug:
        res = [create(a.date, a.lang, a.slug, a.title, a.cluster)]
    else:
        ap.error("give --from-csv, or --date --lang --slug")
    for dest, new in res:
        print(("created " if new else "exists  ") + str(dest.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
