# Visual benchmark: first 2 minutes of top history videos (21 Nov 2026)

Why: the owner watched the Constantinople draft and said it feels like a slide presentation, not something people keep watching. Before building "v2", we measured what breakout videos in the niche actually show.

Method: the built-in browser opened each video. The first 120 s were sampled every 0.2 s: frames at 48×27 to find cuts (mean luminance change > 10), and the first/last frame of each shot at 192×108 to estimate in-shot motion. A contact sheet of frames every 4–5 s gave the look. Not measured: audio (music/SFX density), retention curves (only the channel owner can see them). Three videos is a small sample.

| Video | Views (roadmap) | Format | Shots in 120 s | Typical shot | In-shot motion | What the pictures are |
|---|---|---|---|---|---|---|
| The Entire History of England in 14 Minutes | 235K, 186× channel norm | faceless | 20 | 6 s (3–8 s) | almost none; ~0.6 s animated transition between shots | Cartoon illustrations drawn for **each sentence**: a recurring stick-figure narrator, speech bubbles, maps with the character pointing. Every picture fills the frame. |
| How One Small Country Controlled Half the World | 675K | faceless | ~25 real shots (34 detections incl. dissolves) | 3–8 s, a few 11–18 s holds | some (slow moves, animated globes) | Cinematic, warm-graded AI scenes made **for each sentence** (ships, councils, villages, 3D globes with glowing territory). Every picture fills the frame. |
| The Real History of the Bible | 486K, 566× | presenter on location | — | — | — | Not comparable (a filmed host), dropped. |
| Our Constantinople draft (v1) | — | faceless | ~36 | 3.3 s | 5–10% Ken Burns on everything | Archive images found by search terms: often only loosely related to the sentence; 201/303 images are 4:3 or portrait, shown small on a blurred background. |

## What the breakouts do that we do not

1. **The picture shows the sentence.** Each shot depicts what is being said right then (who, where, doing what), not a generic image of the topic.
2. **Full frame, one consistent look.** No small pictures on blurred backgrounds. A single visual world (one illustration style, one grade) for the whole video.
3. **Maps are illustrated scenes** (globes, territory glowing, a character pointing), not flat diagrams.
4. **Fewer, longer shots than ours** (about 6 s vs 3.3 s), with a soft animated transition instead of many hard cuts.
5. A recurring element (character, motif) the viewer follows.

## Implication for v2

The biggest gap is not effects or pace: it is that our pictures do not tell the story. The options are recorded in the session with the owner (21 Nov 2026); see `docs/decisions.md` once decided.
