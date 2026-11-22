import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import metadata as M  # noqa: E402
from pipeline.youtube_upload import build_description  # noqa: E402


def test_chapters_use_cards_overrides_and_fold_short_sections():
    edl = {"duration": 300.0, "chapters": [
        {"section": "HOOK", "start": 0.0, "title": ""},
        {"section": "PROMISE", "start": 30.0, "title": ""},                   # 5 s long: folded into HOOK
        {"section": "CONTEXT", "start": 35.0, "title": "330 AD · Constantinople"},
        {"section": "CHAPTER 1", "start": 3725.0 - 3600, "title": "1452 · The Bosphorus"}]}
    ch = M.chapters(edl, {"HOOK": "The last night"})
    assert ch == [{"time": "0:00", "title": "The last night"}, {"time": "0:35", "title": "Constantinople, 330 AD"},
                  {"time": "2:05", "title": "The Bosphorus, 1452"}]


def test_sources_skip_locator_entries_and_markdown(tmp_path):
    f = tmp_path / "factsheet.md"
    f.write_text("# X\n\n## Sources\n\n| Key | Work |\n|---|---|\n| R | Runciman, *The Fall*, 1965 |\n"
                 "| WK | Wikipedia articles, used only to locate the cited work |\n\n## Facts\n", encoding="utf-8")
    assert M.sources(f) == ["Runciman, The Fall, 1965"]


def test_credits_group_by_licence_and_keep_the_description_short(tmp_path):
    ep = tmp_path / "ep"
    (ep / "assets").mkdir(parents=True)
    rows = [
        ["wm-1", "assets/a.jpg", "commons", "u", "CC BY-SA 4.0", "Alice, CC BY-SA 4.0, via Wikimedia Commons", "n", "class=cc-by-sa"],
        ["wm-2", "assets/b.jpg", "commons", "u", "CC BY-SA 4.0", "Bob : https://flickr.com/x, CC BY-SA 4.0, via Wikimedia Commons", "n", "class=cc-by-sa"],
        ["wm-3", "assets/c.jpg", "commons", "u", "Public domain", "X, Public domain, via Wikimedia Commons", "n", "class=pd"],
        ["map-a", "data/maps/x.yaml#a", "own map", "own", "own", "Map data © OpenStreetMap contributors (ODbL)", "n", "class=own"],
        ["ai-001", "assets/ai-001.png", "gemini", "g", "AI", "AI", "y", "class=ai; label=Illustration"],
        ["wm-9", "audio/lib/m.mp3", "commons", "u", "CC BY 3.0", "Kevin MacLeod, CC BY 3.0, via Wikimedia Commons", "n",
         "class=cc-by; kind=audio; title=Night Cave (ISRC USUAN1100446).mp3"],
    ]
    with (ep / "assets" / "manifest.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["asset_id", "file", "source", "source_url", "licence", "credit", "ai_generated", "notes"])
        w.writerows(rows)
    edl = {"shots": [{"asset_id": a} for a in ("wm-1", "wm-2", "wm-3", "map-a", "ai-001")]}
    lines = M.credits(ep, edl, {"music": [{"asset": "wm-9"}], "sfx": []})
    assert lines[0] == "CC BY-SA 4.0 (via Wikimedia Commons): Alice; Bob"
    assert any("OpenStreetMap" in x for x in lines) and any(x.startswith("Other pictures: public domain") for x in lines)
    assert any('"Night Cave" by Kevin MacLeod' in x for x in lines) and "Illustration" in lines[-1]
    desc = build_description({"description": "D", "chapters": [{"time": "0:00", "title": "A"}], "footage_credits": lines})
    assert desc.startswith("D\n\n0:00 A") and "Footage and images:" in desc
