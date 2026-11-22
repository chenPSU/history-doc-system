import csv
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import thumbnail as T  # noqa: E402

TITLE = "The Fall of Constantinople: The Last 53 Days of Byzantium"


def test_text_rules():
    assert T.check_text("HE WAS 21", TITLE) == []
    assert "5 words" in T.check_text("ONE TWO THREE FOUR FIVE", TITLE)[0]
    assert any("repeats the title" in p for p in T.check_text("53 DAYS", TITLE))


def test_frame_is_1280x720_from_any_shape():
    assert T.frame(Image.new("RGB", (900, 1600)), [0.5, 0.3], 1.2).size == (T.W, T.H)
    assert T.frame(Image.new("RGB", (4000, 1000)), [0.9, 0.5], 1.0).size == (T.W, T.H)


@pytest.mark.skipif(not T.FONT.exists(), reason="system font not available")
def test_make_writes_a_small_jpeg(tmp_path):
    ep = tmp_path / "ep"
    (ep / "assets").mkdir(parents=True)
    Image.new("RGB", (2000, 1500), (120, 90, 60)).save(ep / "assets" / "a.jpg")
    with (ep / "assets" / "manifest.csv").open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([["asset_id", "file", "source", "source_url", "licence", "credit", "ai_generated", "notes"],
                                 ["wm-1", "assets/a.jpg", "commons", "u", "PD", "c", "n", ""]])
    out, problems = T.make(ep, {"file": "render/t.jpg", "asset": "wm-1", "text": "HE WAS 21", "accent": "red"}, TITLE)
    with Image.open(out) as im:
        assert im.size == (1280, 720)
    assert problems == [] and out.stat().st_size < T.MAX_BYTES
