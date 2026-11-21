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
- Export resolution — DECIDED (21 Nov 2026, owner): **1080p 30 fps**, not 4K. Measured on this PC for a 23-min episode: 1080p ≈ 50 min and ~2.3 GB; 4K ≈ 4 h and ~8 GB. At 4 episodes a week, 4K would keep the PC rendering ~16 h a week. `tools/assemble.py --4k` still exists. Titles must not say "4K".

## D5 · Narration voice — DECIDED (20 Nov 2026, owner)
- **EN: Gemini TTS, voice Charon** (owner's pick, 20 Nov 2026). Listening test: the Constantinople hook (~54 s) in Charon, Orus and Iapetus, loudness-matched; 9 requests. ElevenLabs was not tested: the owner chose from the Gemini samples. It stays an option if retention data later points at the voice (ElevenLabs about $99/month at our volume). Rough Gemini cost: under $1 per 25-min episode. Same voice on every EN episode. Charon is also QURIO's Thai voice; different language and audience, so no clash. Gemini key: copied from the Lupas `.env` with the owner's OK, so both projects share one daily quota.
- **EN delivery: two tones** (owner, 20 Nov 2026). After hearing three directions on the same passage: v1 "calm, steady" was flat and slow; v2 "storyteller" felt "like telling a secret" with some emotion; v3 "epic war documentary" felt like a big scene ("a beach landing") but too heavy for 20 minutes. Both v2 (`intimate`, the default) and v3 (`epic`) are kept in `config/voice.yaml`; the script switches with `[TONE: ...]` cues. Constantinople: epic on 18% of the words.
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

- **Update 21 Nov 2026 (owner): hybrid "B".** After the first draft felt like a slide show and the benchmark (`docs/benchmark-2026-11.md`) showed breakout videos draw a picture for every sentence, AI scenes are used for every story beat that has no *exact* real picture (not only "no real image at all"). Real pictures stay for real people, objects and places (portraits, artefacts, the walls). Same style rules: old-print look, anonymous figures, label "Illustration", `ai_generated=y`. Budget about 150–200 images per episode (~$6–8). Each paid batch still needs the owner's yes with the request count.

## D8 · Footage sources — DECIDED
Public domain first: Library of Congress, NARA, Wikimedia Commons (PD/CC0/CC BY/CC BY-SA with credit), Internet Archive/Prelinger. Every asset logged in `assets/manifest.csv`.
- Image licences (21 Nov 2026, owner): download public domain, CC0, CC BY and **CC BY-SA** (most present-day location photos on Commons are BY-SA). Never NC, ND or unknown. Every CC BY / BY-SA file is credited in the description (author, licence, link), from `assets/manifest.csv`. Internet Archive: PD/CC0 only (uploader-declared licences). Set in `config/assets.yaml`.
- Library of Congress (bot check on loc.gov) and NARA (catalog API needs a key) are searched through their copies on Wikimedia Commons.
- Map data (21 Nov 2026): Natural Earth (public domain) for regional maps; OpenStreetMap coastline (ODbL) for city maps, because Natural Earth has no city-scale coast. ODbL needs the credit "© OpenStreetMap contributors" wherever the map is shown; `tools/map.py` puts it on the frame and in the manifest.

## D9 · Publishing — DECIDED (20 Nov 2026, owner): automatic upload
The system uploads by itself with the YouTube Data API (`pipeline/youtube_upload.py`), under `config/upload_policy.yaml`.
- Every upload passes the gates first: score, preflight, asset licences, metadata limits, right channel token, daily cap, optional owner approval.
- Until Google approves the API compliance audit (`audit_passed: false`), only test uploads go through the API; real episodes are uploaded by hand from the package, because unaudited API uploads are locked private.
- Recommended mode after the audit: `scheduled` with a 24-hour review window before publishAt.
- Open with the owner: keep `require_owner_approval` on for the first ~10 videos, then decide.

## D10 · Code repository — DECIDED (20 Nov 2026, owner): own git repo + private GitHub repo
This folder currently sits inside the home-folder git repo (`C:/Users/Chen`, linked to another GitHub repo). P0.3: `git init` inside `history-doc-system/` so it has its own history, then push to a new **private** GitHub repo. Ask the owner for the repo name and confirm before creating it. `.env`, `secrets/`, renders and large media stay out of git.
