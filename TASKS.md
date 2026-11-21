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
- [x] **P1.3 Script step.** Write `script.md` in the scorer format with the skill; target length = minutes × 150 words.
  AC: the Constantinople script is expanded from the 6.6-minute test cut to the full episode (target ~25 min: 4–6 chapters) and passes the score gate. (Done 20 Nov 2026: 4 chapters + turning point, 3,421 words, about 23 min, rounds 93.0/95.6/98.2/100/100, mean 97.4. 72 new facts added to the fact sheet first. Open: rows 85 and 103 in the fact sheet.)
- [x] **P1.4 Score gate** (starter included). `tools/check_episode.py` runs the scorer and writes `score.json` (with `waivers`), exit code ≠ 0 if the gate fails.
  AC: v0 fixture fails, v5 fixture passes.
- [ ] **P1.5 Thai scorer.** Port the metrics to Thai: word-cut with PyThaiNLP, replace sentence length/Flesch with "breath-group length" (≤ 3–4 s per phrase at the Thai narration rate), Thai banned openers ("สวัสดีครับทุกคน", "วันนี้เราจะ"), Thai connectives for the but/therefore metric ("แต่", "เพราะฉะนั้น", "ผลก็คือ" vs "แล้วก็", "จากนั้น").
  AC: a Thai translation of the v0 and v5 scripts scores like the English pair (v5 ≫ v0).
- [ ] **P1.6 Thai adaptation step.** EN script → Thai script: not a literal translation. Keep the hook, structure and visuals; rewrite for the Thai ear; add Thai place names; apply the Thai channel rules in `CLAUDE.md`.
  AC: the Thai Constantinople script passes the Thai scorer.

## P2 · Voice (target: 1 Dec)

