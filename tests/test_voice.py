"""Tests for pipeline/voice.py. No network: fake provider and fake HTTP responses only."""
import base64
import io
import json
import sys
import urllib.error
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import voice  # noqa: E402

CFG = {"sample_rate": 24000, "max_chars_per_request": 200, "max_requests_default": 30,
       "pause_between_blocks": 0.35, "pause_between_sections": 0.8,
       "languages": {"en": {"provider": "fake", "gemini": {"model": "m", "voice": "Charon", "style": "calm"}}}}

SCRIPT = """TITLE: T
THUMB: X
SIGNOFF: Bye.
## HOOK
[MIX: voice leads]
[MUSIC: drone, instrumental]
It is just after midnight, on 29 May 1453.
Giustiniani waits on the wall. Galata sleeps.
[PAUSE 1.5]
How did it fall?
## CONTEXT
[SOUND BRIDGE: gulls]
Constantinople was a Roman city. It lasted a thousand years.
"""


def make_ep(tmp: Path, text: str = SCRIPT) -> Path:
    ep = tmp / "ep"
    ep.mkdir()
    (ep / "script.md").write_text(text, encoding="utf-8")
    return ep


def groups_of(ep, max_chars=200, sections=None):
    return voice.build_groups(voice.parse_events(ep / "script.md"), max_chars, 0.35, 0.8, sections)


def test_cues_are_not_spoken_and_pauses_split_groups(tmp_path):
    g = groups_of(make_ep(tmp_path))
    assert [x.section for x in g] == ["HOOK", "HOOK", "CONTEXT"]
    assert g[0].sentences == ["It is just after midnight, on 29 May 1453.", "Giustiniani waits on the wall.", "Galata sleeps."]
    assert g[0].pause_after == 1.5          # the [PAUSE 1.5] cue
    assert g[1].pause_after == 0.8          # section change
    assert g[2].pause_after == 0.0          # nothing after the last group
    assert not any("MUSIC" in s or "MIX" in s for x in g for s in x.sentences)


def test_long_paragraphs_are_grouped_up_to_the_char_limit_not_per_line(tmp_path):
    body = "\n".join(f"This is sentence number {i} of a long chapter." for i in range(30))
    ep = make_ep(tmp_path, "## CHAPTER 1\n" + body + "\n")
    g = groups_of(ep, max_chars=200)
    assert all(len(x.text) <= 200 for x in g)
    assert 5 <= len(g) <= 8                 # ~4 sentences per request, never 30 requests
    assert sum(len(x.sentences) for x in g) == 30


def test_sections_filter_for_listening_samples(tmp_path):
    g = groups_of(make_ep(tmp_path), sections={"HOOK"})
    assert {x.section for x in g} == {"HOOK"} and g[-1].pause_after == 0.0


def test_lexicon_changes_only_whole_words(tmp_path):
    lex = {"Galata": "GAH-lah-tah", "Chios": "KEE-os"}
    assert voice.apply_lexicon("Galata sleeps. Galatasaray plays. Chios.", lex) == "GAH-lah-tah sleeps. Galatasaray plays. KEE-os."


def test_project_lexicon_loads():
    lex = voice.load_lexicon("en")
    assert lex["Giustiniani"] == "Joo-stee-NYAH-nee"


def test_voice_lines_are_refused_until_a_second_voice_exists(tmp_path):
    ep = make_ep(tmp_path, '## HOOK\nVOICE (Barbaro): "The Turks came."\n')
    with pytest.raises(voice.VoiceError):
        voice.parse_events(ep / "script.md")


def test_plan_sends_nothing_and_counts_requests(tmp_path):
    ep = make_ep(tmp_path)
    prov = voice.FakeProvider()
    g = groups_of(ep)
    p = voice.plan(ep, prov, g, {})
    assert p["requests_needed"] == 3 and p["cached"] == 0 and prov.calls == []


