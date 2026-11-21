"""Shared pieces for the asset fetchers: HTTP with polite retries, the Candidate record, downloads, manifest."""
from __future__ import annotations

import csv
import html
import http.client
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

MANIFEST_COLUMNS = ["asset_id", "file", "source", "source_url", "licence", "credit", "ai_generated", "notes"]
EXT_BY_MIME = {"image/jpeg": ".jpg", "image/png": ".png", "image/tiff": ".tif", "image/gif": ".gif",
               "image/webp": ".webp", "video/mp4": ".mp4", "video/webm": ".webm", "video/ogg": ".ogv"}


class FetchError(RuntimeError):
    pass


class RateLimited(FetchError):
    """The server asked us to slow down for longer than we are willing to wait: stop the run."""


def _urlopen_bytes(url: str, headers: dict, timeout: float = 60) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


class Http:
    """GET with a fixed User-Agent, a pause between calls, and backoff on 429/5xx.

    `fetch(url, headers) -> bytes` is injectable for tests. A bot-check page (HTTP 403 with HTML) is
    reported as FetchError and never retried or worked around.
    """

    def __init__(self, user_agent: str, fetch=_urlopen_bytes, sleep=time.sleep, delay: float = 1.0, tries: int = 4,
                 max_wait: float = 30.0):
        self.headers = {"User-Agent": user_agent}
        self.fetch, self.sleep, self.delay, self.tries, self.max_wait = fetch, sleep, delay, tries, max_wait
        self.calls = 0

    def get(self, url: str, params: dict | None = None) -> bytes:
        if params:
            url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        wait = 2.0
        for attempt in range(1, self.tries + 1):
            if self.calls:
                self.sleep(self.delay)
            self.calls += 1
            try:
                return self.fetch(url, self.headers)
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:
                    retry_after = e.headers.get("Retry-After") if e.headers else None
                    pause = float(retry_after) if retry_after and retry_after.isdigit() else wait
                    if e.code == 429 and (pause > self.max_wait or attempt == self.tries):
                        raise RateLimited(f"HTTP 429 (asked to wait {pause:.0f}s): {url}") from e
                    if attempt == self.tries:
                        raise FetchError(f"HTTP {e.code} after {attempt} tries: {url}") from e
                    self.sleep(pause)
                    wait *= 2
                    continue
                raise FetchError(f"HTTP {e.code}: {url}") from e
            except (urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError) as e:
                if attempt == self.tries:
                    raise FetchError(f"network error: {getattr(e, 'reason', e)!s:.120}: {url}") from e
                self.sleep(wait)
                wait *= 2
        raise FetchError(f"gave up: {url}")

    def json(self, url: str, params: dict | None = None):
        body = self.get(url, params)
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise FetchError(f"not JSON (bot check or error page?): {url}") from e


def strip_html(s: str | None, limit: int = 200) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", html.unescape(s)).strip()
    return s[:limit]


@dataclass
class Candidate:
    source: str          # commons | ia
    source_id: str       # Commons page id, IA identifier
    title: str
    page_url: str        # human page that shows the licence (goes to manifest source_url)
    download_url: str
    licence_class: str   # see licence.classify
    licence_name: str    # as the source states it, e.g. "CC BY 4.0", "Public domain"
    licence_url: str = ""
    credit: str = ""
    mime: str = ""
    width: int = 0
    height: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def asset_id(self) -> str:
        prefix = {"commons": "wm", "ia": "ia"}.get(self.source, self.source)
        return f"{prefix}-{re.sub(r'[^A-Za-z0-9_.-]+', '-', self.source_id)}"[:80]

    def extension(self) -> str:
        path = urllib.parse.unquote(urllib.parse.urlparse(self.download_url).path).lower()
        ext = Path(path).suffix
        if ext == ".jpeg":
            ext = ".jpg"
        return ext or EXT_BY_MIME.get(self.mime, ".bin")


def download(http: Http, cand: Candidate, assets_dir: Path) -> Path:
    assets_dir.mkdir(parents=True, exist_ok=True)
    dest = assets_dir / f"{cand.asset_id}{cand.extension()}"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    data = http.get(cand.download_url)
    if len(data) < 1000 or data[:15].lower().startswith((b"<!doctype", b"<html")):
        raise FetchError(f"download is not a media file: {cand.download_url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(dest)
    return dest


def read_manifest(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_manifest(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def manifest_row(cand: Candidate, file_rel: str, query: str) -> dict:
    notes = [f"class={cand.licence_class}"]
    if cand.licence_url:
        notes.append(f"licence_url={cand.licence_url}")
    notes.append(f"query={query}")
    notes.append(f"title={cand.title[:120]}")
    notes += cand.notes
    return {"asset_id": cand.asset_id, "file": file_rel, "source": cand.source, "source_url": cand.page_url,
            "licence": cand.licence_name, "credit": cand.credit, "ai_generated": "n",
            "notes": "; ".join(n.replace(";", ",") for n in notes)}
