import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import adapt_th as A  # noqa: E402

EN = ROOT / "episodes" / "2026-12-14-en-constantinople"


def test_names_used_by_the_english_script_come_from_the_glossary():
    cast, places = A.used_names((EN / "script.md").read_text(encoding="utf-8"))
    assert {"เมห์เหม็ด", "คอนสแตนติน", "จุสตินีอานี"} <= set(cast)
    assert "คอนสแตนติโนเปิล" in places and places.count("เวนิส") == 1     # Venice / Venetian -> one entry
    assert "เอเดรียโนเปิล" not in places                                    # only in a [VISUAL] cue, not narrated


def test_adapt_creates_a_thai_folder_with_cues_and_no_narration(tmp_path):
    dest = A.adapt(EN, "2026-12-14", "ทดสอบ", "53 วัน", root=tmp_path)
    b = yaml.safe_load((dest / "brief.yaml").read_text(encoding="utf-8"))
    assert dest.name == "2026-12-14-th-constantinople" and b["language"] == "th"
    assert b["source_episode"] == EN.name and b["signoff"] == A.TH_SIGNOFF
    script = (dest / "script.md").read_text(encoding="utf-8")
    assert script.count("## ") == (EN / "script.md").read_text(encoding="utf-8").count("## ")
    assert "[J-CUT:" in script and "Constantine" not in script and script.rstrip().endswith(A.TH_SIGNOFF)
    assert "## Thai additions" in (dest / "factsheet.md").read_text(encoding="utf-8")
