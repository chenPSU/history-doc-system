#!/usr/bin/env python3
"""Narrate an episode script (TASKS P2.1). Default is a PLAN: nothing is sent, nothing is paid.

  python tools/voice.py episodes/<ep>                                  # plan: how many requests, how long
  python tools/voice.py episodes/<ep> --go --max-requests 5            # really call the provider, at most 5 requests
  python tools/voice.py episodes/<ep> --go --sections HOOK,PROMISE --provider gemini --voice Orus --out test_gemini_orus
  python tools/voice.py episodes/<ep> --go --provider fake             # offline test audio (silence-length tone)

Output: audio/<out>.wav and audio/<out>_timing.json. Finished request groups are cached in audio/.tts-cache.
Always run the plan first and tell the owner the request count before --go (paid quota).
"""
import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import voice  # noqa: E402


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--go", action="store_true", help="call the TTS provider (default: plan only)")
    ap.add_argument("--max-requests", type=int, help="hard cap for this run (default from config/voice.yaml)")
    ap.add_argument("--provider", choices=["gemini", "elevenlabs", "fake"])
    ap.add_argument("--voice", help="override the voice name (Gemini) or voice_id (ElevenLabs)")
    ap.add_argument("--sections", help="only these sections, e.g. HOOK,PROMISE")
    ap.add_argument("--out", default="narration", help="output name inside audio/")
    ap.add_argument("--no-lexicon", action="store_true")
    ap.add_argument("--keep-going", action="store_true",
                    help="skip groups the provider refuses (e.g. safety), keep the rest, list the refused ones")
    a = ap.parse_args(argv)

    ep = Path(a.episode)
    brief = yaml.safe_load((ep / "brief.yaml").read_text(encoding="utf-8")) or {}
    lang = brief.get("language")
    cfg = voice.load_config()
    voice.load_env()
    sections = {s.strip().upper() for s in a.sections.split(",")} if a.sections else None
    try:
        groups, lex = voice.prepare(ep, lang, cfg, not a.no_lexicon, sections)
        prov = voice.make_provider(lang, cfg, a.provider, a.voice)  # keys are checked only when sending
        p = voice.plan(ep, prov, groups, lex)
        cap = a.max_requests if a.max_requests is not None else cfg["max_requests_default"]
        print(f"{ep.name} [{lang}] provider={prov.name} groups={p['groups']} cached={p['cached']} "
              f"requests_needed={p['requests_needed']} chars={p['characters_to_send']} "
              f"words={p['words']} estimated={p['estimated_seconds'] / 60:.1f} min  cap={cap}")
        if not a.go:
            print("PLAN ONLY. Add --go to call the provider.")
            return 0
        t = voice.synthesize(ep, prov, groups, lex, cfg["sample_rate"], cap, a.out, keep_going=a.keep_going)
        print(f"Done: {t['audio']}  {t['total_seconds'] / 60:.1f} min, {t['requests_sent']} requests sent, "
              f"ratio to scorer estimate {t['ratio_to_estimate']}")
        return 0
    except voice.VoiceError as e:
        print(f"STOP: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
