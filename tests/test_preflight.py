import json
import os
import time

import yaml
from PIL import Image

from pipeline import preflight as P

CFG = P.load_config()
FACTS = """# Fact sheet

## Facts

| # | Fact | Value used in script | Source 1 | Source 2 | Checked | Disputed? |
|---|---|---|---|---|---|---|
| 1 | The city fell | 1453 | R | C | web | No |
| 2 | Days of siege | 53 | R | C | book | No |

## First-person quotes (VOICE lines)

| Speaker | Quote (as narrated) | Primary source | Translation used |
|---|---|---|---|
"""
SCRIPT = """TITLE: T
## HOOK
[MUSIC: drone]
In 1453 a wall fell.
Why did it fall in 53 days?
## CLOSE
Until next time, keep looking back.
"""


def probe_for(duration):
    def probe(path):
        vertical = "shorts" in str(path)
        return {"width": 1080 if vertical else 1920, "height": 1920 if vertical else 1080,
                "duration": 30.0 if vertical else duration, "audio": True}
    return probe


def make_ep(tmp_path, name="2026-12-14-en-test", lang="en", tail=15.0, facts=FACTS, script=SCRIPT,
            licence="Public domain", brief_extra=None, meta_extra=None):
    ep = tmp_path / name
    for d in ("assets", "render", "audio"):
        (ep / d).mkdir(parents=True)
    brief = {"language": lang, "slug": "test", "title_formula": "countdown", **(brief_extra or {})}
    (ep / "brief.yaml").write_text(yaml.safe_dump(brief, allow_unicode=True), encoding="utf-8")
    (ep / "script.md").write_text(script, encoding="utf-8")
    (ep / "factsheet.md").write_text(facts, encoding="utf-8")
    time.sleep(0.01)
    (ep / "score.json").write_text(json.dumps({"gate_passed": True, "mean": 95, "rounds": {}}), encoding="utf-8")
    future = time.time() + 5
    os.utime(ep / "score.json", (future, future))
    (ep / "assets" / "manifest.csv").write_text(
        "asset_id,file,source,source_url,licence,credit,ai_generated,notes\n"
        f"wm-1,assets/a.jpg,commons,https://x,{licence},Someone,n,\n", encoding="utf-8")
    (ep / "assets" / "a.jpg").write_bytes(b"x")
    sents = [{"i": 0, "text": "In 1453 a wall fell.", "start": 0.0, "end": 4.0},
             {"i": 1, "text": "Why did it fall in 53 days?", "start": 4.5, "end": 9.0},
             {"i": 2, "text": "Until next time, keep looking back.", "start": 17.5, "end": 20.0}]
    (ep / "audio" / "narration_timing.json").write_text(json.dumps({"total_seconds": 20.0, "sentences": sents}))
    dur = 20.0 + tail
    shots = [{"id": "s001.1", "kind": "image", "asset_id": "wm-1", "start": 0.0, "end": 4.5, "duration": 4.5},
             {"id": "s002.1", "kind": "image", "asset_id": "wm-1", "start": 4.5, "end": 14.0, "duration": 9.5},
             {"id": "s003.1", "kind": "card", "start": 14.0, "end": dur, "duration": dur - 14.0}]
    (ep / "render" / "edl.json").write_text(json.dumps({"duration": dur, "shots": shots, "errors": [], "warnings": [],
                                                        "placeholders": []}))
    time.sleep(0.01)
    (ep / "render" / "video.mp4").write_bytes(b"v")
    (ep / "render" / "captions.srt").write_text("1\n00:00:00,000 --> 00:00:04,000\nIn 1453 a wall fell.\n", encoding="utf-8")
    Image.new("RGB", (1280, 720), (90, 60, 30)).save(ep / "render" / "thumb.jpg")
    meta = {"title": "The Fall of a City", "description": "A story.", "tags": ["history"],
            "chapters": [{"time": "0:00", "title": "a"}, {"time": "0:10", "title": "b"}, {"time": "0:20", "title": "c"}],
            "sources": ["R"], "footage_credits": ["Someone"], "altered_or_synthetic_disclosure": False,
            "video_file": "render/video.mp4", "captions_file": "render/captions.srt", "thumbnail_file": "render/thumb.jpg",
            "thumbnails": [{"file": "render/thumb.jpg", "text": "53 DAYS"}], **(meta_extra or {})}
    (ep / "metadata.yaml").write_text(yaml.safe_dump(meta, allow_unicode=True), encoding="utf-8")
    return ep, probe_for(dur)


def status(res, id_):
    return next(r["status"] for r in res["checks"] if r["id"] == id_)


def test_a_complete_episode_passes_and_lists_manual_items(tmp_path):
    ep, probe = make_ep(tmp_path)
    res = P.run(ep, CFG, probe)
    assert res["passed"], res["failed"]
    assert status(res, "end_tail") == "pass" and status(res, "thai") == "n/a"
    assert any("end screen" in m for m in res["manual"]) and any("1 fact rows" in m for m in res["manual"])
    assert json.loads(P.write(ep, res).read_text(encoding="utf-8"))["passed"] is True


