import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import captions as C  # noqa: E402

LONG = ("In the harbour, some Venetian and Genoese ships broke out past the chain, packed with refugees "
        "who had escaped the city at the last moment.")


def test_short_sentence_is_one_cue_on_one_line():
    cues = C.build({"sentences": [{"text": "Men pushed.", "start": 1.0, "end": 2.0}]})
    assert cues == [(1.0, 2.0, "Men pushed.")]


def test_long_sentence_splits_into_cues_of_two_short_lines_covering_its_time():
    cues = C.build({"sentences": [{"text": LONG, "start": 10.0, "end": 19.0}]})
    assert len(cues) == 2 and cues[0][0] == 10.0 and abs(cues[-1][1] - 19.0) < 1e-9
    assert all(abs(a[1] - b[0]) < 1e-9 for a, b in zip(cues, cues[1:]))
    for _, _, text in cues:
        lines = text.split("\n")
        assert len(lines) <= 2 and all(len(line) <= C.LINE for line in lines)
    assert " ".join(t.replace("\n", " ") for _, _, t in cues) == LONG


def test_srt_format_and_thai_without_spaces():
    srt = C.to_srt([(0.0, 1.5, "One"), (61.25, 3723.004, "Two")])
    assert srt.startswith("1\n00:00:00,000 --> 00:00:01,500\nOne\n")
    assert "2\n00:01:01,250 --> 01:02:03,004\nTwo\n" in srt
    thai = "กำแพงที่กันศัตรูได้ราวพันปีถูกเจาะได้ในห้าสิบสามวันเพราะปืนใหญ่ที่ไม่มีใครยอมจ่ายเงินซื้อ"
    pieces = C.chunks(thai)
    assert "".join(pieces) == thai and all(len(p) <= C.LINE * C.LINES for p in pieces)


def test_every_line_fits_even_when_words_do_not_balance():
    s = "On the far side of the harbour stood Galata, a town run by merchants from Genoa."
    for _, _, text in C.build({"sentences": [{"text": s, "start": 0, "end": 6}]}):
        assert all(len(line) <= C.LINE for line in text.split("\n"))