- [x] **P2.1 TTS module** `pipeline/voice.py`: script → one audio file per sentence + `timing.json` (start/end per sentence). Honour `[PAUSE n]`. Provider per `docs/decisions.md` (D5: run the EN listening test first; the owner picks the voice).
  AC: Constantinople narration generated; total length within ±10% of the scorer's estimate.
  Done 21 Nov 2026: `pipeline/voice.py`, `tools/voice.py`, `config/voice.yaml`. One audio file per request group (≤700 chars, one tone each), not per sentence: per-line takes sound disjointed (Lupas lesson); per-sentence start/end is in `audio/narration_timing.json`. Two tones by `[TONE]` cue (intimate default, epic ~18% for big scenes; owner's choice). Constantinople: 45 groups, 22.8 min, ratio to the scorer estimate 1.00 (AC met), ~153 wpm, -20.2 LUFS raw, no gap over 2.5 s. Gemini refuses some war passages (finishReason SAFETY): smaller groups and `--keep-going` handle it. To check by ear: group 39 "And what became of the emperor?" (19:10) runs fast (~236 wpm).
- [ ] **P2.2 Pronunciation lexicon** `data/lexicon.yaml` (Palaiologos, Giustiniani, Mehmed…), applied before TTS.
  AC: the owner listens and approves the names in the first episode.
- [ ] **P2.3 Mix.** Music −20 dB under voice with ducking, SFX bed, music-out cues, final loudness −14 LUFS integrated, true peak −1 dBTP (ffmpeg `loudnorm`, two-pass).
  AC: measured with `ffmpeg -af ebur128`; values written to `audio/mix_report.json`.
  Built 22 Nov: `pipeline/mix.py` (plan `audio/mix_plan.yaml`: music beds ducked by a voice-keyed sidechain compressor, SFX with low-pass/fades, two-pass loudnorm), `pipeline/audio_fetch.py` (Commons audio by exact title, manifest row per file). v2 test 0:00–1:00: -14.0 LUFS, -1.0 dBTP, passed. Music for the full episode still to choose (D6: YouTube Audio Library, owner downloads).

## P3 · Assets (target: 4 Dec)

- [x] **P3.1 Shot list.** Script → `shotlist.csv` (one row per sentence: visual_type, search_terms, motion).
  AC: every narration sentence has a row; no planned still longer than 10 s. (Done 21 Nov 2026: `tools/shotlist.py init|check`; Constantinople 410 rows pass. Mix: location 102, painting 89, map 63, card 47, engraving 44, manuscript 42, artefact 23, AI illustration 10 (old-print style, no real faces). Durations are estimates until the final narration timing exists: re-run `check` then.)
- [x] **P3.2 Fetchers** `pipeline/assets/`: Wikimedia Commons API, Library of Congress API, NARA catalog API, Internet Archive. Download only public-domain/CC0 (or CC-BY with the credit recorded).
  AC: each download writes a row to `assets/manifest.csv` with licence, source URL and credit. Unknown licence = not downloaded.
  Done 21 Nov: `pipeline/assets/` (commons, archive_org, licence, episode, review) + `tools/fetch_assets.py` + `config/assets.yaml`, 31 tests. LOC's site is behind a bot check and NARA's catalog API needs a key, so their scans are searched through their Commons copies (`commons_loc`, `commons_nara`). Wikimedia needs contact info in the User-Agent: `ASSETS_CONTACT` in `.env` (owner's choice). Constantinople: all 290 real-image shots filled after retargeting search terms (221 files: PD 108, CC0 28, CC BY 38, CC BY-SA 47); 10 shots with no real image became maps/cards/3 AI illustrations (ships over the hill: 13 AI shots in all). `prune` drops files no shot uses. CC BY-SA allowed by the owner (D8). Open: owner reviews `assets/review.html` by eye (generic Ottoman miniatures of other campaigns are used as mood shots).
- [x] **P3.3 Map maker.** Animated maps (territory growth, routes, arrows, year counter) in the chosen render engine. Natural Earth data is public domain.
  AC: the Constantinople map (walls, Golden Horn, chain, Galata road) renders as a 10 s clip.
  Done 21 Nov: Remotion project in `video/` (MapScene: land, walls, chain, routes with arrows, areas with territory growth, markers, labels, counter, camera moves, 3 palettes; sides fixed: Ottoman deep red, Byzantine blue-grey). Python: `tools/geodata.py` (land polygons: Natural Earth for regions, OpenStreetMap coastline via Overpass for cities, since NE 10m has no Golden Horn) and `tools/map.py` (clip from `data/maps/<name>.yaml` -> props -> Remotion; renders inside an episode are logged to its manifest). `episodes/2026-12-14-en-constantinople/render/maps/overview_10s.mp4`: 10 s, 1080p in ~30 s, 4K in ~1 min 45 s. OSM data is ODbL: credit "© OpenStreetMap contributors" (on the frame and in the manifest). Historical lines (walls, chain, Galata, ship road) are hand-traced from gate positions, ~100 m. Not yet: the other 66 map shots in the shot list need clips written (P4.1 timeline), regional borders need sourced data per episode.
- [x] **P3.4 AI image fallback** (only where no real image exists): painterly/old-print style, on-screen label "Illustration", `ai_generated=y` in the manifest.
  AC: no realistic AI image of a real person anywhere.
  Built 21 Nov: `pipeline/images.py` + `tools/images.py` (init → `assets/ai_prompts.yaml`, dry run with request count and cost, `--go`, `check`), `config/images.yaml` (Gemini `gemini-2.5-flash-image`, 3 print styles, fixed rules: historical print, anonymous figures, no faces/portraits). Guard refuses a scene that asks for realism, names a single ruler or a person on the episode's `real_people` list. Manifest rows: `ai_generated=y`, `label=Illustration`, prompt hash (an unchanged prompt is never re-requested). Constantinople (owner approved 13 requests, ~$0.52, paid from the same Gemini billing as TTS): all 13 images made in 14 requests (#233 came back text-only once and was retried, ~$0.56; 1344×768, engraving style, people small/anonymous, no faces); `tools/images.py check` passes. Gemini added fake engraver signatures on #172 and #221 despite the rules: painted out (noted in the manifest). Contact sheet: `assets/ai_contact_sheet.jpg`.

## P4 · Assembly and render (target: 10 Dec)

- [ ] **P4.5 Visual v2 (owner, 21 Nov 2026):** the first draft felt like a slide show. Benchmark: `docs/benchmark-2026-11.md`. Picture per sentence (hybrid B: real pictures for real people/objects/places, AI old-print scenes for story beats), every picture full frame on a focus point (`assets/framing.yaml`), short captions on the picture, soft 0.5 s dissolves, AI print margins trimmed, music + SFX.
  Done so far (22 Nov): renderer and timeline support all of it; opening 0:00–1:00 rebuilt (7 AI scenes + 5 retried, Buondelmonti map, mix) → `render/preview_v2_opening.mp4`. Next: owner verdict, then the rest of the episode.

- [x] **P4.1 Timeline builder:** `timing.json` + `shotlist.csv` + assets → an edit decision list (JSON).
  Done 21 Nov: `pipeline/timeline.py` + `tools/timeline.py` → `render/edl.json`. Shots run sentence start → next sentence start (pauses keep the picture), " | " cells split evenly, 2 s tail; fit `cover` (aspect ≥ 1.5) or `contain_blur`; Ken Burns 5–10% by length, pans; cards (chapter / fact); label "Illustration" on AI assets; fade to black at chapter starts, dissolve after a scripted pause, else cut; audio cues timed (J-cut / sound bridge 1 s early); chapters; pacing stats. Constantinople: 420 shots, 22:51, PASS. Open: (1) pace: after the hook shots average 3.3 s (302 under 4 s) against the 4–7 s rule, an owner call best made on a rendered preview (P4.2); (2) 67 map shots are placeholders until their clips exist (P4.4).
- [x] **P4.2 Renderer** (engine per decisions): Ken Burns 5–10% zoom with alternating direction, 4:3 archive centred on a blurred 16:9 background, chapter cards (year + place), the label "Illustration" on every `ai_generated=y` asset (P3.4), dissolves, fade to black between chapters, J/L-cuts from the cues, subtle film grain. Export 1080p (owner, 21 Nov 2026; was 4K).
  AC: Constantinople renders end to end; shot changes every 2–3 s in the first 30 s, then an average of 3–4 s (owner, 21 Nov 2026: keep the one-shot-per-sentence pace seen in the preview; was 4–7 s).
  Built 21 Nov: `pipeline/assemble.py` + `tools/assemble.py` (stage → Remotion `Episode` in `video/src/episode/`). Python makes proxies sized for the frame (≤ 1.1× for the zoom), pre-blurred dark backgrounds for 4:3/portrait, a muted warm grade for present-day photos, a grain tile, and resolves transitions into per-shot opacity ramps (dissolve overlaps, fade to black, tail fade). Remotion draws Ken Burns/pans, cards (chapter: date in gold + place in italic; fact), placeholders, the "Illustration" tab, grain, narration. Card styles: chapter, fact, quote (words + source), end. Full Constantinople at 1080p rendered end to end on 21 Nov: 22:51, 2.3 GB, 49 min (concurrency 10), no black gaps, audio = video length. 4K measured on a 30 s range: ~11× real time (~4 h, ~8 GB at CRF 18). Pace: owner kept the 3.3 s average after seeing the preview (21 Nov). Done 21 Nov: full Constantinople with all 67 maps rendered end to end at 1080p (owner chose 1080p over 4K): 22:51, 2.6 GB, 56 min, no black gaps, audio = video length; 720p draft copy `render/constantinople_draft_720p.mp4`. Handed to P2.3: J/L-cuts and SFX need sound files (P2.3 mix; cue times are in edl.json).
- [ ] **P4.3 Captions:** SRT from `timing.json` (EN and TH).
- [x] **P4.4 Map clips for the episode:** write a clip in `data/maps/<name>.yaml` for every `map` shot (Constantinople: 67, one exists), render into `render/maps/`, put `map-<clip>` in the shot's asset cell.
  AC: `tools/timeline.py` shows no map placeholders.
  Done 21 Nov: `data/maps/constantinople_episode.yaml` (extends `constantinople.yaml`): 67 clips, one per map shot, bound with `tools/map.py <lib> --bind <ep>` (shot cell `map-<clip>`, manifest row with the map-data credit). Maps are drawn **inline** by the episode render (MapScene inside Episode, SVG ids unique per shot), so there are no per-clip mp4s and maps come out at 4K. New geography: `bosphorus` (OSM), `med` (Natural Earth). `tools/map.py <lib> --sheet x.png` renders every clip's last frame in one bundle (~100 s) for checking. Walls cross-section and tunnel shots are plan views (no diagram engine). Regional borders (Roman split 395, Byzantine 1180/1350/1453, Ottoman 1451, Morea) are hand-drawn approximations, flagged `approximate: true` and "borders approximate" in the manifest: spot-check against an atlas before upload. Constantinople timeline: 0 placeholders.

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
