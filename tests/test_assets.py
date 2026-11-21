import csv
import json
import sys
import urllib.error
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.assets import episode as E  # noqa: E402
from pipeline.assets.common import Candidate, FetchError, Http  # noqa: E402
from pipeline.assets.licence import classify  # noqa: E402

JPEG = b"\xff\xd8\xff" + b"0" * 5000


@pytest.mark.parametrize("text,cls", [
    ("pd", "pd"), ("Public domain", "pd"), ("PD-old-100", "pd"), ("No known restrictions on publication.", "pd"),
    ("https://creativecommons.org/publicdomain/mark/1.0/", "pd"), ("cc0", "cc0"),
    ("https://creativecommons.org/publicdomain/zero/1.0/", "cc0"), ("cc-by-4.0", "cc-by"), ("CC BY 2.0", "cc-by"),
    ("https://creativecommons.org/licenses/by/4.0/", "cc-by"), ("cc-by-sa-4.0", "cc-by-sa"),
    ("CC BY-SA 2.0", "cc-by-sa"), ("https://creativecommons.org/licenses/by-nc-sa/4.0/", "nc"),
    ("CC BY-ND 4.0", "nd"), ("GFDL", "unknown"), ("", "unknown"), (None, "unknown"),
    ("All rights reserved", "unknown"),
])
def test_licence_classes(text, cls):
    assert classify(text) == cls


def commons_page(pid, title, lic, short, width=3000, artist="<a href='x'>Fausto Zonaro</a>"):
    return {"pageid": pid, "title": title, "index": pid, "imageinfo": [{
        "width": width, "height": 2000, "mime": "image/jpeg",
        "thumburl": f"https://upload.wikimedia.org/x/{pid}.jpg?utm=1",
        "url": f"https://upload.wikimedia.org/x/{pid}.jpg", "descriptionurl": f"https://commons.wikimedia.org/wiki/{pid}",
        "extmetadata": {"License": {"value": lic}, "LicenseShortName": {"value": short},
                        "Artist": {"value": artist}, "LicenseUrl": {"value": ""}}}]}


class FakeWeb:
    """Answers Commons searches from a dict {search words: [pages]} and serves fake JPEGs."""

    def __init__(self, results):
        self.results, self.queries, self.downloads = results, [], []

    def __call__(self, url, headers):
        assert headers["User-Agent"]
        if "upload.wikimedia.org" in url:
            self.downloads.append(url)
            return JPEG
        q = parse_qs(urlparse(url).query)["gsrsearch"][0].replace(" filetype:bitmap", "")
        self.queries.append(q)
        pages = self.results.get(q, [])
        return json.dumps({"query": {"pages": {str(p["pageid"]): p for p in pages}}} if pages else {}).encode()


CFG = {"bot_name": "TestBot/0", "contact": "test@example.org", "allowed_licences": ["pd", "cc0", "cc-by"], "ia_allowed_licences": ["pd"],
       "width": 3840, "search_limit": 20, "min_width": 1200, "skip_visual_types": ["map", "card", "illustration_ai"],
       "routes": {"painting": ["commons"], "location": ["commons"]}}


def make_ep(tmp, rows):
    ep = tmp / "ep"
    (ep / "assets").mkdir(parents=True)
    with (ep / "shotlist.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sentence_no", "section", "sentence", "visual_type", "search_terms",
                                          "motion", "duration_s", "asset_id"])
        w.writeheader()
        for i, (vt, terms, aid) in enumerate(rows, 1):
            w.writerow({"sentence_no": i, "section": "HOOK", "sentence": f"S{i}.", "visual_type": vt,
                        "search_terms": terms, "motion": "zoom_in", "duration_s": 3, "asset_id": aid})
    return ep


def read(ep, name):
    return list(csv.DictReader((ep / name).open(encoding="utf-8")))


