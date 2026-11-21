import json
import sys
from pathlib import Path

import pytest
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.maps import geodata  # noqa: E402
from pipeline.maps import render as R  # noqa: E402


def test_land_is_on_the_left_of_the_coastline():
    # A coast running north along x=5: land is west of it (OSM rule), plus a small island drawn
    # counter-clockwise in the eastern sea.
    coast = [(5, -1), (5, 11)]
    island = [(7, 4), (8, 4), (8, 5), (7, 5), (7, 4)]
    land = geodata.land_from_coastlines([coast, island], (0, 0, 10, 10))
    assert land.contains(Point(2, 5)) and land.contains(Point(7.5, 4.5))
    assert not land.contains(Point(6, 5)) and not land.contains(Point(9, 9))
    assert land.area == pytest.approx(50 + 1)


def test_land_flips_when_the_coast_runs_the_other_way():
    land = geodata.land_from_coastlines([[(5, 11), (5, -1)]], (0, 0, 10, 10))
    assert land.contains(Point(8, 5)) and not land.contains(Point(2, 5))


LIB = {
    "land": "constantinople",
    "features": {
        "walls": {"type": "line", "style": "wall", "side": "byz", "coords": [[28.944, 41.04], [28.92, 40.99]]},
        "city": {"type": "label", "kind": "city", "text": "Constantinople", "at": [28.956, 41.012]},
    },
    "clips": {
        "c": {"duration": 4, "view": [28.88, 40.97, 29.04, 41.06], "title": {"text": "T"},
              "show": [{"use": "city", "appear": 0.5}, {"use": "walls", "draw": [1, 3]}]},
        "bad_feature": {"duration": 2, "view": [28.88, 40.97, 29.04, 41.06], "show": [{"use": "nope"}]},
        "bad_draw": {"duration": 2, "view": [28.88, 40.97, 29.04, 41.06], "show": [{"use": "walls", "draw": [3, 1]}]},
    },
}


@pytest.mark.skipif(not (ROOT / "data" / "geo" / "constantinople.geojson").exists(), reason="geo data not built")
def test_build_props_resolves_features_timing_and_the_osm_credit():
    p = R.build_props(LIB, "c", 1920, 1080)
    assert p["durationSec"] == 4.0 and p["width"] == 1920 and p["title"] == {"text": "T"}
    assert [l["type"] for l in p["layers"]] == ["label", "line"]
    assert p["layers"][0]["appear"] == 0.5 and p["layers"][1]["draw"] == [1, 3]
    assert "draw" not in LIB["features"]["walls"]                    # the library itself is not changed
    assert p["credit"] == "© OpenStreetMap contributors" and "ODbL" in p["_credit_full"]
    assert p["land"]["features"], "land was cut away"
    json.dumps(p)                                                     # props must be plain JSON


def test_build_props_rejects_unknown_features_bad_draw_and_unknown_clips():
    with pytest.raises(R.MapError, match="unknown feature 'nope'"):
        R.build_props(LIB, "bad_feature")
    with pytest.raises(R.MapError, match="start < end"):
        R.build_props(LIB, "bad_draw")
    with pytest.raises(R.MapError, match="no clip"):
        R.build_props(LIB, "missing")


def test_render_inside_an_episode_is_logged_to_its_manifest(tmp_path):
    ep = tmp_path / "episodes" / "2026-12-14-en-x"
    (ep / "render" / "maps").mkdir(parents=True)
    out = ep / "render" / "maps" / "c.mp4"
    assert R.log_to_manifest(out, "c", "Map data © OpenStreetMap contributors (ODbL)")
    assert R.log_to_manifest(out, "c", "Map data © OpenStreetMap contributors (ODbL)")   # re-render: one row
    rows = (ep / "assets" / "manifest.csv").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 2 and rows[1].startswith("map-c,render/maps/c.mp4,own map")
    assert not R.log_to_manifest(tmp_path / "elsewhere.mp4", "c", "")
