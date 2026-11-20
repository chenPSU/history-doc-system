import datetime as dt
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import youtube_upload as yu  # noqa: E402

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 12, 10, 3, 0, tzinfo=UTC)  # a Thursday


def policy(**kw):
    p = {
        "mode": "scheduled", "audit_passed": True, "require_owner_approval": True, "review_window_hours": 24,
        "max_uploads_per_day": 2, "channels": {"en": {
            "channel_id": "UC_EN", "token": "secrets/x.json", "default_language": "en", "category_id": "27",
            "publish_slots_utc": ["Tue 22:00", "Fri 22:00"], "playlist_by_cluster": {"9": "PL9"}}},
    }
    p.update(kw)
    return p


def make_episode(tmp: Path, name="2026-12-14-en-constantinople", **overrides) -> Path:
    ep = tmp / "episodes" / name
    (ep / "render").mkdir(parents=True)
    (ep / "assets").mkdir()
    (ep / "brief.yaml").write_text(yaml.safe_dump({"language": "en", "cluster": 9}))
    meta = {"title": "How 53 Days Broke a Thousand-Year Wall", "description": "The fall of Constantinople.",
            "chapters": [{"time": "0:00", "title": "Intro"}], "tags": ["history"], "sources": ["Runciman 1965"],
            "footage_credits": ["Wikimedia Commons, PD"], "altered_or_synthetic_disclosure": True,
            "made_for_kids": False, "video_file": "render/final.mp4", "thumbnail_file": "render/thumbnail.jpg",
            "captions_file": "render/captions.srt"}
    meta.update(overrides)
    (ep / "metadata.yaml").write_text(yaml.safe_dump(meta, allow_unicode=True))
    (ep / "render" / "final.mp4").write_bytes(b"0")
    (ep / "render" / "thumbnail.jpg").write_bytes(b"0")
    (ep / "render" / "captions.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n")
    (ep / "assets" / "manifest.csv").write_text("asset_id,file,source,source_url,licence,credit,ai_generated,notes\n"
                                                "a1,x.jpg,LOC,https://loc.gov/x,PD,LOC,n,\n")
    (ep / "score.json").write_text(json.dumps({"gate_passed": True}))
    (ep / "preflight.json").write_text(json.dumps({"passed": True}))
    (ep / "approved.yaml").write_text("approved_by: owner\napproved_at: 2026-12-09\n")
    return ep


class FakeReq:
    def __init__(self, result, fail_times=0):
        self.result, self.fail_times = result, fail_times

    def next_chunk(self):
        if self.fail_times:
            self.fail_times -= 1
            err = Exception("503")
            err.resp = type("R", (), {"status": 503})()
            raise err
        return None, self.result

    def execute(self):
        return self.result


class FakeService:
    def __init__(self, channel="UC_EN"):
        self.channel, self.calls = channel, []

    def _res(self, name):
        svc = self

        class R:
            def list(self, **kw):
                svc.calls.append((name, "list", kw))
                return FakeReq({"items": [{"id": svc.channel, "snippet": {"title": "EN"}}]})

            def insert(self, **kw):
                svc.calls.append((name, "insert", kw))
                return FakeReq({"id": "VID123"})

            def set(self, **kw):
                svc.calls.append((name, "set", kw))
                return FakeReq({})
        return R()

    def channels(self): return self._res("channels")
    def videos(self): return self._res("videos")
    def thumbnails(self): return self._res("thumbnails")
    def captions(self): return self._res("captions")
    def playlistItems(self): return self._res("playlistItems")


def fake_media(path, mimetype, resumable=True):
    return (str(path), mimetype)


def test_unaudited_project_falls_back_to_private():
    mode, warns = yu.effective_mode(policy(audit_passed=False))
    assert mode == "private" and warns


def test_next_slot_respects_review_window_and_taken():
    earliest = NOW + dt.timedelta(hours=24)  # Fri 11 Dec 03:00
    s1 = yu.next_publish_slot(["Tue 22:00", "Fri 22:00"], earliest)
    assert s1 == dt.datetime(2026, 12, 11, 22, 0, tzinfo=UTC)
    s2 = yu.next_publish_slot(["Tue 22:00", "Fri 22:00"], earliest, {s1})
    assert s2 == dt.datetime(2026, 12, 15, 22, 0, tzinfo=UTC)