def test_plan_skips_maps_cards_and_filled_shots_without_network(tmp_path):
    ep = make_ep(tmp_path, [("painting", "zonaro conquest", ""), ("map", "walls map", ""),
                            ("painting | map", "bellini mehmed | route map", ""), ("painting", "x", "wm-1")])
    s = E.fetch_episode(ep, CFG, http=Http("t", fetch=lambda *a: pytest.fail("network in plan mode")))
    assert s == {"shots_to_fetch": 2, "already_have": 1, "fetched": 0, "reused": 0, "missed": 0}


def test_fetch_downloads_only_allowed_licences_and_logs_the_manifest(tmp_path):
    web = FakeWeb({
        "zonaro conquest": [commons_page(1, "File:BySa.jpg", "cc-by-sa-4.0", "CC BY-SA 4.0"),
                            commons_page(2, "File:Small.jpg", "pd", "Public domain", width=640),
                            commons_page(3, "File:Zonaro.jpg", "pd", "Public domain")],
        "theodosian walls": [commons_page(4, "File:Walls.jpg", "cc-by-sa-2.0", "CC BY-SA 2.0")],
    })
    ep = make_ep(tmp_path, [("painting", "zonaro conquest", ""), ("location", "theodosian walls drone", ""),
                            ("painting | map", "zonaro conquest | walls map", "")])
    s = E.fetch_episode(ep, CFG, http=Http("t", fetch=web, sleep=lambda s: None), go=True, log=lambda *a: None)
    assert (s["fetched"], s["reused"], s["missed"]) == (1, 1, 1)
    rows = read(ep, "shotlist.csv")
    assert rows[0]["asset_id"] == "wm-3"                  # BY-SA and the 640 px file were skipped
    assert rows[1]["asset_id"] == ""                      # only BY-SA exists -> miss
    assert rows[2]["asset_id"] == "wm-3 | "               # same painting reused; map slot stays empty
    m = read(ep, "assets/manifest.csv")
    assert len(m) == 1 and m[0]["licence"] == "Public domain" and m[0]["source_url"].endswith("/3")
    assert m[0]["credit"] == "Fausto Zonaro, Public domain, via Wikimedia Commons"
    assert (ep / "assets" / "wm-3.jpg").read_bytes() == JPEG and len(web.downloads) == 1
    miss = read(ep, "assets/misses.csv")
    assert miss[0]["licences_seen"] == "cc-by-sa"
    assert "theodosian walls drone" in web.queries and "theodosian walls" in web.queries  # camera word dropped


def test_rerun_fetches_only_the_empty_shots(tmp_path):
    web = FakeWeb({"zonaro conquest": [commons_page(3, "File:Zonaro.jpg", "pd", "Public domain")]})
    ep = make_ep(tmp_path, [("painting", "zonaro conquest", "")])
    http = Http("t", fetch=web, sleep=lambda s: None)
    E.fetch_episode(ep, CFG, http=http, go=True, log=lambda *a: None)
    s = E.fetch_episode(ep, CFG, http=http, go=True, log=lambda *a: None)
    assert s["shots_to_fetch"] == 0 and len(read(ep, "assets/manifest.csv")) == 1


def test_query_variants_drop_camera_words_then_shorten():
    assert E.query_variants("Theodosian walls Istanbul drone dawn") == [
        "Theodosian walls Istanbul drone dawn", "Theodosian walls Istanbul", "Theodosian walls"]


def test_http_backs_off_on_429_and_reports_bot_checks():
    calls = []

    def flaky(url, headers):
        calls.append(url)
        if len(calls) == 1:
            raise urllib.error.HTTPError(url, 429, "slow down", {}, None)
        return b"{}"

    waits = []
    assert Http("t", fetch=flaky, sleep=waits.append).json("https://x") == {}
    assert len(calls) == 2 and 2.0 in waits

    def challenge(url, headers):
        raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)

    with pytest.raises(FetchError, match="403"):
        Http("t", fetch=challenge, sleep=lambda s: None).get("https://www.loc.gov/photos/?fo=json")


def test_asset_id_and_extension():
    c = Candidate("ia", "my item/1", "t", "p", "https://archive.org/download/x/Some%20Name.JPEG", "pd", "PD")
    assert c.asset_id == "ia-my-item-1" and c.extension() == ".jpg"


