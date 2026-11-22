"""Guards for tools/score_th.py (TASKS P1.5). The Thai fixtures are faithful translations of the v0/v5 pair:
v0_th keeps v0's faults (long sentences, 'แล้วก็' links, 'ในคลิปนี้' opener, generic CTA), v5_th follows v5."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import score  # noqa: E402
import score_th as T  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
ROUNDS = [1, 2, 3, 4, 5]


def mean_score(path, lang=None):
    r = score.run(str(path), ROUNDS, lang)
    vals = [r["rounds"][k]["score"] for k in ROUNDS]
    return sum(vals) / len(vals), r


def test_thai_scripts_are_detected_and_scored_by_the_thai_rules():
    _, r = mean_score(FIX / "constantinople_v5_th.md")
    assert r["base"]["language"] == "th"
    _, e = mean_score(FIX / "constantinople_v5.md")
    assert "language" not in e["base"]                      # English stays on the English rules
    assert sum(len(T.METRICS[k]) for k in ROUNDS) == 37      # 36 English metrics, Flesch split into 2 breath-group metrics


def test_thai_pair_scores_like_the_english_pair():
    m0, _ = mean_score(FIX / "constantinople_v0_th.md")
    m5, r = mean_score(FIX / "constantinople_v5_th.md")
    e0, _ = mean_score(FIX / "constantinople_v0.md")
    e5, _ = mean_score(FIX / "constantinople_v5.md")
    assert m0 < 40 and m5 > 95 and m5 - m0 > 50
    assert abs(m0 - e0) < 10 and abs(m5 - e5) < 5


def test_thai_v5_passes_the_gate_with_no_zero_metric():
    m5, r = mean_score(FIX / "constantinople_v5_th.md")
    assert m5 >= 90 and all(r["rounds"][k]["score"] >= 85 for k in ROUNDS)
    assert not [x for k in ROUNDS for x in r["rounds"][k]["rows"] if x["score"] == 0]


def test_reading_time_reads_numbers_out():
    assert T.syllables("1453") == T.syllables("หนึ่งพันสี่ร้อยห้าสิบสาม") == 7
    assert T.syllables("ค.ศ. 330") == T.syllables("คริสต์ศักราช สามร้อยสามสิบ")
    assert T.syllables("เมห์เมต") == 2                      # a lone final consonant is not a syllable


def test_breath_groups_split_on_spaces_but_keep_dates_together():
    assert T.phrases("ตอนนี้ตีหนึ่งครึ่ง ของวันที่ 29 พฤษภาคม 1453") == ["ตอนนี้ตีหนึ่งครึ่ง", "ของวันที่ 29 พฤษภาคม 1453"]


def test_thai_number_counting():
    assert T.count_numbers("การบุกเริ่มขึ้น ตั้งแต่เช้ามืดวันที่ 29 พฤษภาคม 1453") == 1
    assert T.count_numbers("ทหารเจ็ดพันคน ยืนเฝ้ากำแพง") == 1
    assert T.count_numbers("คอนสแตนตินที่สิบเอ็ด สิ้นชีวิต") == 0          # ordinal
    assert T.count_numbers("ต้องใช้วัวหกสิบตัว กับคนอีกหลายร้อย") == 1       # vague 'หลายร้อย' is not a figure
    assert T.count_numbers("อูร์บานสร้างปีศาจขึ้นมาตัวหนึ่ง") == 0          # 'หนึ่ง' as an article
    assert T.count_numbers("วัวหกสิบตัว ลากมันไป 2 ไมล์") == 2


def test_names_inside_longer_names_do_not_count():
    every = ["คอนสแตนติน", "คอนสแตนติโนเปิล"]
    assert not T.has_name("คอนสแตนติน", "เมืองคอนสแตนติโนเปิล", every)
    assert T.has_name("คอนสแตนติน", "คอนสแตนตินวิงวอน", every)


def test_thai_questions_without_a_question_mark():
    assert T.is_question("เขาทำได้อย่างไร") and T.is_question("ใครจะเชื่อ?")
    assert not T.is_question("เขาสร้างป้อม")
