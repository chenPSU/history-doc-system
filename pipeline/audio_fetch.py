"""Fetch licence-checked audio (music beds, sound effects) from Wikimedia Commons by exact file title (TASKS P2.3).

Each file lands in audio/lib/ of the episode and gets a row in assets/manifest.csv (rights gate), like images do.
Titles are chosen by hand (search with `tools/fetch_assets.py search "<q>"`): sound needs listening, not keywords.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from pipeline.assets.common import Http, read_manifest, write_manifest
from pipeline.assets.licence import allowed, classify

API = "https://commons.wikimedia.org/w/api.php"


def info(http: Http, title: str) -> dict:
    d = http.json(API, {"action": "query", "format": "json", "titles": title, "prop": "imageinfo",
                        "iiprop": "url|mime|size|extmetadata"})
    page = next(iter(d["query"]["pages"].values()))
    if "imageinfo" not in page:
        raise ValueError(f"not on Commons: {title}")
    ii = page["imageinfo"][0]
    meta = ii.get("extmetadata", {})
    val = lambda k: (meta.get(k) or {}).get("value", "")
    import re
    artist = re.sub(r"<[^>]+>", "", val("Artist")).strip() or "unknown"
    lic = val("LicenseShortName") or val("License")
    return {"pageid": page["pageid"], "url": ii["url"], "page": ii["descriptionurl"], "mime": ii.get("mime", ""),
            "licence": lic, "class": classify(f"{lic} {val('License')} {val('UsageTerms')}"),
            "credit": f"{artist}, {lic}, via Wikimedia Commons"}


def fetch(ep: Path, titles: dict[str, str], http: Http, allowed_classes, log=print) -> dict[str, str]:
    """titles: {role: "File:..."}. Returns {role: asset_id}. Already fetched files are not downloaded again."""
    ep = Path(ep)
    mpath = ep / "assets" / "manifest.csv"
    rows = read_manifest(mpath)
    have = {r["asset_id"]: r for r in rows}
    out = {}
    for role, title in titles.items():
        i = info(http, title)
        aid = f"wm-{i['pageid']}"
        out[role] = aid
        if not allowed(i["class"], allowed_classes):
            raise ValueError(f"{title}: licence {i['licence']!r} ({i['class']}) not allowed")
        ext = Path(urlparse(i["url"]).path).suffix.lower()   # the URL carries a query string
        rel = f"audio/lib/{aid}{ext}"
        if aid in have and (ep / have[aid]["file"]).exists():
            continue
        data = http.get(i["url"])
        (ep / rel).parent.mkdir(parents=True, exist_ok=True)
        (ep / rel).write_bytes(data)
        rows = [r for r in read_manifest(mpath) if r["asset_id"] != aid]   # re-read: other stages write this file too
        rows.append({"asset_id": aid, "file": rel, "source": "commons", "source_url": i["page"], "licence": i["licence"],
                     "credit": i["credit"], "ai_generated": "n",
                     "notes": f"class={i['class']}; kind=audio; role={role}; title={title[5:120]}"})
        write_manifest(mpath, rows)
        log(f"{role}: {rel} [{i['licence']}] {len(data) // 1024} KB")
    return out
