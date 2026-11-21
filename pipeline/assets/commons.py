"""Wikimedia Commons search (MediaWiki API, no key needed)."""
from __future__ import annotations

from .common import Candidate, Http, strip_html
from .licence import classify

API = "https://commons.wikimedia.org/w/api.php"
META = "License|LicenseShortName|LicenseUrl|Artist|Credit|AttributionRequired|Restrictions|ObjectName"


def search(http: Http, query: str, limit: int = 20, width: int = 3840, filetype: str = "bitmap",
           extra: str = "") -> list[Candidate]:
    """Files matching `query`, best match first. filetype: bitmap | video. extra: added search words,
    e.g. '"Library of Congress"' to find LOC scans mirrored on Commons."""
    q = " ".join(x for x in (query, extra, f"filetype:{filetype}") if x)
    data = http.json(API, {"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                           "gsrlimit": limit, "gsrsearch": q, "prop": "imageinfo",
                           "iiprop": "url|size|mime|extmetadata", "iiurlwidth": width,
                           "iiextmetadatafilter": META})
    pages = sorted((data.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    out = []
    for p in pages:
        if not p.get("imageinfo"):
            continue
        ii = p["imageinfo"][0]
        m = {k: (v or {}).get("value", "") for k, v in (ii.get("extmetadata") or {}).items()}
        cls = classify(m.get("License"))
        if cls == "unknown":
            cls = classify(m.get("LicenseShortName"))
        name = strip_html(m.get("LicenseShortName")) or m.get("License", "")
        artist = strip_html(m.get("Artist"), 120) or strip_html(m.get("Credit"), 120) or "Unknown author"
        video = ii.get("mime", "").startswith("video/")
        url = ii.get("url") if video else (ii.get("thumburl") or ii.get("url"))
        notes = []
        if m.get("Restrictions"):
            notes.append(f"restrictions={strip_html(m['Restrictions'], 80)}")
        out.append(Candidate(
            source="commons", source_id=str(p["pageid"]), title=p.get("title", ""),
            page_url=ii.get("descriptionurl", ""), download_url=url or "",
            licence_class=cls, licence_name=name, licence_url=m.get("LicenseUrl", ""),
            credit=f"{artist}, {name}, via Wikimedia Commons", mime=ii.get("mime", ""),
            width=int(ii.get("width") or 0), height=int(ii.get("height") or 0), notes=notes))
    return out
