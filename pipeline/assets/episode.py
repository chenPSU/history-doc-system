"""Fill an episode's shot list with real assets (TASKS P3.2).

For every shot in shotlist.csv that has no asset_id yet (and is not a map, card or AI shot):
search the sources configured for its visual_type, keep only files whose licence is allowed,
download the first one not used elsewhere in the episode, log it to assets/manifest.csv and
write its id into the shot's asset_id slot. Shots with no allowed file go to assets/misses.csv.

The shot list and manifest are saved after each row, so an interrupted run can simply be re-run.
"""
from __future__ import annotations

import csv
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import archive_org, commons
from .common import Candidate, FetchError, Http, RateLimited, download, manifest_row, read_manifest, write_manifest
from .licence import allowed
from ..voice import load_env

ROOT = Path(__file__).resolve().parents[2]
NOISE = {"drone", "aerial", "close-up", "closeup", "detail", "dawn", "dusk", "night", "sunset", "sunrise",
         "view", "today", "modern", "present-day", "wide", "shot", "photo", "texture"}
STOP = {"a", "an", "the", "of", "at", "on", "in", "into", "to", "from", "by", "with", "and", "or", "for", "before",
        "after", "over", "under", "de", "la", "le", "les", "des", "du", "il", "di", "von", "der", "seen"}
GENERIC = {"painting", "engraving", "miniature", "manuscript", "portrait", "medieval", "old", "file", "jpg", "png",
           "tif", "image", "picture", "illustration", "print", "lithograph", "drawing", "photograph"}


def load_config(path: Path | None = None) -> dict:
    return yaml.safe_load(Path(path or ROOT / "config" / "assets.yaml").read_text(encoding="utf-8"))


def contact_of(cfg: dict) -> str:
    """config `contact`, else ASSETS_CONTACT from the environment / .env."""
    if (cfg.get("contact") or "").strip():
        return cfg["contact"].strip()
    load_env()
    return os.environ.get("ASSETS_CONTACT", "").strip()


def user_agent(cfg: dict) -> str:
    """Wikimedia User-Agent policy format: <name>/<version> (<contact>) <library>/<version>."""
    contact = contact_of(cfg)
    if not contact:
        raise ValueError("set ASSETS_CONTACT in .env (email, website or wiki user) before downloading; "
                         "Wikimedia blocks clients without contact information")
    return f"{cfg.get('bot_name', 'HistoryDocBot/0.1')} ({contact}) Python-urllib/{sys.version_info[0]}.{sys.version_info[1]}"


def split_cell(s: str | None) -> list[str]:
    return [x.strip() for x in (s or "").split("|")]


