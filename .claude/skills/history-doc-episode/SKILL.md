---
name: "history-doc-episode"
description: "Use when writing a script, shot list, or production brief for an episode of the English or Thai history documentary YouTube channels, so every episode keeps the channel style."
---

# History documentary episode (EN + TH channels)

Produce one episode package in the channel's fixed style: a calm, credible documentary narrated like a storyteller who knows the facts. Real footage first, maps as the backbone, slow movement, no flashy effects.

## Inputs to confirm
- Topic and topic cluster (WWII, entire history of X, ancient civilisation, myth, medieval/royals, everyday life, rise and fall of empires, American history, Southeast Asian kingdoms (TH), local legends (TH))
- Language: English (main channel, US/UK audience) or Thai (second channel)
- Target length (default 30 min)

## Deliverables, in this order
1. **Fact sheet**: key dates, names, numbers, each with 2 sources. Flag anything disputed.
2. **Hook**: one paradox in the first 15 seconds (small or ignored thing -> huge outcome), then the promise line ("This is the entire story of X, from A to B").
3. **Script** in 6 parts, written in the scorer format (`CLAUDE.md` → Script format) and saved as `script.md`:
   1. Hook 0:00-0:30: open in the middle of a moment (date, place, people), state the known ending, then ask HOW/WHY. Opening sentence ≤ 14 words; first question within ~15 s; thumbnail words spoken within 30 s. Never open with "In this video" or a greeting.
   2. Promise: one line, at most 2 teased mysteries, no list of chapters.
   3. Context 1-4 min: the world before the story; end on the obstacle that drives chapter 1.
   4. Main chapters (4-6), 4-6 min each, each opens with a year + place card and a 1-2 sentence recap for listeners who drifted. Link beats with but/so/still, never "and then". Every chapter has a real obstacle that makes the known ending feel uncertain, at least 3 named people with a stated want across the episode, and ends on an open question. A question or tease at least every 90 s. One small human anecdote per chapter.
   5. Turning point at 60-85% of the runtime: music out, 1-2 s pause, then the reveal; put the listener in the scene ("Picture yourself...").
   6. Close: answer the hook question in its own words, sum up the causes in 3 short sentences, a specific next-episode question, a series CTA (no generic "like and subscribe"), then the channel sign-off as the last line.
   - Ear rules: one idea and one number per sentence (a deliberate contrast pair in the hook is allowed), average 8-16 words, ≤ 10% over 20 words, nothing over 28, a long sentence followed by a short one, active voice, round numbers and compare them to familiar things, no "as you can see". Direct address "you" 1-4 times a minute in key scenes.
   - Sound cues in the script: a [MIX] line, a [MUSIC] cue per section (instrumental only), J/L-cut or sound bridge at every section start, [PAUSE 1-2] after big facts (never over 3 s).
   - Length: about 150 words per minute in English. Thai narration is read slower and calmer than a news voice.
   - Gate: `python tools/score.py script.md --rounds 1,2,3,4,5` → every round ≥ 85, mean ≥ 90, no metric at 0. Write waivers into `score.json` with a reason.
4. **Shot list**: one row per sentence: sentence -> visual type -> archive search terms -> movement/effect.
5. **Title, thumbnail brief, description** with chapters and a list of sources and footage credits.

## Visual rules
- Source priority: 1) public-domain footage and photos (Library of Congress, NARA, Internet Archive/Prelinger, Pond5 Public Domain; check the licence of every file) 2) self-made animated maps 3) public-domain paintings, manuscripts, artefacts 4) present-day location shots 5) AI images in a painterly/old-print style only, for scenes with no real image.
- Cluster mix: WWII = real footage >50% + front-line maps, day-counter cards, heavy grain. Entire history = maps 30-40% with territory growing/shrinking and a year counter. Ancient/myth = artefacts and classical paintings with 2.5D parallax; gold frame for legend, white frame for evidence. Empires = one colour spreading across the map. Southeast Asia (TH) = regional maps, trade/army routes, present-day ruins and drone shots, ancient + modern place names on screen.
- Editing: change shot every 2-3 s in the first 30 s, then about one shot per sentence (average 3-4 s; owner chose this pace on 21 Nov 2026), nothing static over 10 s. Slow 5-10% Ken Burns zoom, alternating direction. Cuts and dissolves only, short fade to black between chapters. 4:3 archive centred on a dark blurred 16:9 background. Colorized footage is labelled "colorized". Export 1080p (owner, 21 Nov 2026).
- Vary zoom directions, map colours, shot order, thumbnail layout, and title formula between episodes. Never reuse the same template on consecutive videos.

