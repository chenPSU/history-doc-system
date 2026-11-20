import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import shotlist  # noqa: E402

SCRIPT = """TITLE: T
## HOOK
[MUSIC: drone, instrumental]
It is night. The walls wait in the dark.
## CONTEXT
[TONE: intimate]
Constantinople was a Roman city that had stood for a very long time on the edge of two continents and two seas and many centuries of history.
"""


def make_ep(tmp: Path) -> Path:
    ep = tmp / "ep"
    ep.mkdir()
    (ep / "script.md").write_text(SCRIPT, encoding="utf-8")
    return ep


def rows(ep):
    return list(csv.DictReader((ep / "shotlist.csv").open(encoding="utf-8")))


def fill(ep, values):
    rs = rows(ep)
    for r, (vt, st, mo) in zip(rs, values):
        r.update(visual_type=vt, search_terms=st, motion=mo)
    shotlist.write_rows(ep / "shotlist.csv", rs)


def test_init_makes_one_row_per_spoken_sentence_and_keeps_filled_work(tmp_path):
    ep = make_ep(tmp_path)
    shotlist.init(ep)
    rs = rows(ep)
    assert [r["sentence"] for r in rs] == ["It is night.", "The walls wait in the dark.", rs[2]["sentence"]]
    assert rs[0]["section"] == "HOOK" and not any("MUSIC" in r["sentence"] or "TONE" in r["sentence"] for r in rs)
    fill(ep, [("map", "city at night", "zoom_in")] * 3)
    shotlist.init(ep)                                   # re-run after a script edit must not wipe work
    assert rows(ep)[0]["visual_type"] == "map"


def test_check_flags_empty_unknown_and_long_shots(tmp_path):
    ep = make_ep(tmp_path)
    shotlist.init(ep)
    fill(ep, [("map", "walls at night", "zoom_in"), ("photo", "torch", "zoom_in"), ("painting", "city", "zoom_out")])
    errors, warnings = shotlist.check(ep)
    assert any("unknown visual_type 'photo'" in e for e in errors)
    assert any("> 10s" in e for e in errors)            # the 28-word sentence is ~11 s as one still
    assert any("two zoom_in shots in a row" in w for w in warnings)


def test_splitting_a_long_sentence_into_shots_passes(tmp_path):
    ep = make_ep(tmp_path)
    shotlist.init(ep)
    fill(ep, [("map", "walls at night", "zoom_in"), ("location", "torch", "zoom_out"),
              ("painting", "panorama of the city | map of the straits", "pan_left | map_anim")])
    errors, _ = shotlist.check(ep)
    assert errors == []


def test_check_refuses_a_stale_shotlist(tmp_path):
    ep = make_ep(tmp_path)
    shotlist.init(ep)
    (ep / "script.md").write_text(SCRIPT + "A new line.\n", encoding="utf-8")
    errors, _ = shotlist.check(ep)
    assert errors and "run init" in errors[0]
