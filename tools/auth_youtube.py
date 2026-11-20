#!/usr/bin/env python3
"""One-time sign-in for a channel. Run on your own computer (it opens a browser).

  python tools/auth_youtube.py --lang en
  python tools/auth_youtube.py --lang th

When Google asks which account/channel to use, pick the channel for that language (Brand Account).
The token is saved to the path in config/upload_policy.yaml, and the channel id is printed so you can
paste it into the policy (or pass --write-channel-id to save it there).
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import youtube_upload as yu  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, choices=["en", "th"])
    ap.add_argument("--write-channel-id", action="store_true", help="save the channel id into upload_policy.yaml")
    a = ap.parse_args()
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    policy = yu.load_policy()
    ch = policy["channels"][a.lang]
    secrets = ROOT / policy["client_secrets"]
    if not secrets.exists():
        sys.exit(f"Missing {secrets}. Follow docs/upload-setup.md step 4.")
    flow = InstalledAppFlow.from_client_secrets_file(str(secrets), yu.SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    token = ROOT / ch["token"]
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(creds.to_json())
    svc = build("youtube", "v3", credentials=creds, cache_discovery=False)
    item = svc.channels().list(part="id,snippet", mine=True).execute()["items"][0]
    print(f"Signed in as channel: {item['snippet']['title']}  id={item['id']}")
    if ch.get("channel_id") and ch["channel_id"] != item["id"]:
        print(f"WARNING: policy expects {ch['channel_id']} for {a.lang}. Wrong channel? Run again and pick the right one.")
    if a.write_channel_id:
        p = ROOT / "config" / "upload_policy.yaml"
        text = p.read_text(encoding="utf-8")
        marker = f"  {a.lang}:\n    channel_id: \"\""
        if marker in text:
            p.write_text(text.replace(marker, f"  {a.lang}:\n    channel_id: \"{item['id']}\""), encoding="utf-8")
            print("channel_id saved to config/upload_policy.yaml")
        else:
            print("channel_id already set; not changed.")


if __name__ == "__main__":
    main()
