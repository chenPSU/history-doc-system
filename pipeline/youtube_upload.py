"""YouTube upload stage.

Reads an episode folder (metadata.yaml, brief.yaml, score.json, approved.yaml, render files) and the owner's
config/upload_policy.yaml, checks every gate, then uploads with the YouTube Data API v3:
videos.insert (resumable) -> thumbnails.set -> captions.insert -> playlistItems.insert.
The result is written to <episode>/upload.json, so a second run never uploads twice.

Google client libraries are imported lazily: the gate and request-building logic is testable without them.
"""
from __future__ import annotations

import datetime as dt
import json
import random
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "config" / "upload_policy.yaml"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",  # thumbnails, captions, playlists, channel check
]
RETRY_STATUS = {500, 502, 503, 504}
MAX_RETRIES = 8
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class GateError(Exception):
    """Raised when an episode is not allowed to upload. .failures lists the reasons."""

    def __init__(self, failures):
        super().__init__("; ".join(failures))
        self.failures = failures


# ---------------------------------------------------------------- loading
def load_yaml(path: Path, default=None):
    if not path.exists():
        return default
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_policy(path: Path = POLICY_PATH) -> dict:
    p = load_yaml(Path(path), {})
    p.setdefault("mode", "private")
    p.setdefault("audit_passed", False)
    p.setdefault("require_owner_approval", True)
    p.setdefault("review_window_hours", 24)
    p.setdefault("max_uploads_per_day", 4)
    p.setdefault("channels", {})
    return p


def effective_mode(policy: dict) -> tuple[str, list[str]]:
    """The mode that will really be used, plus warnings."""
    mode, warns = policy["mode"], []
    if mode not in ("off", "private", "scheduled", "public"):
        raise ValueError(f"unknown upload mode: {mode}")
    if mode in ("scheduled", "public") and not policy.get("audit_passed"):
        warns.append("audit_passed is false: YouTube locks API uploads to private, so this upload stays private.")
        mode = "private"
    return mode, warns


# ---------------------------------------------------------------- gates
def check_gates(ep: Path, policy: dict) -> list[str]:
    ep = Path(ep)
    f = []
    brief = load_yaml(ep / "brief.yaml", {})
    meta = load_yaml(ep / "metadata.yaml", {})
    lang = brief.get("language")
    if policy["mode"] == "off":
        f.append("upload mode is off")
    if not policy.get("audit_passed") and not brief.get("test_upload"):
        f.append("API audit not passed: YouTube would lock this video to private (reported as permanent). "
                 "Upload it by hand in YouTube Studio, or set test_upload: true in brief.yaml for a test video.")
    if lang not in policy.get("channels", {}):
        f.append(f"no channel configured for language {lang!r}")
    elif not policy["channels"][lang].get("channel_id"):
        f.append(f"channel_id for {lang} is empty: run tools/auth_youtube.py --lang {lang}")
    if (load_json(ep / "upload.json") or {}).get("video_id"):
        f.append("already uploaded (upload.json has a video_id)")
    # quality gates
    score = load_json(ep / "score.json")
    if not score or not score.get("gate_passed"):
        f.append("score gate not passed (score.json missing or gate_passed false)")
    pre = load_json(ep / "preflight.json")
    if not pre or not pre.get("passed"):
        f.append("preflight not passed (preflight.json missing or passed false)")
    if policy.get("require_owner_approval"):
        appr = load_yaml(ep / "approved.yaml", {})
        if not appr.get("approved_by") or not appr.get("approved_at"):
            f.append("owner approval missing (approved.yaml needs approved_by and approved_at)")
    # rights gate
    man = ep / "assets" / "manifest.csv"
    if man.exists():
        import csv
        rows = list(csv.DictReader(man.open(encoding="utf-8")))
        bad = [r.get("asset_id", "?") for r in rows if not (r.get("licence") and r.get("source_url"))]
        if bad:
            f.append(f"assets without licence/source: {', '.join(bad[:5])}")
    else:
        f.append("assets/manifest.csv missing")
    # metadata
    title = (meta.get("title") or "").strip()
    if not title:
        f.append("metadata title empty")
    if len(title) > 100:
        f.append("title over 100 characters")
    if "<" in title or ">" in title:
        f.append("title contains < or >")
    if len(build_description(meta).encode("utf-8")) > 5000:
        f.append("description over 5000 bytes")
    if len(",".join(meta.get("tags") or [])) > 500:
        f.append("tags over 500 characters")
    for key in ("video_file",):
        p = ep / (meta.get(key) or "")
        if not meta.get(key) or not p.is_file():
            f.append(f"{key} not found")
    return f