## Sound
- One consistent deep, calm narrator voice for the channel (human preferred for Thai names).
- Two narration tones, chosen in the script with `[TONE: ...]` cues: `intimate` (default: a storyteller sharing a secret) and `epic` (powerful, for the hook and the big set pieces: the first shot, a battle, the final assault). Keep epic to roughly a fifth to a quarter of the runtime; a whole episode in epic is too heavy. Never put a TONE cue among the first two cues of a section (the J/L-cut check reads those).
- Royalty-free orchestral/ambient music about -20 to -25 dB under the voice; swell at chapter breaks. No copyrighted music in Shorts.
- Subtle ambience under stills (wind, crowd, distant artillery, projector). No whooshes or comedy sounds.

## Thumbnail and title
- One strong image (face from an old photo, battlefield, or map), at most 4 words or a single number (year, days, years), sepia or black-and-white plus one channel accent colour (deep red or gold).
- Title formulas, rotated: compressed time ("The Entire History of X"), countdown ("100 Days of..."), rise and fall, the forgotten secret, real footage ("Restored Footage"; never "4K": we export 1080p), everyday life, dark mysteries. Thai titles always include the proper name and the years.

## Shorts
3-5 per long video, 30-60 s, 9:16, cut from the strongest anecdote, big captions, ending with a line pointing to the long video.

## Thai adaptation (a Thai episode from an English one)
Start with `python tools/adapt_th.py episodes/<en-ep> --date <week> --title "<Thai title>" --thumb "<Thai thumb>"`. It copies the brief and fact sheet, fills `CAST:`/`PLACES:` from `data/th_names.yaml`, and keeps the English sections and cues. Then write the narration:
- Not a translation. Keep the hook, the structure, every cue and visual (the Thai episode reuses the English pictures, maps and music), and every fact exactly. Rewrite each beat the way a Thai storyteller would say it aloud.
- One sentence per line. Put a space where the narrator takes a breath: short breath groups (about 4–12 syllables) are what the Thai scorer rewards. Split an English line with two sentences into two lines.
- Link beats with แต่ / เพราะอย่างนั้น / ดังนั้น / ถึงอย่างนั้น / ตอนนี้ / ทว่า. Never start a sentence with แล้วก็ / จากนั้น / ต่อมา / หลังจากนั้น. Avoid ซึ่ง clauses and ถูก/โดน passives. Speak to the listener as คุณ in the key scenes.
- Thai anchors: give the Buddhist-era year once (ปีนั้นตรงกับ พ.ศ. ...) and a Thai time anchor without naming a Thai king (ราวสมัยอยุธยาตอนต้น); convert miles and feet to metric; say where a place is today (อิสตันบูล เมืองใหญ่ที่สุดของตุรกี). Every such fact goes into `## Thai additions` of the fact sheet with 2 sources.
- Names: spell them as in `data/th_names.yaml`; add new names there first. Write regnal numbers in words (คอนสแตนตินที่สิบเอ็ด), plain register for foreign rulers (เขา), no Thai-monarchy vocabulary.
- Title: the proper name and the year (e.g. "53 วันสุดท้ายของคอนสแตนติโนเปิล: ... (ค.ศ. 1453)"); vary the formula from the Thai episode the same week.
- Sign-off: `จนกว่าจะพบกันใหม่ อย่าลืมมองย้อนกลับไป` (owner, 22 Nov 2026).
- Gate: `python tools/check_episode.py episodes/<th-ep>` uses the Thai scorer automatically.

## Pre-upload checklist
- Every date, name, and number checked against 2 sources
- Footage rights logged per asset
- "Altered or synthetic content" disclosure turned on if any realistic AI imagery is used
- No AI faces or voices of real people
- Score gate passed and `score.json` saved
- `VOICE` lines quote only verified primary sources
- Hook present in the first 30 s; no still held over 10 s
- Thumbnail and title differ from the previous 3 videos
- Chapters, captions, and end screen added
- Thai channel: avoid topics about the Thai monarchy; tell neighbour-country history neutrally, with no inflammatory wording