def test_synthesize_writes_wav_and_sentence_timing(tmp_path):
    ep = make_ep(tmp_path)
    prov = voice.FakeProvider()
    g = groups_of(ep)
    t = voice.synthesize(ep, prov, g, {"Galata": "GAH-lah-tah"}, 24000, max_requests=10, log=lambda *_: None)
    assert (ep / "audio" / "narration.wav").exists()
    saved = json.loads((ep / "audio" / "narration_timing.json").read_text(encoding="utf-8"))
    assert saved["requests_sent"] == 3 and len(saved["sentences"]) == 6
    starts = [s["start"] for s in saved["sentences"]]
    assert starts == sorted(starts)
    assert saved["sentences"][0]["text"].startswith("It is just after")      # captions keep the real spelling
    assert "GAH-lah-tah sleeps." in prov.calls[0]                             # TTS got the respelling
    # the [PAUSE 1.5] is real silence between group 0 and group 1
    assert saved["groups"][1]["start"] - saved["groups"][0]["end"] == pytest.approx(1.5, abs=0.01)
    assert 0.9 < t["ratio_to_estimate"] < 1.3


def test_cache_means_a_rerun_sends_nothing(tmp_path):
    ep = make_ep(tmp_path)
    g = groups_of(ep)
    voice.synthesize(ep, voice.FakeProvider(), g, {}, 24000, 10, log=lambda *_: None)
    again = voice.FakeProvider()
    t = voice.synthesize(ep, again, g, {}, 24000, 10, log=lambda *_: None)
    assert again.calls == [] and t["requests_sent"] == 0
    assert voice.plan(ep, again, g, {})["requests_needed"] == 0


def test_request_cap_stops_and_keeps_what_was_made(tmp_path):
    ep = make_ep(tmp_path)
    g = groups_of(ep)
    prov = voice.FakeProvider()
    with pytest.raises(voice.CapReached):
        voice.synthesize(ep, prov, g, {}, 24000, max_requests=2, log=lambda *_: None)
    assert len(prov.calls) == 2
    assert voice.plan(ep, prov, g, {})["requests_needed"] == 1


# ---------------------------------------------------------------- Gemini response handling (fake HTTP)
class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def gemini_body(pcm: bytes, mime="audio/L16;codec=pcm;rate=24000"):
    return json.dumps({"candidates": [{"content": {"parts": [{"inlineData": {
        "mimeType": mime, "data": base64.b64encode(pcm).decode()}}]}}]}).encode()


def test_gemini_raw_pcm_and_wav_answers(tmp_path):
    pcm = b"\x10\x00" * 2400
    sent = []

    def opener(req, timeout):
        sent.append(json.loads(req.data))
        assert req.get_header("X-goog-api-key") == "k"
        return FakeResp(gemini_body(pcm))

    g = voice.GeminiProvider("k", "m", "Charon", "calm", 24000, opener=opener)
    assert g.synth("Hello.") == pcm
    assert "### TRANSCRIPT\nHello." in sent[0]["contents"][0]["parts"][0]["text"]
    assert sent[0]["generationConfig"]["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"] == "Charon"

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(24000), w.writeframes(pcm)
    g2 = voice.GeminiProvider("k", "m", "Charon", "", 24000, opener=lambda r, timeout: FakeResp(gemini_body(buf.getvalue(), "audio/wav")))
    assert g2.synth("Hi.") == pcm


def test_gemini_missing_key_fails_only_when_sending():
    g = voice.GeminiProvider("", "m", "Charon")
    assert g.identity()[0] == "gemini"           # a plan can still be made
    with pytest.raises(voice.VoiceError):
        g.synth("x")