def test_long_retry_after_stops_the_run_instead_of_waiting(tmp_path):
    def limited(url, headers):
        if "upload.wikimedia.org" in url:
            raise urllib.error.HTTPError(url, 429, "Too many requests", {"Retry-After": "120"}, None)
        return FakeWeb({"zonaro conquest": [commons_page(3, "File:Zonaro.jpg", "pd", "Public domain")]})(url, headers)

    waits = []
    ep = make_ep(tmp_path, [("painting", "zonaro conquest", ""), ("painting", "zonaro conquest", "")])
    s = E.fetch_episode(ep, CFG, http=Http("t", fetch=limited, sleep=waits.append), go=True, log=lambda *a: None)
    assert "429" in s["stopped"] and s["fetched"] == 0 and max(waits) < 30
    assert read(ep, "shotlist.csv")[0]["asset_id"] == ""


def test_user_agent_needs_contact_information(monkeypatch):
    assert E.user_agent(CFG).startswith("TestBot/0 (test@example.org) Python-urllib/")
    monkeypatch.delenv("ASSETS_CONTACT", raising=False)
    monkeypatch.setattr(E, "load_env", lambda: None)   # no .env in this test
    with pytest.raises(ValueError, match="ASSETS_CONTACT"):
        E.user_agent({**CFG, "contact": ""})


def test_shortened_queries_must_stay_on_topic():
    term = "Fausto Zonaro Ottoman fleet transported overland Golden Horn painting"
    woman = Candidate("commons", "1", "File:Fausto Zonaro - Woman Playing a String Instrument.jpg", "", "", "pd", "PD")
    ships = Candidate("commons", "2", "File:Zonaro - Ottoman fleet carried overland to the Golden Horn.jpg", "", "", "pd", "PD")
    assert not E.relevant(woman, term, "Fausto Zonaro Ottoman fleet transported")
    assert E.relevant(ships, term, "Fausto Zonaro Ottoman fleet transported")
    assert E.relevant(woman, term, term)                 # the full term is trusted
    castle = Candidate("commons", "3", "File:Rochester Castle, Kent, England - Norman Keep.jpg", "", "", "pd", "PD")
    assert not E.relevant(castle, "medieval siege crossing a moat engraving", "medieval siege crossing")
    assert E.query_variants("Palma il Giovane conquest of Constantinople 1204 painting")[-1] == "Palma il Giovane conquest"


def test_one_file_is_placed_on_at_most_three_shots(tmp_path):
    web = FakeWeb({"zonaro conquest": [commons_page(3, "File:Zonaro conquest.jpg", "pd", "Public domain")]})
    ep = make_ep(tmp_path, [("painting", "zonaro conquest", "")] * 5)
    s = E.fetch_episode(ep, CFG, http=Http("t", fetch=web, sleep=lambda s: None), go=True, log=lambda *a: None)
    assert (s["fetched"], s["reused"], s["missed"]) == (1, 2, 2)


def test_review_sheet_lists_assets_misses_and_own_shots(tmp_path):
    from pipeline.assets import review
    web = FakeWeb({"zonaro conquest": [commons_page(3, "File:Zonaro conquest.jpg", "pd", "Public domain")]})
    ep = make_ep(tmp_path, [("painting | map", "zonaro conquest | walls map", ""), ("location", "nothing here", "")])
    E.fetch_episode(ep, CFG, http=Http("t", fetch=web, sleep=lambda s: None), go=True, log=lambda *a: None)
    page = review.build(ep).read_text(encoding="utf-8")
    assert 'src="wm-3.jpg"' in page and "1 shots with an asset · 1 without · 1 made by us" in page


def test_broken_download_is_retried():
    import http.client
    calls = []

    def flaky(url, headers):
        calls.append(url)
        if len(calls) == 1:
            raise http.client.IncompleteRead(b"x" * 10, 100)
        return JPEG

    assert Http("t", fetch=flaky, sleep=lambda s: None).get("https://upload.wikimedia.org/a.jpg") == JPEG