# ---------------------------------------------------------------- request body
def build_description(meta: dict) -> str:
    parts = [(meta.get("description") or "").strip()]
    ch = meta.get("chapters") or []
    if ch:
        parts.append("\n".join(f"{c['time']} {c['title']}" for c in ch))
    if meta.get("sources"):
        parts.append("Sources:\n" + "\n".join(f"- {s}" for s in meta["sources"]))
    if meta.get("footage_credits"):
        parts.append("Footage and images:\n" + "\n".join(f"- {s}" for s in meta["footage_credits"]))
    if meta.get("altered_or_synthetic_disclosure"):
        parts.append("Some illustrations in this video were created with AI.")
    return "\n\n".join(p for p in parts if p)


def next_publish_slot(slots: list[str], after: dt.datetime, taken: set[dt.datetime] = frozenset()) -> dt.datetime:
    """Next 'Ddd HH:MM' UTC slot strictly after `after` that is not taken."""
    parsed = []
    for s in slots:
        day, hm = s.split()
        h, m = (int(x) for x in hm.split(":"))
        parsed.append((DAYS.index(day), h, m))
    if not parsed:
        raise ValueError("no publish_slots_utc configured")
    base = after.replace(second=0, microsecond=0)
    for d in range(0, 7 * 8):
        day = (base + dt.timedelta(days=d)).date()
        for wd, h, m in sorted(parsed, key=lambda x: (x[1], x[2])):
            if day.weekday() != wd:
                continue
            cand = dt.datetime(day.year, day.month, day.day, h, m, tzinfo=dt.timezone.utc)
            if cand > after and cand not in taken:
                return cand
    raise ValueError("no free slot in the next 8 weeks")


def build_body(meta: dict, brief: dict, channel: dict, mode: str, publish_at: dt.datetime | None) -> dict:
    status = {
        "privacyStatus": "public" if mode == "public" else "private",
        "selfDeclaredMadeForKids": bool(meta.get("made_for_kids", False)),
        "containsSyntheticMedia": bool(meta.get("altered_or_synthetic_disclosure", False)),
        "embeddable": True,
        "license": "youtube",
    }
    if mode == "scheduled":
        status["publishAt"] = publish_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    lang = channel.get("default_language") or brief.get("language")
    return {
        "snippet": {
            "title": meta["title"].strip(),
            "description": build_description(meta),
            "tags": meta.get("tags") or [],
            "categoryId": str(channel.get("category_id", "27")),
            "defaultLanguage": lang,
            "defaultAudioLanguage": lang,
        },
        "status": status,
    }


# ---------------------------------------------------------------- API helpers
def get_service(channel: dict):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token = ROOT / channel["token"]
    if not token.exists():
        raise RuntimeError(f"no token at {token}: run tools/auth_youtube.py first")
    creds = Credentials.from_authorized_user_file(str(token), SCOPES)
    if not creds.valid:
        creds.refresh(Request())
        token.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def channel_id_of(service) -> str:
    items = service.channels().list(part="id,snippet", mine=True).execute().get("items", [])
    if len(items) != 1:
        raise RuntimeError("token does not resolve to exactly one channel")
    return items[0]["id"]


def _media(path: Path, mimetype: str, resumable: bool = True):
    from googleapiclient.http import MediaFileUpload
    return MediaFileUpload(str(path), mimetype=mimetype, chunksize=8 * 1024 * 1024, resumable=resumable)


def resumable_insert(request, sleep=time.sleep, log=print) -> dict:
    """Drive a resumable upload with exponential backoff on transient errors."""
    response, retry = None, 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                log(f"  uploaded {int(status.progress() * 100)}%")
        except Exception as e:  # googleapiclient.errors.HttpError or connection errors
            code = getattr(getattr(e, "resp", None), "status", None)
            transient = code in RETRY_STATUS or code is None
            if not transient or retry >= MAX_RETRIES:
                raise
            retry += 1
            wait = min(64, 2 ** retry) * random.random()
            log(f"  transient error ({code}); retry {retry} in {wait:.1f}s")
            sleep(wait)
    return response


