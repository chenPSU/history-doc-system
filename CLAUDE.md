# History Documentary Content System

This repo builds and runs a production system for two faceless YouTube history-documentary channels:

- **EN (main):** English, US/UK audience. Higher RPM; the priority channel.
- **TH (second):** Thai. Reuses EN research and visuals, plus Thai-only episodes (marked ★ in the roadmap).

The owner speaks Thai. Talk to them in Thai. Code, comments and file names are in English.

## Read these before you work

| File | What it holds |
|---|---|
| `TASKS.md` | The build plan: phases, tasks, acceptance criteria. **Start here.** |
| `docs/decisions.md` | Stack choices. Some are still **open**: confirm them with the owner before building on them. |
| `docs/style-guide.md` | Channel identity, script structure, footage, editing, sound, thumbnails, checklist |
| `docs/roadmap.md` | 26-week content plan, 12 topic clusters, the Phase 1 episode list, decision gates |
| `docs/narration-experiment.md` | 5-round experiment that produced the script rules and `tools/score.py` |
| `docs/market-research.md` | Why history documentaries were chosen, and EN vs TH economics |
| `docs/upload-setup.md` | YouTube upload setup (Thai): Google Cloud, OAuth, audit, modes, cron |
| `.claude/skills/history-doc-episode/SKILL.md` | How to write one episode package. Use it for every script. |

## Key dates (today's date is around 2026-11-19)

- **23 Nov – 6 Dec 2026:** build the system (this repo).
- **7 Dec 2026:** Phase 1 starts. 2 long videos per week per language (16 + 16 by 31 Jan).
- **14 Dec 2026:** first milestone. The Constantinople EN episode goes end-to-end through the pipeline.
- **31 Jan 2027:** YPP deadline. Applications that reach YouTube by 23:59 UTC are judged at 1,000 subs + 4,000 long-form watch hours. From 1 Feb 2027 the bar is 8,000 hours.

## Episode folder contract

One folder per episode: `episodes/<YYYY-MM-DD>-<en|th>-<slug>/`

```
brief.yaml        topic, cluster, language, length, hook paradox, key visual, title options
factsheet.md      every date, name and number, each with 2 sources; disputed items flagged
script.md         narration in the scorer format (below)
score.json        output of tools/score.py
shotlist.csv      one row per sentence: sentence, visual_type, search_terms, motion, asset_id
assets/manifest.csv   every asset: id, file, source_url, licence, credit, ai_generated (y/n)
audio/            narration takes, music, sfx, final mix
render/           renders
metadata.yaml     title, description, chapters, tags, credits, AI disclosure flag, file paths
score.json        written by tools/check_episode.py (gate_passed)
preflight.json    written by tools/preflight.py (passed)
approved.yaml     owner sign-off (only when require_owner_approval is true)
upload.json       written by the uploader: video id, URL, publish time, step results
shorts/           3–5 vertical cuts
```

Start from `templates/episode/`. `python tools/new_episode.py` creates the folder.

## Script format (what `tools/score.py` parses)

```
TITLE: ...
THUMB: ...
SIGNOFF: Until next time, keep looking back.
## HOOK            sections: HOOK, PROMISE, CONTEXT, CHAPTER n, TURNING POINT, CLOSE
[CUE: ...]         production cues, not narrated: MUSIC, SFX, VISUAL, PAUSE n, J-CUT, L-CUT, SOUND BRIDGE, MIX,
                   TONE: epic | intimate (narration tone until the next TONE cue or section; see config/voice.yaml)
VOICE (who): "..." a real first-person quote read by a second voice (verified source only)
plain lines        narration
```

## Quality gates (do not skip)

1. **Score gate:** `python tools/score.py <script.md> --rounds 1,2,3,4,5`. Every round ≥ 85, mean ≥ 90, and no single metric at 0. If a rule is broken on purpose (e.g. the hook's number pair), write why in `score.json` → `waivers`.
2. **Fact gate:** every date, name and number in the script appears in `factsheet.md` with 2 sources. Never invent quotes. `VOICE` lines must cite the primary source and translation.
3. **Rights gate:** every asset in `assets/manifest.csv` has a licence and source URL. Priority: public domain (LOC, NARA, Wikimedia Commons PD, Internet Archive) → own animated maps → PD paintings/artefacts → AI painterly images (labelled on screen).
4. **Policy gate:** YouTube "inauthentic content" policy (enforced at channel level since Jan 2026). Vary titles, thumbnails, zoom directions, map colours and structure between consecutive videos. Turn on the "altered or synthetic content" disclosure when realistic AI imagery is used. No AI faces or voices of real people.
5. **Upload gate:** uploads happen only through `tools/upload.py`, under `config/upload_policy.yaml`, which the **owner** controls. Never edit that policy, `secrets/`, or create `approved.yaml`, unless the owner asks for that exact change in chat. Never run `tools/upload.py --go` yourself unless the owner asks in chat for that episode; the scheduled job (cron) runs it, not you. Never spend money on paid APIs without the owner's yes.

## Thai channel rules

- No topics touching the Thai monarchy (Section 112 risk).
- Tell neighbour-country history (Cambodia, Myanmar, Laos, Vietnam) neutrally. No inflammatory wording. Skip Khmer topics in Thai until someone checks the tone.
- `score.py` sentence-length and Flesch metrics are English-only. Use the Thai scorer (TASKS P1.5) for Thai scripts.

## Lessons from the QURIO channel (a Thai channel that grew slowly)

One lane only. Make Shorts by cutting them from long videos, not as standalone news clips. Long videos of 15–30+ minutes, grouped into playlists/series. A scattered topic mix gave views but no returning audience.

## Commands

```
python -m venv .venv                     # once; then activate: .venv\Scripts\activate (Windows)
pip install -r requirements.txt
python tools/score.py episodes/<ep>/script.md --rounds 1,2,3,4,5
python tools/score.py a.md b.md --rounds 1,2,3,4,5 --json      # compare versions
python tools/new_episode.py --date 2026-12-07 --lang en --slug korea --title "..."
python tools/check_episode.py episodes/<ep>          # score gate -> score.json
python tools/fetch_assets.py episodes/<ep> --go     # licence-checked images -> assets/, manifest, shot asset_id
python tools/fetch_assets.py review episodes/<ep>   # contact sheet assets/review.html
python tools/map.py data/maps/constantinople.yaml overview_10s --out episodes/<ep>/render/maps/x.mp4   # animated map (Remotion, video/)
python tools/upload.py episodes/<ep>                 # dry run: shows the YouTube request
python tools/upload.py --queue --go                  # what the owner's cron job runs
pytest -q
```

## Working agreement

- Ask before choosing a paid service, creating accounts or using API keys. Keys live in `.env` (see `.env.example`). Never commit `.env`.
- Keep modules small and testable. Every pipeline stage reads and writes files in the episode folder, so any stage can be re-run alone.
- When a metric in `score.py` turns out wrong, fix the scorer, re-score old scripts, and note it in `docs/narration-experiment.md`.
- Update `TASKS.md` checkboxes as you finish tasks.
