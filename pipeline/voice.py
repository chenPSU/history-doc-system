"""Narration stage (TASKS P2.1).

script.md -> audio/<name>.wav + audio/<name>_timing.json (start/end of every narrated sentence).

How it spends quota (lessons from the Lupas channel, see docs/decisions.md D5):
- One request = a group of consecutive sentences read in one go (up to max_chars_per_request).
  Never one request per line: separate takes sound like different people talking.
- [PAUSE n] cues and section changes split groups and become real silence in the mix.
- Every finished group is cached in audio/.tts-cache by a hash of (provider, model, voice, style, text),
  so a re-run, or a run stopped by --max-requests, never pays twice for the same audio.
- `plan()` says how many requests a run will send before anything is called.

Sentence timing is proportional inside each group (weighted by spoken length, digits count extra).
It is good enough for the shot list; forced alignment (faster-whisper, as in Lupas) can refine it later.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import time
import urllib.error
import urllib.request
import wave
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "voice.yaml"
LEXICON_PATH = ROOT / "data" / "lexicon.yaml"
WPM = 150
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


class VoiceError(Exception):
    pass


class CapReached(VoiceError):
    """--max-requests reached. Groups made so far are cached; run again to continue."""


class QuotaExhausted(VoiceError):
    """Provider says the daily quota is used up. Stop; do not retry."""


class NoAudio(VoiceError):
    """The provider answered but sent no audio. The call still counted against quota."""


class GroupsBlocked(VoiceError):
    """--keep-going run finished, but some groups got no audio. Everything else is cached."""

    def __init__(self, blocked: list[dict], requests: int):
        self.blocked, self.requests = blocked, requests
        lines = "\n".join(f"  group {b['group'] + 1} [{b['section']}]: {b['first']}... ({b['reason']})" for b in blocked)
        super().__init__(f"{len(blocked)} group(s) got no audio after {requests} requests "
                         f"(all other groups are cached; no final file written):\n{lines}")


# ---------------------------------------------------------------- config
def load_env(path: Path = ROOT / ".env") -> None:
    """Minimal .env reader (KEY=VALUE). Existing environment variables win."""
    if not Path(path).exists():
        return
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.split(" #", 1)[0].strip().strip('"').strip("'")
        if v:
            os.environ.setdefault(k.strip(), v)


def load_config(path: Path = CONFIG_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_lexicon(lang: str, path: Path = LEXICON_PATH) -> dict[str, str]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return {w: (e["say"] if isinstance(e, dict) else e) for w, e in (data.get(lang) or {}).items()}


def apply_lexicon(text: str, lexicon: dict[str, str]) -> str:
    for word in sorted(lexicon, key=len, reverse=True):
        text = re.sub(r"(?<![\w-])" + re.escape(word) + r"(?![\w-])", lexicon[word], text)
    return text


# ---------------------------------------------------------------- script -> groups
@dataclass
class Group:
    section: str
    sentences: list[str] = field(default_factory=list)
    pause_after: float = 0.0
    direction: str = ""   # extra director's note for this section (config section_styles)

    @property
    def text(self) -> str:
        return " ".join(self.sentences)


def parse_events(script: Path) -> list[tuple[str, object]]:
    """('section', name) | ('pause', seconds) | ('sentence', text), in script order."""
    ev = []
    started = False
    for raw in Path(script).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or re.match(r"^(TITLE|THUMB|SIGNOFF):", line):
            continue
        if line.startswith("## "):
            ev.append(("section", line[3:].strip().upper()))
            started = True
            continue
        if not started:
            continue
        if line.startswith("["):
            m = re.match(r"^\[PAUSE\s*([\d.]+)", line, re.I)
            if m:
                ev.append(("pause", float(m.group(1))))
            continue  # other cues are production notes, not narration
        if line.startswith("VOICE"):
            raise VoiceError("VOICE lines need a second voice, which pipeline/voice.py does not support yet: " + line[:60])
        for s in SENT_SPLIT.split(line):
            if s.strip():
                ev.append(("sentence", s.strip()))
    return ev


def build_groups(events, max_chars: int, gap_block: float, gap_section: float,
                 sections: set[str] | None = None) -> list[Group]:
    groups: list[Group] = []
    cur: Group | None = None
    section = ""

    def close(pause: float):
        nonlocal cur
        if cur and cur.sentences:
            cur.pause_after = pause
            groups.append(cur)
        cur = None

    for kind, val in events:
        if kind == "section":
            close(gap_section)
            section = val
            continue
        if sections and section not in sections:
            continue
        if kind == "pause":
            if cur and cur.sentences:
                close(val)
            elif groups:
                groups[-1].pause_after = max(groups[-1].pause_after, val)
            continue
        if cur is None:
            cur = Group(section)
        if cur.sentences and len(cur.text) + 1 + len(val) > max_chars:
            close(gap_block)
            cur = Group(section)
        cur.sentences.append(val)
    close(0.0)
    if groups:
        groups[-1].pause_after = 0.0
    return groups


# ---------------------------------------------------------------- audio helpers
def pcm_seconds(pcm: bytes, sr: int) -> float:
    return len(pcm) / 2 / sr


def silence(seconds: float, sr: int) -> bytes:
    return b"\x00\x00" * int(round(seconds * sr))


def trim_silence(pcm: bytes, threshold: int = 300) -> bytes:
    n = len(pcm) // 2
    if n == 0:
        return pcm
    vals = memoryview(pcm).cast("h")
    a, b = 0, n - 1
    while a < n and abs(vals[a]) < threshold:
        a += 1
    while b > a and abs(vals[b]) < threshold:
        b -= 1
    if a >= b:
        return pcm
    return pcm[a * 2:(b + 1) * 2]


def write_wav(path: Path, pcm: bytes, sr: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)


def read_wav(path: Path) -> tuple[bytes, int]:
    with wave.open(str(path), "rb") as w:
        return w.readframes(w.getnframes()), w.getframerate()


def wav_or_pcm(data: bytes) -> bytes:
    if data[:4] == b"RIFF":
        with wave.open(io.BytesIO(data), "rb") as w:
            return w.readframes(w.getnframes())
    return data


def spoken_weight(sentence: str) -> float:
    digits = len(re.findall(r"\d", sentence))
    return len(sentence) + 3 * digits  # "1453" is read as "fourteen fifty-three"


# ---------------------------------------------------------------- providers
def _post_json(url: str, body: dict, headers: dict, opener=urllib.request.urlopen, timeout=180) -> bytes:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with opener(req, timeout=timeout) as r:
        return r.read()


def _with_retries(call, sleep=time.sleep, tries: int = 5):
    for attempt in range(1, tries + 1):
        try:
            return call()
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace") if hasattr(e, "read") else ""
            if e.code == 429 and ("PerDay" in text or "per day" in text.lower()):
                raise QuotaExhausted("daily quota used up; groups made so far are cached. Try again tomorrow.")
            if (e.code == 429 or e.code >= 500) and attempt < tries:
                sleep(min(60, 2 ** attempt))
                continue
            raise VoiceError(f"TTS request failed: HTTP {e.code}: {text[:300]}")


class FakeProvider:
    """No network. Returns a quiet tone as long as the text would take at 150 wpm."""

    name = "fake"

    def __init__(self, sample_rate: int = 24000, wpm: int = WPM):
        self.sr, self.wpm, self.calls = sample_rate, wpm, []

    def identity(self) -> list:
        return ["fake", self.wpm]

    def synth(self, text: str, extra: str = "") -> bytes:
        self.calls.append(text)
        secs = len(text.split()) / self.wpm * 60
        n = int(secs * self.sr)
        return (int(1000).to_bytes(2, "little", signed=True)) * n


class GeminiProvider:
    name = "gemini"
    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    SAFETY_CATEGORIES = ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                         "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]

    def __init__(self, api_key: str, model: str, voice: str, style: str = "", sample_rate: int = 24000,
                 opener=urllib.request.urlopen, sleep=time.sleep, safety: str | None = None):
        self.key, self.model, self.voice, self.style, self.sr = api_key, model, voice, style, sample_rate
        self.opener, self.sleep = opener, sleep
        # War history (sieges, executions) trips the default filters (finishReason SAFETY, 20 Nov 2026).
        # Not part of identity(): it does not change the audio, so cached groups stay valid.
        self.safety = safety

    def identity(self) -> list:
        return ["gemini", self.model, self.voice, self.style, self.sr]

    def synth(self, text: str, extra: str = "") -> bytes:
        if not self.key:
            raise VoiceError("GEMINI_API_KEY is missing in .env")
        notes = " ".join(x for x in (self.style, extra) if x)
        prompt = f"### DIRECTOR'S NOTES\n{notes}\n\n### TRANSCRIPT\n{text}" if notes else text
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {
                    "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": self.voice}}}}}
        if self.safety:
            body["safetySettings"] = [{"category": c, "threshold": self.safety} for c in self.SAFETY_CATEGORIES]
        # One call per synth(): every call that reaches the model counts against the owner's quota, so the
        # caller decides about retrying (and counts it). Earlier code retried silently 3x (20 Nov 2026).
        raw = _with_retries(lambda: _post_json(self.URL.format(model=self.model), body,
                                               {"x-goog-api-key": self.key}, self.opener), self.sleep)
        data = json.loads(raw)
        cand = (data.get("candidates") or [{}])[0]
        parts = (cand.get("content") or {}).get("parts") or []
        part = next((p for p in parts if "inlineData" in p), None)
        if not part:
            said = " ".join(p.get("text", "") for p in parts if "text" in p)[:200]
            flagged = [r for r in cand.get("safetyRatings") or [] if r.get("blocked") or r.get("probability") not in (None, "NEGLIGIBLE")]
            raise NoAudio(f"Gemini returned no audio (finishReason={cand.get('finishReason')!r}, safetyRatings={flagged!r}, "
                          f"promptFeedback={data.get('promptFeedback')!r}, text={said!r}, "
                          f"usage={data.get('usageMetadata')!r}) for {len(text)} chars: {text[:80]}")
        mime = part["inlineData"].get("mimeType", "")
        rate = re.search(r"rate=(\d+)", mime)
        if rate and int(rate.group(1)) != self.sr:
            raise VoiceError(f"Gemini returned {rate.group(1)} Hz, config says {self.sr}: fix sample_rate")
        return wav_or_pcm(base64.b64decode(part["inlineData"]["data"]))


class ElevenLabsProvider:
    name = "elevenlabs"
    URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=pcm_{sr}"

    def __init__(self, api_key: str, voice_id: str, model: str, sample_rate: int = 24000,
                 opener=urllib.request.urlopen, sleep=time.sleep):
        self.key, self.voice, self.model, self.sr = api_key, voice_id, model, sample_rate
        self.opener, self.sleep = opener, sleep

    def identity(self) -> list:
        return ["elevenlabs", self.model, self.voice, self.sr]

    def synth(self, text: str, extra: str = "") -> bytes:  # no prompt-level direction in this API
        if not self.key:
            raise VoiceError("ELEVENLABS_API_KEY is missing in .env")
        if not self.voice:
            raise VoiceError("elevenlabs voice_id is empty in config/voice.yaml (or pass --voice)")
        return _with_retries(lambda: _post_json(self.URL.format(voice=self.voice, sr=self.sr),
                                                {"text": text, "model_id": self.model},
                                                {"xi-api-key": self.key}, self.opener), self.sleep)


def make_provider(lang: str, cfg: dict, provider: str | None = None, voice: str | None = None):
    lc = cfg["languages"][lang]
    name = provider or lc["provider"]
    sr = cfg["sample_rate"]
    if name == "fake":
        return FakeProvider(sr)
    if name == "gemini":
        g = lc["gemini"]
        return GeminiProvider(os.environ.get("GEMINI_API_KEY", ""), g["model"], voice or g["voice"], g.get("style", ""), sr,
                              safety=g.get("safety"))
    if name == "elevenlabs":
        e = lc.get("elevenlabs") or {}
        return ElevenLabsProvider(os.environ.get("ELEVENLABS_API_KEY", ""), voice or e.get("voice_id", ""),
                                  e.get("model", "eleven_multilingual_v2"), sr)
    raise VoiceError(f"unknown provider {name!r}")


# ---------------------------------------------------------------- plan and run
def cache_key(provider, spoken: str, extra: str = "") -> str:
    parts = [provider.identity(), spoken] + ([extra] if extra else [])
    return hashlib.sha1(json.dumps(parts, ensure_ascii=False).encode("utf-8")).hexdigest()[:20]


def section_direction(styles: dict, section: str) -> str:
    """'CHAPTER 3' uses the CHAPTER entry; exact names win."""
    if section in styles:
        return styles[section]
    return styles.get(section.split()[0], "") if section else ""


def prepare(ep: Path, lang: str, cfg: dict, use_lexicon: bool = True, sections: set[str] | None = None):
    events = parse_events(Path(ep) / "script.md")
    groups = build_groups(events, cfg["max_chars_per_request"], cfg["pause_between_blocks"],
                          cfg["pause_between_sections"], sections)
    lex = load_lexicon(lang) if use_lexicon else {}
    lc = cfg["languages"][lang]
    styles = (lc.get(lc["provider"]) or {}).get("section_styles") or {}
    for g in groups:
        g.direction = section_direction(styles, g.section)
    return groups, lex


def plan(ep: Path, provider, groups: list[Group], lex: dict) -> dict:
    cache = Path(ep) / "audio" / ".tts-cache"
    todo = [g for g in groups if not (cache / f"{cache_key(provider, apply_lexicon(g.text, lex), g.direction)}.wav").exists()]
    words = sum(len(g.text.split()) for g in groups)
    return {"groups": len(groups), "requests_needed": len(todo), "cached": len(groups) - len(todo),
            "characters_to_send": sum(len(apply_lexicon(g.text, lex)) for g in todo),
            "words": words, "estimated_seconds": round(words / WPM * 60 + sum(g.pause_after for g in groups), 1)}


def synthesize(ep: Path, provider, groups: list[Group], lex: dict, sr: int, max_requests: int,
               out_name: str = "narration", log=print, keep_going: bool = False) -> dict:
    ep = Path(ep)
    cache = ep / "audio" / ".tts-cache"
    cache.mkdir(parents=True, exist_ok=True)
    pieces, requests, blocked = [], 0, []
    for i, g in enumerate(groups):
        spoken = apply_lexicon(g.text, lex)
        f = cache / f"{cache_key(provider, spoken, g.direction)}.wav"
        if f.exists():
            pcm, _ = read_wav(f)
        else:
            if requests >= max_requests:
                raise CapReached(f"stopped at the cap of {max_requests} requests ({i}/{len(groups)} groups done, all cached). "
                                 "Run again with a higher --max-requests to continue.")
            requests += 1
            log(f"  request {requests}: group {i + 1}/{len(groups)} [{g.section}] {len(spoken)} chars")
            try:
                pcm = trim_silence(provider.synth(spoken, g.direction))
            except NoAudio as e:
                if not keep_going:
                    raise
                reason = str(e).split(" for ", 1)[0]
                blocked.append({"group": i, "section": g.section, "first": g.text[:60], "reason": reason[:160]})
                log(f"    no audio: {reason[:120]}")
                pieces.append(None)
                continue
            write_wav(f, pcm, sr)
        pieces.append(pcm)
    if blocked:
        report = ep / "audio" / f"{out_name}_blocked.json"
        report.write_text(json.dumps([{**b, "text": groups[b["group"]].text} for b in blocked],
                                     ensure_ascii=False, indent=1), encoding="utf-8")
        raise GroupsBlocked(blocked, requests)

    audio, t, blocks, sents = [], 0.0, [], []
    for i, (g, pcm) in enumerate(zip(groups, pieces)):
        dur = pcm_seconds(pcm, sr)
        weights = [spoken_weight(s) for s in g.sentences]
        total_w = sum(weights) or 1
        at = t
        for s, w in zip(g.sentences, weights):
            d = dur * w / total_w
            sents.append({"i": len(sents), "section": g.section, "group": i, "text": s,
                          "start": round(at, 3), "end": round(at + d, 3)})
            at += d
        blocks.append({"group": i, "section": g.section, "start": round(t, 3), "end": round(t + dur, 3),
                       "pause_after": g.pause_after})
        audio += [pcm, silence(g.pause_after, sr)]
        t += dur + g.pause_after

    out_dir = ep / "audio"
    write_wav(out_dir / f"{out_name}.wav", b"".join(audio), sr)
    words = sum(len(g.text.split()) for g in groups)
    estimate = words / WPM * 60
    timing = {"audio": f"audio/{out_name}.wav", "provider": provider.identity()[:3], "sample_rate": sr,
              "total_seconds": round(t, 2), "scorer_estimate_seconds": round(estimate, 1),
              "ratio_to_estimate": round(t / estimate, 3) if estimate else None,
              "timing_method": "proportional within each request group",
              "requests_sent": requests, "groups": blocks, "sentences": sents}
    (out_dir / f"{out_name}_timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
    return timing
