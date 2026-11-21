import csv
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import images as I  # noqa: E402
from pipeline.voice import QuotaExhausted  # noqa: E402

CFG = I.load_config()
COLS = ["sentence_no", "section", "sentence", "visual_type", "search_terms", "motion", "duration_s", "asset_id"]


def make_ep(tmp_path, rows):
    ep = tmp_path / "episodes" / "2026-12-14-en-x"
    (ep / "assets").mkdir(parents=True)
    with (ep / "shotlist.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for no, vt, terms in rows:
            w.writerow({"sentence_no": no, "section": "CHAPTER 1", "sentence": f"Sentence {no}.", "visual_type": vt,
                        "search_terms": terms, "motion": "zoom_in", "duration_s": "4", "asset_id": ""})
    return ep


def shot_assets(ep):
    with (ep / "shotlist.csv").open(encoding="utf-8", newline="") as f:
        return {int(r["sentence_no"]): r["asset_id"] for r in csv.DictReader(f)}


def test_init_takes_only_ai_shots_strips_prefixes_and_keeps_edits(tmp_path):
    ep = make_ep(tmp_path, [(1, "painting", "Zonaro"), (2, "illustration_ai", "Illustration: fire boats at night, old-print style"),
                            (3, "illustration_ai", "old print style: oxen hauling a galley")])
    p, added = I.init_prompts(ep, CFG)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert added == 2 and set(data["shots"]) == {2, 3}
    assert data["shots"][2]["subject"] == "Fire boats at night" and data["shots"][3]["subject"] == "Oxen hauling a galley"
    data["shots"][2]["subject"] = "Edited by hand"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert I.init_prompts(ep, CFG)[1] == 0
    assert yaml.safe_load(p.read_text(encoding="utf-8"))["shots"][2]["subject"] == "Edited by hand"


def test_prompt_always_carries_style_and_the_no_real_person_rules():
    p = I.build_prompt("Fire boats at night", "Constantinople, 1453", "engraving", CFG)
    assert "engraving" in p and "Scene: Fire boats at night." in p and "Setting: Constantinople, 1453" in p
    assert "no recognisable historical person" in p and "never photorealistic" in p
    with pytest.raises(I.ImageError, match="unknown style"):
        I.build_prompt("x", "", "oil", CFG)


@pytest.mark.parametrize("subject,why", [
    ("A photorealistic siege", "realism"), ("Portrait of a soldier", "portrait"), ("The sultan on horseback", "ruler"),
    ("Mehmed watching the ships", "real person"), ("A close-up of a miner", "portrait"), ("", "empty"),
])
def test_guard_refuses_realism_rulers_and_named_people(subject, why):
    out = I.problems(subject, "", CFG, ["Mehmed", "Constantine"])
    assert out and any(why in o for o in out)


def test_guard_allows_anonymous_crowds():
    assert I.problems("Crowd of men pushing a galley; kings' banners far away", "Ottoman army, 1453", CFG, ["Mehmed"]) == []


def test_dry_run_sends_nothing_then_go_makes_logs_and_never_repeats(tmp_path):
    ep = make_ep(tmp_path, [(5, "illustration_ai", "Illustration: fire boats"), (6, "illustration_ai", "Illustration: a tunnel")])
    I.init_prompts(ep, CFG)
    fake = I.FakeImage()
    res = I.generate(ep, CFG, fake)
    assert res["planned"] == [5, 6] and fake.calls == [] and not (ep / "assets" / "manifest.csv").exists()
    res = I.generate(ep, CFG, fake, go=True)
    assert res["made"] == [5, 6] and res["requests"] == 2
    rows = {r["asset_id"]: r for r in csv.DictReader((ep / "assets" / "manifest.csv").open(encoding="utf-8"))}
    assert rows["ai-005"]["ai_generated"] == "y" and "label=Illustration" in rows["ai-005"]["notes"]
    assert rows["ai-005"]["licence"] and rows["ai-005"]["source_url"]          # the upload preflight needs both
    assert (ep / "assets" / "ai-005.png").exists() and shot_assets(ep)[5] == "ai-005"
    assert I.check(ep, CFG) == []
    assert I.generate(ep, CFG, fake, go=True)["requests"] == 0                 # nothing new: no request
    # editing a subject redoes only that shot
    p = I.prompts_path(ep)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    data["shots"][6]["subject"] = "A narrow tunnel lit by one torch"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert [i.no for i in I.plan(ep, CFG) if i.status == "todo"] == [6]
    assert I.check(ep, CFG) == ["#6: no image for the current prompt"]


def test_refused_prompt_is_never_sent_and_fails_check(tmp_path):
    ep = make_ep(tmp_path, [(7, "illustration_ai", "Illustration: the emperor on the wall")])
    I.init_prompts(ep, CFG)
    fake = I.FakeImage()
    res = I.generate(ep, CFG, fake, go=True)
    assert res["refused"] == [7] and fake.calls == []
    assert "prompt refused" in I.check(ep, CFG)[0]


def test_max_requests_and_quota_stop(tmp_path):
    ep = make_ep(tmp_path, [(n, "illustration_ai", f"Illustration: scene {n}") for n in (1, 2, 3)])
    I.init_prompts(ep, CFG)
    assert I.generate(ep, CFG, I.FakeImage(), go=True, max_requests=1)["made"] == [1]

    class Broke:
        calls = 0

        def generate(self, prompt):
            Broke.calls += 1
            raise QuotaExhausted("daily quota used up")
    res = I.generate(ep, CFG, Broke(), go=True)
    assert Broke.calls == 1 and res["failed"] == [2] and res["made"] == []


def test_new_ai_shot_without_a_prompt_entry_is_an_error(tmp_path):
    ep = make_ep(tmp_path, [(1, "illustration_ai", "Illustration: a")])
    I.init_prompts(ep, CFG)
    with (ep / "shotlist.csv").open("a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow([2, "CHAPTER 1", "S.", "illustration_ai", "Illustration: b", "zoom_in", "4", ""])
    with pytest.raises(I.ImageError, match="no entry"):
        I.plan(ep, CFG)


def test_ai_sub_shots_get_their_own_prompt_asset_and_cell(tmp_path):
    ep = make_ep(tmp_path, [(2, "illustration_ai | painting | illustration_ai", "Illustration: a | b | Illustration: c")])
    I.init_prompts(ep, CFG)
    data = yaml.safe_load(I.prompts_path(ep).read_text(encoding="utf-8"))
    assert set(map(str, data["shots"])) == {"2.1", "2.3"} and data["shots"]["2.3"]["subject"] == "C"
    res = I.generate(ep, CFG, I.FakeImage(), go=True)
    assert res["requests"] == 2
    assert shot_assets(ep)[2] == "ai-002-1 |  | ai-002-3"
    assert (ep / "assets" / "ai-002-3.png").exists() and I.check(ep, CFG) == []