# ---------------------------------------------------------------- main entry
def uploads_today(channel_lang: str, episodes_dir: Path, now: dt.datetime) -> int:
    n = 0
    for up in Path(episodes_dir).glob("*/upload.json"):
        d = json.loads(up.read_text())
        if d.get("lang") == channel_lang and d.get("uploaded_at", "")[:10] == now.strftime("%Y-%m-%d"):
            n += 1
    return n


def taken_slots(channel_lang: str, episodes_dir: Path) -> set[dt.datetime]:
    out = set()
    for up in Path(episodes_dir).glob("*/upload.json"):
        d = json.loads(up.read_text())
        if d.get("lang") == channel_lang and d.get("publish_at"):
            out.add(dt.datetime.strptime(d["publish_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc))
    return out


def upload_episode(ep: Path, policy: dict | None = None, go: bool = False, service=None, make_media=_media,
                   now: dt.datetime | None = None, log=print) -> dict:
    ep = Path(ep)
    policy = policy or load_policy()
    now = now or dt.datetime.now(dt.timezone.utc)
    failures = check_gates(ep, policy)
    if failures:
        raise GateError(failures)
    mode, warns = effective_mode(policy)
    for w in warns:
        log("WARNING: " + w)
    brief, meta = load_yaml(ep / "brief.yaml", {}), load_yaml(ep / "metadata.yaml", {})
    lang = brief["language"]
    channel = policy["channels"][lang]
    episodes_dir = ep.parent
    if uploads_today(lang, episodes_dir, now) >= policy["max_uploads_per_day"]:
        raise GateError([f"max_uploads_per_day reached for {lang}"])
    publish_at = None
    if mode == "scheduled":
        earliest = now + dt.timedelta(hours=policy["review_window_hours"])
        publish_at = next_publish_slot(channel.get("publish_slots_utc", []), earliest, taken_slots(lang, episodes_dir))
    body = build_body(meta, brief, channel, mode, publish_at)
    plan = {"episode": ep.name, "lang": lang, "mode": mode, "warnings": warns, "body": body,
            "publish_at": body["status"].get("publishAt")}
    if not go:
        log("DRY RUN (add --go to upload):\n" + json.dumps(plan, ensure_ascii=False, indent=1))
        return plan

    service = service or get_service(channel)
    actual = channel_id_of(service)
    if actual != channel["channel_id"]:
        raise GateError([f"token is for channel {actual}, policy expects {channel['channel_id']} ({lang})"])

    log(f"Uploading {ep.name} to {lang} channel as {mode}...")
    req = service.videos().insert(part="snippet,status", body=body,
                                  media_body=make_media(ep / meta["video_file"], "video/*"))
    resp = resumable_insert(req, log=log)
    vid = resp["id"]
    result = {**plan, "video_id": vid, "uploaded_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
              "url": f"https://youtu.be/{vid}", "steps": {"insert": "ok"}}
    (ep / "upload.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))  # save before extras

    def step(name, fn):
        try:
            fn()
            result["steps"][name] = "ok"
        except Exception as e:  # keep going; the video is up, record what failed
            result["steps"][name] = f"failed: {e}"
            log(f"  {name} failed: {e}")
        (ep / "upload.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))

    thumb = ep / (meta.get("thumbnail_file") or "")
    if meta.get("thumbnail_file") and thumb.is_file():
        step("thumbnail", lambda: service.thumbnails().set(
            videoId=vid, media_body=make_media(thumb, "image/jpeg", False)).execute())
    caps = ep / (meta.get("captions_file") or "")
    if meta.get("captions_file") and caps.is_file():
        step("captions", lambda: service.captions().insert(
            part="snippet", body={"snippet": {"videoId": vid, "language": lang, "name": "", "isDraft": False}},
            media_body=make_media(caps, "application/octet-stream", False)).execute())
    pl = (channel.get("playlist_by_cluster") or {}).get(str(brief.get("cluster")))
    if pl:
        step("playlist", lambda: service.playlistItems().insert(part="snippet", body={
            "snippet": {"playlistId": pl, "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute())
    log(f"Done: {result['url']} ({mode}{', publishes ' + result['publish_at'] if result.get('publish_at') else ''})")
    return result