def query_variants(term: str) -> list[str]:
    """The term as written, then without camera words, then shorter: never below half the words (or 2),
    and never ending on a stop word ("... siege of")."""
    out = [term.strip()]
    words = [w for w in term.split() if w.lower().strip(",.") not in NOISE]
    floor = max(2, -(-len(words) // 2))
    while len(words) >= floor:
        while len(words) > 1 and words[-1].lower() in STOP:
            words = words[:-1]
        q = " ".join(words)
        if len(words) >= floor and q not in out:
            out.append(q)
        words = words[:-1]
    return out


def content_words(text: str) -> list[str]:
    """Lower-case words that carry meaning (no stop, camera or generic words), plural 's' stripped, in order."""
    out = []
    for w in re.findall(r"[^\W_]+", text.lower()):
        if len(w) < 3 or w in STOP or w in NOISE or w in GENERIC:
            continue
        w = w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
        if w not in out:
            out.append(w)
    return out


def relevant(c: Candidate, term: str, query: str) -> bool:
    """A file found with the full term is trusted (Commons matched every word). A file found with a
    shortened query must share 2 meaning words with the full term in its title, and not only the first
    two (usually the artist: 'Fausto Zonaro - Woman Playing a String Instrument' is not the fleet)."""
    if query.strip() == term.strip():
        return True
    tw = content_words(term)
    overlap = set(tw) & set(content_words(c.title))
    if len(overlap) < min(2, len(tw)):
        return False
    return len(tw) <= 3 or not overlap <= set(tw[:2])


class Searcher:
    """Runs a search on one named source; results are cached per (source, query) for the run."""

    def __init__(self, http: Http, cfg: dict):
        self.http, self.cfg, self.cache = http, cfg, {}

    def allowed_classes(self, source: str):
        return self.cfg.get("ia_allowed_licences", []) if source.startswith("ia") else self.cfg.get("allowed_licences", [])

    def run(self, source: str, query: str) -> list[Candidate]:
        key = (source, query)
        if key not in self.cache:
            self.cache[key] = self._run(source, query)
        return self.cache[key]

    def _run(self, source: str, query: str) -> list[Candidate]:
        lim, w = self.cfg.get("search_limit", 20), self.cfg.get("width", 3840)
        if source == "commons":
            return commons.search(self.http, query, lim, w)
        if source == "commons_loc":
            return commons.search(self.http, query, lim, w, extra='"Library of Congress"')
        if source == "commons_nara":
            return commons.search(self.http, query, lim, w, extra='"National Archives and Records Administration"')
        if source == "commons_video":
            return commons.search(self.http, query, lim, w, filetype="video")
        if source in ("ia", "ia_movies"):
            return archive_org.search(self.http, query, lim, "movies" if source == "ia_movies" else "image",
                                      allowed=self.allowed_classes(source))
        raise ValueError(f"unknown source {source!r}")

    def usable(self, c: Candidate, source: str) -> bool:
        if not c.download_url or not allowed(c.licence_class, self.allowed_classes(source)):
            return False
        return c.mime.startswith("video/") or not c.width or c.width >= self.cfg.get("min_width", 0)


@dataclass
class Pick:
    cand: Candidate | None
    query: str = ""
    source: str = ""
    reused: bool = False
    seen: set = field(default_factory=set)   # licence classes of rejected results, for the misses report


def pick(searcher: Searcher, term: str, visual_type: str, used, log=print, max_uses: int = 3) -> Pick:
    """`used`: asset id -> times already placed in the episode. A file is placed at most `max_uses` times."""
    seen, fallback = set(), None
    for source in searcher.cfg.get("routes", {}).get(visual_type, ["commons"]):
        for q in query_variants(term):
            try:
                cands = searcher.run(source, q)
            except RateLimited:
                raise
            except FetchError as e:
                log(f"    {source}: {e}")
                break
            ok = [c for c in cands if searcher.usable(c, source)]
            seen.update(c.licence_class for c in cands if c not in ok)
            if cands and not ok:
                continue
            ok = [c for c in ok if relevant(c, term, q)]
            if cands and not ok:
                seen.add("off-topic")
                continue
            for c in ok:
                if not used.get(c.asset_id):
                    return Pick(c, q, source, seen=seen)
            again = [c for c in ok if used.get(c.asset_id, 0) < max_uses]
            if again and fallback is None:
                fallback = Pick(again[0], q, source, reused=True)
            if ok:
                break   # this query found allowed files (all used already): don't broaden it
    if fallback:
        fallback.seen = seen
        return fallback
    return Pick(None, seen=seen)


@dataclass
class Task:
    row: int           # index in the shot list
    shot: int          # sub-shot index inside the row
    sentence_no: str
    visual_type: str
    term: str


def plan(rows: list[dict], cfg: dict, only: set[int] | None = None) -> tuple[list[Task], int]:
    tasks, have = [], 0
    skip = set(cfg.get("skip_visual_types", []))
    for i, r in enumerate(rows):
        if only and int(r["sentence_no"]) not in only:
            continue
        terms, vts, ids = split_cell(r.get("search_terms")), split_cell(r.get("visual_type")), split_cell(r.get("asset_id"))
        for j, term in enumerate(terms):
            vt = vts[j] if len(vts) > 1 and j < len(vts) else vts[0]
            if vt in skip or not term:
                continue
            if j < len(ids) and ids[j]:
                have += 1
                continue
            tasks.append(Task(i, j, r["sentence_no"], vt, term))
    return tasks, have


def _read_rows(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        return list(rd.fieldnames or []), list(rd)


def _write_rows(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def fetch_episode(ep: Path, cfg: dict, http: Http | None = None, go: bool = False, only: set[int] | None = None,
                  limit: int | None = None, log=print) -> dict:
    ep = Path(ep)
    fields, rows = _read_rows(ep / "shotlist.csv")
    tasks, have = plan(rows, cfg, only)
    if limit is not None:
        tasks = tasks[:limit]
    summary = {"shots_to_fetch": len(tasks), "already_have": have, "fetched": 0, "reused": 0, "missed": 0}
    if not go:
        return summary
    http = http or Http(user_agent(cfg))
    searcher = Searcher(http, cfg)
    mpath, assets_dir = ep / "assets" / "manifest.csv", ep / "assets"
    manifest = read_manifest(mpath)
    in_manifest = {m["asset_id"] for m in manifest}
    used = Counter(x for r in rows for x in split_cell(r.get("asset_id")) if x)
    max_uses = int(cfg.get("max_uses_per_asset", 3))
    misses = []
    for t in tasks:
        try:
            p = pick(searcher, t.term, t.visual_type, used, log, max_uses)
        except RateLimited as e:
            summary["stopped"] = str(e)
            break
        if p.cand is None:
            summary["missed"] += 1
            misses.append({"sentence_no": t.sentence_no, "shot": t.shot + 1, "visual_type": t.visual_type,
                           "search_terms": t.term, "licences_seen": " ".join(sorted(p.seen)) or "no results"})
            log(f"  #{t.sentence_no}.{t.shot + 1} MISS  {t.term!r} (seen: {', '.join(sorted(p.seen)) or 'nothing'})")
            continue
        try:
            path = download(http, p.cand, assets_dir)
        except RateLimited as e:
            summary["stopped"] = str(e)
            break
        except FetchError as e:
            summary["missed"] += 1
            misses.append({"sentence_no": t.sentence_no, "shot": t.shot + 1, "visual_type": t.visual_type,
                           "search_terms": t.term, "licences_seen": f"download failed: {e}"[:200]})
            log(f"  #{t.sentence_no}.{t.shot + 1} FAIL  {e}")
            continue
        if p.cand.asset_id not in in_manifest:
            manifest.append(manifest_row(p.cand, f"assets/{path.name}", p.query))
            in_manifest.add(p.cand.asset_id)
            write_manifest(mpath, manifest)
        used[p.cand.asset_id] += 1
        r = rows[t.row]
        n_shots = len(split_cell(r.get("search_terms")))
        ids = (split_cell(r.get("asset_id")) + [""] * n_shots)[:n_shots]
        ids[t.shot] = p.cand.asset_id
        r["asset_id"] = " | ".join(ids) if n_shots > 1 else ids[0]
        _write_rows(ep / "shotlist.csv", fields, rows)
        summary["reused" if p.reused else "fetched"] += 1
        log(f"  #{t.sentence_no}.{t.shot + 1} {'REUSE' if p.reused else 'OK   '} {p.cand.asset_id} "
            f"[{p.cand.licence_name}] {p.cand.title[:60]}")
    miss_file = assets_dir / "misses.csv"
    miss_file.unlink(missing_ok=True)
    if misses:
        with miss_file.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(misses[0]))
            w.writeheader()
            w.writerows(misses)
    summary["http_calls"] = http.calls
    return summary