def test_fact_gate_needs_two_sources_and_every_number(tmp_path):
    facts = FACTS.replace("| 2 | Days of siege | 53 | R | C |", "| 2 | Days of siege | 54 | R | — |")
    ep, probe = make_ep(tmp_path, facts=facts)
    res = P.run(ep, CFG, probe)
    assert not res["passed"]
    assert status(res, "facts.two_sources") == "fail" and status(res, "facts.numbers") == "fail"
    assert "53" in next(r["detail"] for r in res["checks"] if r["id"] == "facts.numbers")


def test_open_fact_and_voice_without_source_fail(tmp_path):
    facts = FACTS.replace("| web | No |", "| open | ? |")
    script = SCRIPT.replace("## CLOSE", 'VOICE (Barbaro): "The city is lost."\n## CLOSE')
    ep, probe = make_ep(tmp_path, facts=facts, script=script)
    res = P.run(ep, CFG, probe)
    assert status(res, "facts.open") == "fail" and status(res, "quotes") == "fail"


def test_non_commercial_licence_fails_rights(tmp_path):
    ep, probe = make_ep(tmp_path, licence="CC BY-NC 4.0")
    res = P.run(ep, CFG, probe)
    assert status(res, "rights.licence") == "fail" and not res["passed"]


def test_short_end_tail_fails_unless_waived(tmp_path):
    ep, probe = make_ep(tmp_path, tail=2.0)
    assert status(P.run(ep, CFG, probe), "end_tail") == "fail"
    ep2, probe2 = make_ep(tmp_path, name="2026-12-15-en-x", tail=2.0,
                          brief_extra={"preflight_waivers": {"end_tail": "owner adds no end screen"}})
    res = P.run(ep2, CFG, probe2)
    assert "end_tail" not in [f["id"] for f in res["failed"]]
    assert {"id": "end_tail", "waived": "owner adds no end screen"}.items() <= next(
        w for w in res["warnings"] if w["id"] == "end_tail").items()


def test_still_over_ten_seconds_fails_but_the_end_tail_is_exempt(tmp_path):
    ep, probe = make_ep(tmp_path, tail=20.0)          # the last card runs 26 s, nearly all of it tail
    assert status(P.run(ep, CFG, probe), "picture.still") == "pass"
    edl = json.loads((ep / "render" / "edl.json").read_text())
    edl["shots"][0].update(end=11.0, duration=11.0)
    (ep / "render" / "edl.json").write_text(json.dumps(edl))
    assert status(P.run(ep, CFG, probe), "picture.still") == "fail"


def test_hook_needs_a_question_in_the_first_30_seconds(tmp_path):
    ep, probe = make_ep(tmp_path)
    t = json.loads((ep / "audio" / "narration_timing.json").read_text())
    t["sentences"][1]["text"] = "It fell in 53 days."
    (ep / "audio" / "narration_timing.json").write_text(json.dumps(t))
    assert status(P.run(ep, CFG, probe), "hook") == "fail"


def test_thai_channel_blocks_monarchy_and_unchecked_khmer_topics(tmp_path):
    ep, probe = make_ep(tmp_path, lang="th", script=SCRIPT + "\nเรื่องของในหลวงและเขมร\n")
    res = P.run(ep, CFG, probe)
    assert status(res, "thai.monarchy") == "fail" and status(res, "thai.khmer") == "fail"
    ep2, probe2 = make_ep(tmp_path, name="2026-12-15-th-x", lang="th", script=SCRIPT + "\nเรื่องเขมร\n",
                          brief_extra={"tone_checked": True})
    res2 = P.run(ep2, CFG, probe2)
    assert status(res2, "thai.khmer") == "pass" and status(res2, "thai.monarchy") == "pass"


def test_title_formula_and_thumbnail_must_differ_from_previous_uploads(tmp_path):
    prev, _ = make_ep(tmp_path, name="2026-12-07-en-prev")
    (prev / "upload.json").write_text(json.dumps({"video_id": "abc", "publish_at": "2026-12-07T15:00:00Z"}))
    ep, probe = make_ep(tmp_path)                    # same formula, same (flat) thumbnail
    res = P.run(ep, CFG, probe)
    assert status(res, "variety.title") == "fail" and status(res, "variety.thumbnail") == "fail"
    test, _ = make_ep(tmp_path, name="2026-12-01-en-upload-test", brief_extra={"test_upload": True})
    assert [d.name for d in P.previous_videos(P.Episode(ep), 3)] == ["2026-12-07-en-prev"]


def test_realistic_ai_media_needs_the_disclosure_flag(tmp_path):
    ep, probe = make_ep(tmp_path)
    man = ep / "assets" / "manifest.csv"
    man.write_text(man.read_text() + "ai-001,assets/a.jpg,gemini,generated:x,AI-generated for this channel (no third-party rights),"
                   "Channel,y,class=ai; label=Illustration; realistic=y\n")
    edl = json.loads((ep / "render" / "edl.json").read_text())
    edl["shots"][1].update(asset_id="ai-001", label="Illustration")
    (ep / "render" / "edl.json").write_text(json.dumps(edl))
    res = P.run(ep, CFG, probe)
    assert status(res, "ai.disclosure") == "fail"


def test_a_crashing_check_fails_instead_of_passing(tmp_path, monkeypatch):
    ep, probe = make_ep(tmp_path)
    def boom(e, cfg):
        raise RuntimeError("bad file")
    monkeypatch.setattr(P, "CHECKS", [boom])
    res = P.run(ep, CFG, probe)
    assert not res["passed"] and "crashed" in res["failed"][0]["detail"]
