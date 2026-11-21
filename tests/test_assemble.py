import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import assemble as A  # noqa: E402


def shot(i, start, end, kind="image", transition="cut", t_s=None, **kw):
    s = {"id": f"s{i:03d}.1", "kind": kind, "start": start, "end": end, "transition_in": transition,
         "motion": {"type": "zoom", "scale": [1.0, 1.05]}, "visual_type": kw.pop("vt", "painting")}
    if t_s:
        s["transition_s"] = t_s
    s.update(kw)
    return s


def make(tmp_path):
    ep = tmp_path / "ep"
    (ep / "assets").mkdir(parents=True)
    (ep / "audio").mkdir()
    (ep / "audio" / "narration.wav").write_bytes(b"RIFF....")
    Image.new("RGB", (6000, 3000), (200, 120, 60)).save(ep / "assets" / "big.jpg")
    Image.new("RGB", (800, 600), (30, 60, 200)).save(ep / "assets" / "old.jpg")
    edl = {"fps": 30, "duration": 12.0, "audio": {"narration": "audio/narration.wav"}, "shots": [
        shot(1, 0, 3, file="assets/big.jpg", asset_id="wm-1", fit="cover", vt="location"),
        shot(2, 3, 6, file="assets/old.jpg", asset_id="wm-2", fit="contain_blur", transition="dissolve", t_s=0.8,
             label="Illustration"),
        shot(3, 6, 9, kind="card", transition="fade_black", t_s=1.0, card={"text": "1452 · Edirne", "style": "chapter"}),
        dict(shot(4, 9, 12, kind="placeholder", text="map: x", reason="map clip not made yet"), fade_out_s=2.0),
    ]}
    return ep, edl


def test_props_resolve_transitions_into_frames(tmp_path):
    ep, edl = make(tmp_path)
    p = A.build_props(edl, ep, tmp_path / "stage", 1920, 1080)
    s1, s2, s3, s4 = p["shots"]
    assert p["durationInFrames"] == 360 and p["audio"] == "narration.wav"
    # dissolve 0.8 s = 24 frames: the incoming shot starts 12 early and ramps in; the outgoing runs 12 longer
    assert (s2["from"], s2["fadeIn"]) == (90 - 12, 24) and s1["from"] + s1["dur"] == 90 + 12
    # fade to black 1 s: 15 frames out, 15 in, no overlap
    assert s2["fadeOut"] == 15 and s2["from"] + s2["dur"] == 180 and (s3["from"], s3["fadeIn"]) == (180, 15)
    assert s4["fadeOut"] == 60 and s4["from"] + s4["dur"] == 360
    assert s3["card"]["style"] == "chapter" and s4["reason"] == "map clip not made yet" and s2["label"] == "Illustration"


def test_proxies_are_sized_for_the_frame_graded_and_backgrounds_made(tmp_path):
    ep, edl = make(tmp_path)
    stage = tmp_path / "stage"
    p = A.build_props(edl, ep, stage, 1920, 1080)
    s1, s2 = p["shots"][:2]
    assert s1["src"] == "p/wm-1_g.jpg" and s2["src"] == "p/wm-2_t.jpg"        # photos graded; labelled AI prints trimmed
    with Image.open(stage / s1["src"]) as im:
        assert im.height == round(1080 * A.MAX_SCALE) and im.width < 6000        # cover at the largest zoom
        r, g, b = im.getpixel((10, 10))
    assert (r, g, b) != (200, 120, 60)
    with Image.open(stage / s2["src"]) as im:
        assert im.size == (800, 600)                                             # never upscaled; no paper margin to trim
    assert s2["bg"] == "bg/wm-2.jpg" and (stage / "bg" / "wm-2.jpg").exists() and "bg" not in s1
    assert (stage / "narration.wav").exists() and (stage / "grain.png").exists()


def test_frames_round_to_the_nearest_frame():
    assert A.frames(1.0, 30) == 30 and A.frames(0.016, 30) == 0 and A.frames(0.017, 30) == 1
