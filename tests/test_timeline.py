import csv
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import timeline as T  # noqa: E402

SCRIPT = """TITLE: T
THUMB: X
SIGNOFF: Until next time, keep looking back.
## HOOK
[MIX: voice leads]
[MUSIC: drone]
It is night. The walls wait.
[PAUSE 1.5]
Who will win?
## CHAPTER 1
[J-CUT: hammers start under the last hook shot]
[VISUAL: card "1452 · Edirne"]
A cannon is cast.
[SFX: cannon]
It fires.
"""
SENTS = [("HOOK", "It is night.", 0.0, 2.0), ("HOOK", "The walls wait.", 2.0, 4.0),
         ("HOOK", "Who will win?", 5.5, 8.0),
         ("CHAPTER 1", "A cannon is cast.", 9.0, 40.0), ("CHAPTER 1", "It fires.", 40.0, 44.0)]
COLS = ["sentence_no", "section", "sentence", "visual_type", "search_terms", "motion", "duration_s", "asset_id"]


def make_ep(tmp_path, cells=None):
    ep = tmp_path / "episodes" / "2026-12-14-en-x"
    (ep / "assets").mkdir(parents=True)
    (ep / "audio").mkdir()
    (ep / "script.md").write_text(SCRIPT, encoding="utf-8")
    (ep / "audio" / "narration_timing.json").write_text(json.dumps({
        "audio": "audio/narration.wav", "total_seconds": 44.0,
        "sentences": [{"i": i, "section": s, "text": t, "start": a, "end": b} for i, (s, t, a, b) in enumerate(SENTS)]}))
    Image.new("RGB", (1600, 900)).save(ep / "assets" / "wide.jpg")
    Image.new("RGB", (800, 600)).save(ep / "assets" / "old.jpg")
    Image.new("RGB", (1344, 768)).save(ep / "assets" / "ai-004.png")
    (ep / "render" / "maps").mkdir(parents=True)
    (ep / "render" / "maps" / "m.mp4").write_bytes(b"x")
    with (ep / "assets" / "manifest.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["asset_id", "file", "source", "source_url", "licence", "credit", "ai_generated", "notes"])
        w.writerow(["wm-1", "assets/wide.jpg", "commons", "u", "PD", "c", "n", ""])
        w.writerow(["wm-2", "assets/old.jpg", "commons", "u", "PD", "c", "n", ""])
        w.writerow(["ai-004", "assets/ai-004.png", "gemini", "g", "AI", "c", "y", "label=Illustration"])
        w.writerow(["map-m", "render/maps/m.mp4", "own map", "own", "own", "c", "n", ""])
    cells = cells or [
        ("location", "walls at night", "zoom_in", "wm-1"),
        ("painting | card", "a painting | card: 7,000 defenders", "zoom_out | static", "wm-2 | "),
        ("location | map", "walls | map: the land walls", "pan_left | map_anim", "wm-1 | "),
        ("illustration_ai | painting | painting | painting | map", "a | b | c | d | map: cannon road",
         "zoom_in | zoom_out | zoom_in | zoom_out | map_anim", "ai-004 | wm-2 | wm-1 | wm-2 | map-m"),
        ("engraving", "firing", "zoom_in", "wm-2"),
    ]
    with (ep / "shotlist.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for i, ((sec, text, a, b), (vt, terms, mot, aid)) in enumerate(zip(SENTS, cells), 1):
            w.writerow({"sentence_no": i, "section": sec, "sentence": text, "visual_type": vt, "search_terms": terms,
                        "motion": mot, "duration_s": b - a, "asset_id": aid})
    return ep


def probe(path):
    return {"width": 1920, "height": 1080, "duration": 3.0}


def test_shots_cover_the_narration_end_to_end_and_split_sentences_evenly(tmp_path):
    e = T.build(make_ep(tmp_path), probe)
    sh = e["shots"]
    assert sh[0]["start"] == 0 and sh[-1]["end"] == 44.0 + T.TAIL == e["duration"]
    assert all(abs(a["end"] - b["start"]) < 1e-9 for a, b in zip(sh, sh[1:]))
    assert [s["id"] for s in sh[1:3]] == ["s002.1", "s002.2"] and sh[1]["duration"] == 1.75   # 2.0 -> 5.5 halved
    assert sh[-1]["fade_out_s"] == T.TAIL and not e["errors"]


def test_fit_motion_cards_labels_video_and_placeholders(tmp_path):
    s = {x["id"]: x for x in T.build(make_ep(tmp_path), probe)["shots"]}
    assert s["s001.1"]["fit"] == "cover" and s["s002.1"]["fit"] == "contain_blur"          # 16:9 vs 4:3
    assert s["s001.1"]["motion"] == {"type": "zoom", "scale": [1.0, 1.05]}
    assert s["s002.1"]["motion"]["scale"][0] > 1 and s["s002.1"]["motion"]["scale"][1] == 1.0
    assert s["s003.1"]["motion"]["type"] == "pan" and s["s003.1"]["motion"]["x"] == [1, -1]  # pan_left
    assert s["s002.2"]["kind"] == "card" and s["s002.2"]["card"] == {"text": "7,000 defenders", "style": "fact"}
    assert s["s004.1"]["label"] == "Illustration" and "label" not in s["s004.2"]
    assert s["s003.2"]["kind"] == "placeholder" and s["s003.2"]["reason"] == "map clip not made yet"
    assert s["s004.5"]["kind"] == "video" and s["s004.5"]["hold_last"] and s["s004.5"]["clip_s"] == 3.0


def test_ken_burns_grows_with_length_but_stays_5_to_10_percent():
    assert T.ken_burns("zoom_in", 2)["scale"] == [1.0, 1.05]
    assert T.ken_burns("zoom_in", 30)["scale"] == [1.0, 1.1]
    assert T.ken_burns("static", 5) == {"type": "static"}


def test_transitions_fade_at_chapters_and_dissolve_after_pauses(tmp_path):
    s = {x["id"]: x for x in T.build(make_ep(tmp_path), probe)["shots"]}
    assert s["s001.1"]["transition_in"] == "cut" and s["s002.1"]["transition_in"] == "cut"
    assert s["s003.1"]["transition_in"] == "dissolve"          # after [PAUSE 1.5]
    assert s["s004.1"]["transition_in"] == "fade_black"        # CHAPTER 1 starts
    assert s["s004.2"]["transition_in"] == "cut"


def test_cues_are_timed_and_j_cuts_lead_the_picture(tmp_path):
    e = T.build(make_ep(tmp_path), probe)
    cues = [(c["type"], c["t"]) for c in e["cues"]]
    assert cues == [("MIX", 0.0), ("MUSIC", 0.0), ("J-CUT", 8.0), ("SFX", 40.0)]
    assert [c["section"] for c in e["chapters"]] == ["HOOK", "CHAPTER 1"]


def test_pacing_rules_are_checked(tmp_path):
    e = T.build(make_ep(tmp_path), probe)
    assert e["stats"]["first_30s"]["over_3s"] == 4 and "s004.4" in e["warnings"][0]   # s004.1-4 start before 30 s, 6.2 s each
    long = make_ep(tmp_path / "b", cells=[("location", "x", "zoom_in", "wm-1")] * 3 +
                   [("painting", "y", "zoom_in", "wm-2"), ("engraving", "z", "zoom_in", "wm-2")])
    e = T.build(long, probe)
    assert e["errors"] and "s004.1 (31.0s)" in e["errors"][0]


def test_shotlist_out_of_step_with_timing_is_refused(tmp_path):
    ep = make_ep(tmp_path)
    t = json.loads((ep / "audio" / "narration_timing.json").read_text())
    t["sentences"][0]["text"] = "Changed."
    (ep / "audio" / "narration_timing.json").write_text(json.dumps(t))
    with pytest.raises(T.TimelineError, match="disagree"):
        T.build(ep, probe)


def test_card_kinds():
    assert T.card_of("card: 1452 · Edirne") == {"text": "1452 · Edirne", "style": "chapter"}
    assert T.card_of('quote card: "Better the turban." (reported by Doukas)') ==         {"text": "Better the turban.", "source": "reported by Doukas", "style": "quote"}
    assert T.card_of("end card: Until next time, keep looking back.")["text"] == "Until next time, keep looking back."
    assert T.card_of("end card: series playlist") == {"text": "", "style": "end"}
