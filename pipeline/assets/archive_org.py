"""Internet Archive search (advancedsearch + metadata API, no key needed).

Only items that state a licence URL are considered. That licence is declared by the uploader, so the
manifest notes say so; config/assets.yaml keeps IA to pd/cc0 by default.
"""
from __future__ import annotations

from urllib.parse import quote

from .common import Candidate, Http, strip_html
from .licence import classify

SEARCH = "https://archive.org/advancedsearch.php"
IMAGE_FORMATS = ("JPEG", "PNG", "TIFF", "JPEG 2000")
VIDEO_FORMATS = ("MPEG4", "h.264", "h.264 IA", "512Kb MPEG4")


def search(http: Http, query: str, limit: int = 20, mediatype: str = "image", allowed=None) -> list[Candidate]:
    """Items matching `query`. The extra metadata call (to find the file) is made only for items whose
    licence class is in `allowed` (all items when allowed is None)."""
    params = [("q", f"({query}) AND mediatype:{mediatype} AND licenseurl:*"), ("fl[]", "identifier"),
              ("fl[]", "title"), ("fl[]", "licenseurl"), ("fl[]", "creator"), ("rows", limit), ("output", "json")]
    data = http.json(SEARCH, params)  # a list of pairs: urlencode repeats fl[]
    out = []
    for d in (data.get("response") or {}).get("docs", []):
        ident = d.get("identifier", "")
        cls = classify(d.get("licenseurl"))
        creator = d.get("creator") or "Unknown"
        creator = ", ".join(creator) if isinstance(creator, list) else creator
        cand = Candidate(source="ia", source_id=ident, title=strip_html(str(d.get("title", ""))),
                         page_url=f"https://archive.org/details/{ident}", download_url="",
                         licence_class=cls, licence_name=d.get("licenseurl", ""), licence_url=d.get("licenseurl", ""),
                         credit=f"{strip_html(creator, 120)}, via Internet Archive",
                         notes=["licence declared by the uploader: check the item page"])
        if allowed is None or cls in allowed:
            pick = pick_file(http, ident, mediatype)
            if not pick:
                continue
            cand.download_url, cand.mime = pick
        out.append(cand)
    return out


def pick_file(http: Http, ident: str, mediatype: str) -> tuple[str, str] | None:
    meta = http.json(f"https://archive.org/metadata/{ident}")
    formats = VIDEO_FORMATS if mediatype == "movies" else IMAGE_FORMATS
    files = [f for f in meta.get("files", []) if f.get("format") in formats and "thumb" not in f.get("name", "").lower()]
    if not files:
        return None
    best = max(files, key=lambda f: int(f.get("size") or 0))
    mime = "video/mp4" if mediatype == "movies" else {"PNG": "image/png", "TIFF": "image/tiff"}.get(best["format"], "image/jpeg")
    return f"https://archive.org/download/{ident}/{quote(best['name'])}", mime
