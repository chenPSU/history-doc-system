# Decisions

Status: `DECIDED` (date, who) or `OPEN` (recommendation + options). Claude Code: confirm every OPEN item with the owner before building on it.

## D1 · Channel format: history documentary, EN main + TH second — DECIDED (Nov 2026, owner)
Top-ranked of 5 formats (score 4.40/5). See `docs/market-research.md`.

## D2 · Script rules and scorer — DECIDED (19 Nov 2026)
`tools/score.py` (36 metrics, 5 rounds) from `docs/narration-experiment.md`. Gate: each round ≥ 85, mean ≥ 90. To be re-calibrated against real retention (TASKS P6.3).

## D3 · Pipeline language — DECIDED: Python 3.11
Orchestration, scoring, asset fetching, audio mixing (ffmpeg).

## D4 · Render engine — DECIDED (20 Nov 2026, owner): Remotion
React/TypeScript renders the video (maps, year counters, chapter cards, Ken Burns, captions) as code, so episodes are repeatable and easy to vary. Python stays the orchestrator (D3) and calls the Remotion render.
- The owner already runs Remotion on this machine (LupasProject), so the toolchain is proven on Windows.
- Licence: free for individuals and companies with up to 3 employees. Re-check if the business grows past that.
- Rejected: Python + ffmpeg/MoviePy (weak for animated maps and text), HyperFrames (unproven here, too risky for 14 Dec), DaVinci Resolve EDL (manual finishing does not scale to 4 long videos/week).

## D5 · Narration voice — DECIDED (20 Nov 2026, owner)
- **EN: listening test first.** Before P2.1 (~1 Dec), render the Constantinople hook (~1 min) with Gemini TTS and with ElevenLabs (free tiers only) and the owner picks by ear. Then fill `TTS_PROVIDER` / `TTS_VOICE_EN`. Rough costs at ~200k characters/month (9 x 25 min): Gemini about $5/month; ElevenLabs about $99/month plan. Check current prices and get the owner's yes before any paid plan. The owner signs up for ElevenLabs themself.
- **TH: Gemini TTS + pronunciation lexicon** (`data/lexicon.yaml`, P2.2). Same provider the owner already approved by ear for Lupas, but a **different voice from QURIO** so the channels don't sound the same. Revisit a human narrator at gate G1 if the channel is working.
- Gemini TTS needs billing on (the free tier is 10 requests/day). Lessons from Lupas: one request per paragraph, not per line (per-line takes sound disjointed); always print the request count with `--plan` and cap with `--max-requests` before a run; never re-run a quota-burning call without asking.
- Never clone or imitate a real person's voice.

## D6 · Music — DECIDED (20 Nov 2026, owner): free sources first
- YouTube Audio Library (monetisation allowed; record any attribution it requires) and classical music whose **recording** is public domain or CC0 (e.g. Musopen). Instrumental only (no lyrics). Log the licence and source URL per track.
- Known risk: some PD recordings get false Content ID claims; dispute them with the licence record.
- Revisit a paid library (Epidemic Sound / Artlist, ~$10-20/month) when tracks start repeating across episodes. Owner's yes required before subscribing.

## D7 · AI images — DECIDED (20 Nov 2026, owner): Gemini image generation
Same Google account as TTS, called by API inside the pipeline (P3.4). Rough cost ~$0.04/image, ~10-20 images/episode (under $1), reused for TH. Images carry a SynthID watermark, which is fine because AI images are labelled anyway.
Rules unchanged: only where no real image exists; painterly/old-print style; on-screen label "Illustration"; `ai_generated=y` in the manifest; disclosure on upload if realistic; no realistic AI image of a real person.

## D8 · Footage sources — DECIDED
Public domain first: Library of Congress, NARA, Wikimedia Commons (PD/CC0/CC-BY with credit), Internet Archive/Prelinger. Every asset logged in `assets/manifest.csv`.

## D9 · Publishing — DECIDED (20 Nov 2026, owner): automatic upload
The system uploads by itself with the YouTube Data API (`pipeline/youtube_upload.py`), under `config/upload_policy.yaml`.
- Every upload passes the gates first: score, preflight, asset licences, metadata limits, right channel token, daily cap, optional owner approval.
- Until Google approves the API compliance audit (`audit_passed: false`), only test uploads go through the API; real episodes are uploaded by hand from the package, because unaudited API uploads are locked private.
- Recommended mode after the audit: `scheduled` with a 24-hour review window before publishAt.
- Open with the owner: keep `require_owner_approval` on for the first ~10 videos, then decide.

## D10 · Code repository — DECIDED (20 Nov 2026, owner): own git repo + private GitHub repo
This folder currently sits inside the home-folder git repo (`C:/Users/Chen`, linked to another GitHub repo). P0.3: `git init` inside `history-doc-system/` so it has its own history, then push to a new **private** GitHub repo. Ask the owner for the repo name and confirm before creating it. `.env`, `secrets/`, renders and large media stay out of git.
