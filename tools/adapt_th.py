#!/usr/bin/env python3
"""Start a Thai episode from an English one (TASKS P1.6, the Thai adaptation step).

  python tools/adapt_th.py episodes/2026-12-14-en-constantinople --date 2026-12-14 --title "..."

Creates episodes/<date>-th-<slug>/ (never overwrites) with:
- brief.yaml   from the English brief: same cluster, hook, key visual; language th, the Thai sign-off,
               `source_episode:` pointing at the English folder (the Thai episode reuses its visuals and maps);
- factsheet.md the English fact sheet plus a `## Thai additions` section for Thai-only facts
               (Buddhist-era years, Thai time anchors, unit conversions), each with 2 sources like the rest;
- script.md    a skeleton: Thai headers (CAST:/PLACES: filled from data/th_names.yaml for every name the English
               script uses), the English sections and cues in place, and no narration. The writer then adapts
               the narration line by line with the history-doc-episode skill (section "Thai adaptation").
Then: python tools/score.py episodes/<th-ep>/script.md --rounds 1,2,3,4,5   (the Thai scorer, P1.5)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import new_episode  # noqa: E402

TH_SIGNOFF = "จนกว่าจะพบกันใหม่ อย่าลืมมองย้อนกลับไป"
NAMES = ROOT / "data" / "th_names.yaml"


def used_names(en_script: str, names_path: Path = NAMES) -> tuple[list[str], list[str]]:
    g = yaml.safe_load(names_path.read_text(encoding="utf-8")) or {}
    narration = "\n".join(l for l in en_script.splitlines() if l.strip() and not l.lstrip().startswith(("[", "#")))

    def pick(rows):
        out = []
        for r in rows or []:
            if re.search(rf"\b{re.escape(r['en'])}\b", narration) and r["th"] not in out:
                out.append(r["th"])
        return out
    return pick(g.get("people")), pick(g.get("places"))


def skeleton(en_script: str, title: str, thumb: str, cast: list[str], places: list[str]) -> str:
    out = [f"TITLE: {title}", f"THUMB: {thumb}", f"SIGNOFF: {TH_SIGNOFF}",
           f"CAST: {', '.join(cast)}", f"PLACES: {', '.join(places)}"]
    for line in en_script.splitlines():
        s = line.strip()
        if s.startswith("## "):
            out += ["", s]
        elif s.startswith("["):
            out.append(s)
    out.append(TH_SIGNOFF)
    return "\n".join(out) + "\n"


def adapt(en_ep: Path, date: str, title: str, thumb: str = "", slug: str | None = None, root: Path | None = None) -> Path:
    en_ep = Path(en_ep)
    brief = yaml.safe_load((en_ep / "brief.yaml").read_text(encoding="utf-8")) or {}
    slug = slug or brief.get("slug") or en_ep.name.split("-en-", 1)[-1]
    dest, created = new_episode.create(date, "th", slug, title, str(brief.get("cluster", 0)), "false",
                                       brief.get("hook_paradox", ""), brief.get("key_visual", ""),
                                       root=root or new_episode.EPISODES)
    if not created:
        raise SystemExit(f"{dest} already exists; not overwritten")
    b = yaml.safe_load((dest / "brief.yaml").read_text(encoding="utf-8")) or {}
    b.update({"signoff": TH_SIGNOFF, "source_episode": en_ep.name, "title_formula": brief.get("title_formula", ""),
              "next_episode_tease": "", "status": "factsheet"})
    (dest / "brief.yaml").write_text("# Thai episode adapted from the English one (tools/adapt_th.py, TASKS P1.6).\n"
                                     + yaml.safe_dump(b, allow_unicode=True, sort_keys=False), encoding="utf-8")
    fs = (en_ep / "factsheet.md").read_text(encoding="utf-8")
    (dest / "factsheet.md").write_text(
        fs.rstrip() + f"\n\n## Thai additions\n\nShared with `{en_ep.name}`: every fact above holds for the Thai script. "
        "Facts only the Thai script uses (Buddhist-era years, Thai time anchors, unit conversions):\n\n"
        "| # | Fact | Value used in script | Source 1 | Source 2 | Checked | Disputed? |\n|---|---|---|---|---|---|---|\n",
        encoding="utf-8")
    en_script = (en_ep / "script.md").read_text(encoding="utf-8")
    cast, places = used_names(en_script)
    (dest / "script.md").write_text(skeleton(en_script, title, thumb, cast, places), encoding="utf-8")
    return dest


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("en_episode")
    ap.add_argument("--date", required=True, help="Thai publish week, YYYY-MM-DD")
    ap.add_argument("--title", required=True, help="Thai title (proper name + years)")
    ap.add_argument("--thumb", default="")
    ap.add_argument("--slug")
    a = ap.parse_args(argv)
    dest = adapt(Path(a.en_episode), a.date, a.title, a.thumb, a.slug)
    print(f"created {dest}: brief, factsheet (+ Thai additions), script skeleton. Write the Thai narration next.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