def test_body_scheduled_is_private_with_publish_at_and_ai_flag():
    pub = dt.datetime(2026, 12, 11, 22, 0, tzinfo=UTC)
    b = yu.build_body({"title": "T", "altered_or_synthetic_disclosure": True}, {"language": "en"},
                      policy()["channels"]["en"], "scheduled", pub)
    assert b["status"]["privacyStatus"] == "private"
    assert b["status"]["publishAt"] == "2026-12-11T22:00:00Z"
    assert b["status"]["containsSyntheticMedia"] is True
    assert b["snippet"]["categoryId"] == "27"
    assert "created with AI" in b["snippet"]["description"]


def test_gates_list_every_missing_piece(tmp_path):
    ep = make_episode(tmp_path)
    (ep / "approved.yaml").unlink()
    (ep / "score.json").write_text(json.dumps({"gate_passed": False}))
    f = yu.check_gates(ep, policy())
    assert any("approval" in x for x in f)
    assert any("score gate" in x for x in f)


def test_unaudited_project_blocks_real_episodes_but_allows_test_uploads(tmp_path):
    ep = make_episode(tmp_path)
    p = policy(audit_passed=False)
    assert any("audit not passed" in x for x in yu.check_gates(ep, p))
    (ep / "brief.yaml").write_text(yaml.safe_dump({"language": "en", "cluster": 9, "test_upload": True}))
    assert yu.check_gates(ep, p) == []
    plan = yu.upload_episode(ep, p, go=False, now=NOW, log=lambda *_: None)
    assert plan["mode"] == "private" and plan["publish_at"] is None


def test_dry_run_sends_nothing(tmp_path):
    ep = make_episode(tmp_path)
    svc = FakeService()
    plan = yu.upload_episode(ep, policy(), go=False, service=svc, now=NOW, log=lambda *_: None)
    assert plan["publish_at"] == "2026-12-11T22:00:00Z"
    assert svc.calls == [] and not (ep / "upload.json").exists()


def test_upload_writes_result_and_never_uploads_twice(tmp_path):
    ep = make_episode(tmp_path)
    svc = FakeService()
    res = yu.upload_episode(ep, policy(), go=True, service=svc, make_media=fake_media, now=NOW, log=lambda *_: None)
    assert res["video_id"] == "VID123"
    assert res["steps"] == {"insert": "ok", "thumbnail": "ok", "captions": "ok", "playlist": "ok"}
    saved = json.loads((ep / "upload.json").read_text())
    assert saved["video_id"] == "VID123"
    with pytest.raises(yu.GateError) as e:
        yu.upload_episode(ep, policy(), go=True, service=svc, make_media=fake_media, now=NOW, log=lambda *_: None)
    assert any("already uploaded" in x for x in e.value.failures)


def test_wrong_channel_token_is_refused(tmp_path):
    ep = make_episode(tmp_path)
    with pytest.raises(yu.GateError):
        yu.upload_episode(ep, policy(), go=True, service=FakeService("UC_TH"), make_media=fake_media, now=NOW,
                          log=lambda *_: None)
    assert not (ep / "upload.json").exists()


def test_daily_cap(tmp_path):
    p = policy(max_uploads_per_day=1)
    a = make_episode(tmp_path, "2026-12-14-en-a")
    b = make_episode(tmp_path, "2026-12-14-en-b")
    yu.upload_episode(a, p, go=True, service=FakeService(), make_media=fake_media, now=NOW, log=lambda *_: None)
    with pytest.raises(yu.GateError) as e:
        yu.upload_episode(b, p, go=True, service=FakeService(), make_media=fake_media, now=NOW, log=lambda *_: None)
    assert "max_uploads_per_day" in e.value.failures[0]


def test_resumable_retries_transient_errors():
    out = yu.resumable_insert(FakeReq({"id": "X"}, fail_times=2), sleep=lambda s: None, log=lambda *_: None)
    assert out["id"] == "X"
