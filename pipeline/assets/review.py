"""A contact sheet to check fetched assets by eye: assets/review.html (open it in a browser).

One card per shot: sentence, search terms, the picked image, its licence, credit and source link.
Shots without an asset (misses) are marked; maps, cards and AI shots are listed as "made by us".
"""
from __future__ import annotations

import csv
import html
from pathlib import Path

from .common import read_manifest
from .episode import split_cell

CSS = """
:root{--bg:#f6f4ef;--card:#fff;--ink:#222;--mute:#666;--miss:#b3261e;--ok:#1b6e3a;--line:#ddd}
@media (prefers-color-scheme:dark){:root{--bg:#16171a;--card:#212328;--ink:#eee;--mute:#aaa;--miss:#ff8a80;--ok:#7bd88f;--line:#333}}
body{margin:0;padding:16px;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,sans-serif}
h1{font-size:20px;margin:0 0 4px} .sum{color:var(--mute);margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.c{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px}
.c img{width:100%;aspect-ratio:16/9;object-fit:contain;background:#000;border-radius:4px}
.n{font-weight:600} .s{margin:4px 0} .t{color:var(--mute);font-size:12px}
.miss{color:var(--miss);font-weight:600} .lic{color:var(--ok);font-size:12px} a{color:inherit}
.own{color:var(--mute);font-style:italic}
"""


def build(ep: Path, skip_types=("map", "card", "illustration_ai")) -> Path:
    ep = Path(ep)
    with (ep / "shotlist.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    man = {m["asset_id"]: m for m in read_manifest(ep / "assets" / "manifest.csv")}
    cards, n_ok, n_miss, n_own = [], 0, 0, 0
    for r in rows:
        terms, vts, ids = split_cell(r["search_terms"]), split_cell(r["visual_type"]), split_cell(r.get("asset_id"))
        for j, term in enumerate(terms):
            vt = vts[j] if len(vts) > 1 and j < len(vts) else vts[0]
            aid = ids[j] if j < len(ids) else ""
            head = (f'<div class="n">#{r["sentence_no"]}.{j + 1} · {html.escape(vt)}</div>'
                    f'<div class="s">{html.escape(r["sentence"])}</div><div class="t">{html.escape(term)}</div>')
            if vt in skip_types:
                n_own += 1
                body = '<div class="own">made by us (map / card / illustration)</div>'
            elif aid and aid in man:
                n_ok += 1
                m = man[aid]
                body = (f'<img loading="lazy" src="{html.escape(Path(m["file"]).name)}" alt="">'
                        f'<div class="lic">{html.escape(m["licence"])} · {html.escape(aid)}</div>'
                        f'<div class="t">{html.escape(m["credit"])} · <a href="{html.escape(m["source_url"])}">source</a></div>')
            else:
                n_miss += 1
                body = '<div class="miss">no asset yet</div>'
            cards.append(f'<div class="c">{head}{body}</div>')
    out = ep / "assets" / "review.html"
    out.write_text(f'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                   f'<title>Asset review</title><style>{CSS}</style><h1>{html.escape(ep.name)}: asset review</h1>'
                   f'<div class="sum">{n_ok} shots with an asset · {n_miss} without · {n_own} made by us</div>'
                   f'<div class="grid">{"".join(cards)}</div>', encoding="utf-8")
    return out
