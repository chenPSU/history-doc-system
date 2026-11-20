"""Guards for tools/score.py. The v0/v5 fixtures come from docs/narration-experiment.md."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import score  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
ROUNDS = [1, 2, 3, 4, 5]


def mean_score(path):
    r = score.run(str(path), ROUNDS)
    vals = [r["rounds"][k]["score"] for k in ROUNDS]
    return sum(vals) / len(vals), r


def test_metric_count_is_36():
    assert sum(len(score.METRICS[k]) for k in ROUNDS) == 36


def test_v5_beats_v0_by_a_wide_margin():
    m0, _ = mean_score(FIX / "constantinople_v0.md")
    m5, _ = mean_score(FIX / "constantinople_v5.md")
    assert m0 < 40
    assert m5 > 95
    assert m5 - m0 > 50


def test_v5_passes_gate():
    m5, r = mean_score(FIX / "constantinople_v5.md")
    assert m5 >= 90
    assert all(r["rounds"][k]["score"] >= 85 for k in ROUNDS)


def test_number_counting_treats_dates_and_number_phrases_as_one():
    assert score.count_numbers("It began early on 29 May 1453.") == 1
    assert score.count_numbers("Its seven thousand defenders waited.") == 1
    assert score.count_numbers("Sixty oxen pulled it 2 miles.") == 2
