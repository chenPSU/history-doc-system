# Build plan

Goal: by **14 Dec 2026**, the Constantinople EN episode goes from brief to an upload-ready package (video, thumbnail, metadata, Shorts) through this pipeline. After that, produce 2 EN + 2 TH long videos per week.

Work top to bottom. Each task has acceptance criteria (AC). Tick the box when the AC pass.
**Exception: start P5.6 and P5.7 in the first week.** Google's API audit can take weeks, and until it passes the system can't publish by itself.

---

## P0 · Setup and decisions (do first, with the owner)

- [x] **P0.1 Confirm the open decisions** in `docs/decisions.md` with the owner (in Thai): render engine, TTS voice per language, music source, image-generation tool, where the repo lives (GitHub?).
  AC: each open decision is marked `DECIDED` with the date and the choice. (Done 20 Nov 2026: D4-D7, D10.)
- [x] **P0.2 Environment.** Python 3.11+, `requirements.txt` installs, `ffmpeg` available, `.env` from `.env.example`.
  AC: `pytest -q` passes; `ffmpeg -version` works; Node 18+ for Remotion (D4). (Done 20 Nov 2026: Python 3.12.10 in `.venv`, ffmpeg 9.0.2, Node 24.19, 15 tests pass.)
- [x] **P0.3 Git repo.** Init, `.gitignore` covers `.env`, renders and large media.
  AC: first commit pushed (if the owner wants a remote). (Done 20 Nov 2026: private repo github.com/chenPSU/history-doc-system.)

## P1 · Script pipeline (target: 27 Nov)

- [x] **P1.1 `tools/new_episode.py`** (starter included): creates the episode folder from `templates/episode/` and fills `brief.yaml`.
  AC: running it for the 16 Phase-1 episodes in `data/episodes.csv` creates 32 folders (EN + TH) without overwriting existing ones. (Done 20 Nov 2026: 31 created + Constantinople kept unchanged; a second run creates nothing.)
- [x] **P1.2 Fact sheet step.** Use the `history-doc-episode` skill to research and write `factsheet.md` (2 sources per fact, disputed items flagged).
  AC: Constantinople fact sheet covers every number in `episodes/2026-12-14-en-constantinople/script.md`; any fact that can't be sourced gets rewritten or removed in the script. (Done 20 Nov 2026 for the 6.6-min test cut: 40 facts, 10 script lines corrected, score still passes at mean 97.4. Open: page numbers for the `book` rows; new facts added in P1.3 go into the sheet first.)
- [ ] **P1.3 Script step.** Write `script.md` in the scorer format with the skill; target length = minutes × 150 words.
  AC: the Constantinople script is expanded from the 6.6-minute test cut to the full episode (target ~25 min: 4–6 chapters) and passes the score gate.
- [x] **P1.4 Score gate** (starter included). `tools/check_episode.py` runs the scorer and writes `score.json` (with `waivers`), exit code ≠ 0 if the gate fails.
  AC: v0 fixture fails, v5 fixture passes.
- [ ] **P1.5 Thai scorer.** Port the metrics to Thai: word-cut with PyThaiNLP, replace sentence length/Flesch with "breath-group length" (≤ 3–4 s per phrase at the Thai narration rate), Thai banned openers ("สวัสดีครับทุกคน", "วันนี้เราจะ"), Thai connectives for the but/therefore metric ("แต่", "เพราะฉะนั้น", "ผลก็คือ" vs "แล้วก็", "จากนั้น").
  AC: a Thai translation of the v0 and v5 scripts scores like the English pair (v5 ≫ v0).
- [ ] **P1.6 Thai adaptation step.** EN script → Thai script: not a literal translation. Keep the hook, structure and visuals; rewrite for the Thai ear; add Thai place names; apply the Thai channel rules in `CLAUDE.md`.
  AC: the Thai Constantinople script passes the Thai scorer.

## P2 · Voice (target: 1 Dec)

- [ ] **P2.1 TTS module** `pipeline/voice.py`: script → one audio file per sentence + `timing.json` (start/end per sentence). Honour `[PAUSE n]`. Provider per `docs/decisions.md` (D5: run the EN listening test first; the owner picks the voice).
  AC: Constantinople narration generated; total length within ±10% of the scorer's estimate.
- [ ] **P2.2 Pronunciation lexicon** `data/lexicon.yaml` (Palaiologos, Giustiniani, Mehmed…), applied before TTS.
  AC: the owner listens and approves the names in the first episode.
- [ ] **P2.3 Mix.** Music −20 dB under voice with ducking, SFX bed, music-out cues, final loudness −14 LUFS integrated, true peak −1 dBTP (ffmpeg `loudnorm`, two-pass).
  AC: measured with `ffmpeg -af ebur128`; values written to `audio/mix_report.json`.

## P3 · Assets (target: 4 Dec)

- [ ] **P3.1 Shot list.** Script → `shotlist.csv` (one row per sentence: visual_type, search_terms, motion).
  AC: every narration sentence has a row; no planned still longer than 10 s.