def test_daily_quota_stops_without_retrying():
    calls = []

    def opener(req, timeout):
        calls.append(1)
        raise urllib.error.HTTPError(req.full_url, 429, "quota", {}, io.BytesIO(b'{"quotaId": "GenerateRequestsPerDayPerProject"}'))

    g = voice.GeminiProvider("k", "m", "Charon", opener=opener, sleep=lambda s: None)
    with pytest.raises(voice.QuotaExhausted):
        g.synth("x")
    assert len(calls) == 1


def test_rate_limit_is_retried():
    calls = []

    def opener(req, timeout):
        calls.append(1)
        if len(calls) < 3:
            raise urllib.error.HTTPError(req.full_url, 429, "slow down", {}, io.BytesIO(b"per minute"))
        return FakeResp(gemini_body(b"\x01\x00" * 10))

    g = voice.GeminiProvider("k", "m", "Charon", opener=opener, sleep=lambda s: None)
    assert g.synth("x") == b"\x01\x00" * 10 and len(calls) == 3


def test_no_audio_answer_costs_exactly_one_call_and_reports_why():
    # Regression (20 Nov 2026): the provider used to retry a no-audio answer 3 times while the run counted 1 request.
    calls = []

    def opener(req, timeout):
        calls.append(1)
        return FakeResp(json.dumps({"candidates": [{"finishReason": "OTHER", "content": {"parts": []}}]}).encode())

    g = voice.GeminiProvider("k", "m", "Charon", opener=opener, sleep=lambda s: None)
    with pytest.raises(voice.NoAudio) as e:
        g.synth("x")
    assert len(calls) == 1 and "OTHER" in str(e.value)


def test_safety_threshold_is_sent_but_does_not_change_the_cache_key():
    sent = []

    def opener(req, timeout):
        sent.append(json.loads(req.data))
        return FakeResp(gemini_body(b"\x01\x00" * 10))

    plain = voice.GeminiProvider("k", "m", "Charon", "calm", opener=opener)
    relaxed = voice.GeminiProvider("k", "m", "Charon", "calm", opener=opener, safety="BLOCK_ONLY_HIGH")
    plain.synth("a")
    relaxed.synth("a")
    assert "safetySettings" not in sent[0]
    assert {s["threshold"] for s in sent[1]["safetySettings"]} == {"BLOCK_ONLY_HIGH"}
    assert len(sent[1]["safetySettings"]) == 4
    assert voice.cache_key(plain, "a") == voice.cache_key(relaxed, "a")


class PickyProvider(voice.FakeProvider):
    """Refuses any text containing 'attacker', like the Gemini safety filter on 20 Nov 2026."""

    def synth(self, text):
        if "attacker" in text:
            self.calls.append(text)
            raise voice.NoAudio("Gemini returned no audio (finishReason='SAFETY') for x")
        return super().synth(text)


def test_keep_going_skips_refused_groups_keeps_the_rest_and_lists_them(tmp_path):
    ep = make_ep(tmp_path, SCRIPT.replace("Giustiniani waits on the wall.", "Picture yourself as an attacker."))
    g = groups_of(ep)
    prov = PickyProvider()
    with pytest.raises(voice.GroupsBlocked) as e:
        voice.synthesize(ep, prov, g, {}, 24000, 10, log=lambda *_: None, keep_going=True)
    assert [b["group"] for b in e.value.blocked] == [0] and e.value.requests == 3
    assert not (ep / "audio" / "narration.wav").exists()
    report = json.loads((ep / "audio" / "narration_blocked.json").read_text(encoding="utf-8"))
    assert "attacker" in report[0]["text"]
    assert voice.plan(ep, prov, g, {})["requests_needed"] == 1      # only the refused group is left


def test_without_keep_going_the_first_refusal_stops_the_run(tmp_path):
    ep = make_ep(tmp_path, SCRIPT.replace("Giustiniani waits on the wall.", "Picture yourself as an attacker."))
    with pytest.raises(voice.NoAudio):
        voice.synthesize(ep, PickyProvider(), groups_of(ep), {}, 24000, 10, log=lambda *_: None)