- [ ] **P3.2 Fetchers** `pipeline/assets/`: Wikimedia Commons API, Library of Congress API, NARA catalog API, Internet Archive. Download only public-domain/CC0 (or CC-BY with the credit recorded).
  AC: each download writes a row to `assets/manifest.csv` with licence, source URL and credit. Unknown licence = not downloaded.
- [ ] **P3.3 Map maker.** Animated maps (territory growth, routes, arrows, year counter) in the chosen render engine. Natural Earth data is public domain.
  AC: the Constantinople map (walls, Golden Horn, chain, Galata road) renders as a 10 s clip.
- [ ] **P3.4 AI image fallback** (only where no real image exists): painterly/old-print style, on-screen label "Illustration", `ai_generated=y` in the manifest.
  AC: no realistic AI image of a real person anywhere.

## P4 · Assembly and render (target: 10 Dec)

- [ ] **P4.1 Timeline builder:** `timing.json` + `shotlist.csv` + assets → an edit decision list (JSON).
- [ ] **P4.2 Renderer** (engine per decisions): Ken Burns 5–10% zoom with alternating direction, 4:3 archive centred on a blurred 16:9 background, chapter cards (year + place), dissolves, fade to black between chapters, J/L-cuts from the cues, subtle film grain. Export 4K.
  AC: Constantinople renders end to end; shot changes every 2–3 s in the first 30 s, then every 4–7 s.
- [ ] **P4.3 Captions:** SRT from `timing.json` (EN and TH).

## P5 · Packaging (target: 12 Dec)

- [ ] **P5.1 Metadata:** title (rotate the 7 formulas; must differ from the last 3 videos), description with chapters from the timing, sources and footage credits from the manifest, tags. Written to `metadata.yaml`.
- [ ] **P5.2 Thumbnail:** one strong image + ≤ 4 words or one number; sepia/B&W + one accent colour (deep red or gold). 1280×720. Two variants for YouTube Test & Compare.
- [ ] **P5.3 Shorts:** 3–5 cuts, 30–60 s, 9:16, big captions, last line points to the long video.
- [ ] **P5.4 Pre-upload checklist** (style guide) as `tools/preflight.py`, writing `preflight.json` with `passed` and the failed items.
  AC: preflight passes on Constantinople.
- [x] **P5.5 YouTube uploader** (starter included): `pipeline/youtube_upload.py`, `tools/upload.py`, `tools/auth_youtube.py`, `config/upload_policy.yaml`. Gates, dry run, resumable upload with retries, thumbnail, captions, playlist, scheduled publishAt, containsSyntheticMedia, channel check, daily cap, idempotent `upload.json`. Tested with a fake service.
- [ ] **P5.6 Connect the channels** with the owner, following `docs/upload-setup.md` steps 1–6.
  AC: `auth_youtube.py` saved tokens and channel ids for EN and TH; a 10-second test video uploaded private with title, thumbnail, captions, playlist and AI label correct; test video deleted.
  Status 20 Nov 2026: **paused by the owner until they have seen the first finished video** (Constantinople EN). Ready: test episodes `episodes/2026-11-20-{en,th}-upload-test` (10 s video, thumbnail, captions, AI flag; score gate passes; `preflight.json` is a marked test stub until P5.4). Waiting on the owner: `secrets/client_secret.json` (setup step 4), then sign-in per channel, a private "test" playlist id per channel for `playlist_by_cluster` "0", and an approval in chat for `approved.yaml`.
- [ ] **P5.7 API audit** (owner submits the form; Claude Code drafts the answers and the screenshots list).
  AC: form submitted; date noted in `docs/decisions.md`. When approved, the owner sets `audit_passed: true` and picks the mode.
- [ ] **P5.8 Scheduled job:** help the owner install the daily `tools/upload.py --queue --go` job (cron/launchd/Task Scheduler) and a log file; add a Thai summary of each run (uploaded / skipped + reasons).
  AC: a dry run of the queue prints the right episodes and reasons.

## P6 · Learning loop (after the first uploads)

- [ ] **P6.1 Analytics pull:** YouTube Analytics API (owner's OAuth). Per video: Intro (% still watching at 0:30), average % viewed, retention curve, returning viewers, end-screen CTR.
- [ ] **P6.2 Weekly report** (Thai) per cluster against the roadmap gates G1–G3.
- [ ] **P6.3 Calibrate the scorer:** compare script scores with real retention after ~10 videos; keep metrics that predict retention, drop or re-weight the rest.
- [ ] **P6.4 Listening test** (cheap, before scale): 5–10 people listen with the screen off while working; mark the second they drift; 3 recall questions. Compare v0 vs v5 Constantinople audio.

## Backlog

- 2-hour "listen while you work / sleep" compilations per cluster (Phase 3 in the roadmap).
- A third channel (decided at gate G3, 23 May 2027).
- vidIQ credits refill on 7 Dec 2026: re-run outlier research for the Phase 2 series.
