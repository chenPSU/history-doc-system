#!/usr/bin/env python3
"""Score a documentary script against measurable rules.

Script format:
  TITLE: ...           (optional header lines)
  THUMB: ...
  ## SECTION NAME      (HOOK, PROMISE, CONTEXT, CHAPTER n, TURNING POINT, CLOSE ...)
  [CUE: ...]           production cues (not narrated)
  VOICE (who): "..."   first-person voice read by a second voice (narrated)
  plain lines          narrator text
Usage: score.py file.md [--rounds 1,2,3] [--json]
"""
import re, sys, json, statistics as st

WPM = 150  # narration speed used across the channel

# ---------- parsing ----------
def parse(path):
    meta, sections, cur = {}, [], None
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        m = re.match(r"^(TITLE|THUMB|SIGNOFF):\s*(.*)", line)
        if m:
            meta[m.group(1).lower()] = m.group(2); continue
        if line.startswith("## "):
            cur = {"name": line[3:].strip().upper(), "narr": [], "voice": [], "cues": [], "order": []}
            sections.append(cur); continue
        if cur is None:
            continue
        if line.lstrip().startswith("["):
            cur["cues"].append(line.strip()); cur["order"].append(("cue", line.strip()))
        elif line.startswith("VOICE"):
            q = re.search(r'"(.*)"', line)
            cur["voice"].append(q.group(1) if q else line)
        else:
            cur["narr"].append(line.strip()); cur["order"].append(("text", line.strip()))
    return meta, sections

def spoken(sec):  # all narrated text in order (narrator + voices)
    return " ".join(sec["narr"] + sec["voice"])

def words(t):
    return re.findall(r"[A-Za-z0-9'’\-]+", t)

def sentences(t):
    parts = re.split(r"(?<=[.!?])\s+", t.strip())
    return [p for p in parts if words(p)]

def syllables(w):
    w = w.lower().strip("'’")
    if not w: return 0
    if w.isdigit(): return 2
    w = re.sub(r"e$", "", w)
    n = len(re.findall(r"[aeiouy]+", w))
    return max(1, n)

def flesch(t):
    ws, ss = words(t), sentences(t)
    if not ws or not ss: return 0
    syl = sum(syllables(w) for w in ws)
    return 206.835 - 1.015 * (len(ws) / len(ss)) - 84.6 * (syl / len(ws))

def pause_seconds(sec):
    total = 0.0
    for c in sec["cues"]:
        m = re.search(r"PAUSE\s*([\d.]+)", c)
        if m: total += float(m.group(1))
    return total

def secs(nwords):
    return nwords / WPM * 60

# ---------- scoring helpers ----------
def band(v, lo, hi, soft):
    """1.0 inside [lo,hi]; falls linearly to 0 over `soft` outside."""
    if lo <= v <= hi: return 1.0
    d = lo - v if v < lo else v - hi
    return max(0.0, 1 - d / soft)

def atleast(v, target):
    return min(1.0, v / target) if target else 1.0

def atmost(v, target, soft):
    return 1.0 if v <= target else max(0.0, 1 - (v - target) / soft)

# ---------- metrics by round ----------
METRICS = {}
def metric(rnd, name):
    def deco(f):
        METRICS.setdefault(rnd, []).append((name, f)); return f
    return deco

def first_secs_text(sections, seconds):
    out, budget = [], int(seconds / 60 * WPM)
    for s in sections:
        for w in words(spoken(s)):
            if len(out) >= budget: return " ".join(out)
            out.append(w)
    return " ".join(out)

# Round 1: hook and first 30 seconds
@metric(1, "seconds to first open question")
def r1_gap(meta, S):
    txt = " ".join(spoken(s) for s in S)
    i = txt.find("?")
    if i < 0: return 999, 0.0
    v = secs(len(words(txt[:i])))
    return round(v, 1), atmost(v, 12, 20)

@metric(1, "hook + promise length (s)")
def r1_len(meta, S):
    n = sum(len(words(spoken(s))) for s in S if s["name"] in ("HOOK", "PROMISE"))
    v = secs(n)
    return round(v, 1), band(v, 20, 40, 30)

@metric(1, "opening sentence: words (≤14) & concrete")
def r1_open(meta, S):
    first = sentences(spoken(S[0]))[0]
    n = len(words(first))
    concrete = bool(re.search(r"\b(1[0-9]{3}|dawn|night|morning|midnight|[A-Z][a-z]+ [A-Z][a-z]+)\b", first))
    sc = atmost(n, 14, 14) * (1.0 if concrete else 0.5)
    return f"{n} words, concrete={concrete}", sc

@metric(1, "items listed in promise (spoiler TOC ≤2)")
def r1_toc(meta, S):
    p = next((spoken(s) for s in S if s["name"] == "PROMISE"), "")
    items = max([len(re.split(r",\s*(?:and\s+)?|\s+and\s+", x)) for x in sentences(p)] or [0])
    return items, atmost(items, 2, 4)

@metric(1, "banned openers (in this video / welcome / today)")
def r1_banned(meta, S):
    t = first_secs_text(S, 45).lower()
    hits = sum(t.count(b) for b in ["in this video", "welcome", "today we", "hey guys", "before we begin"])
    return hits, 1.0 if hits == 0 else 0.0

@metric(1, "title/thumbnail words confirmed in first 30s")
def r1_match(meta, S):
    if "title" not in meta: return "no title", 0.0
    stop = set("the a an of in to and how why what was is it for on with by".split())
    keys = [w.lower() for w in words(meta["title"] + " " + meta.get("thumb", "")) if w.lower() not in stop]
    t = first_secs_text(S, 30).lower()
    hit = [k for k in set(keys) if k in t]
    return f"{len(hit)}/{len(set(keys))}", len(hit) / max(1, len(set(keys)))

@metric(1, "hook question asks HOW/WHY (ending is known)")
def r1_how(meta, S):
    qs = [q for q in re.findall(r"[^.?!]*\?", spoken(S[0]))]
    ok = any(re.search(r"\b(how|why)\b", q, re.I) for q in qs)
    return ok, 1.0 if ok else 0.0


# Round 2: writing for the ear
def all_sents(S):
    return [x for s in S for x in sentences(" ".join(s["narr"]))]

@metric(2, "mean sentence length (8-16 words)")
def r2_mean(meta, S):
    L = [len(words(x)) for x in all_sents(S)]
    v = st.mean(L)
    return round(v, 1), band(v, 8, 16, 8)

@metric(2, "% sentences over 20 words (<=10%)")
def r2_long(meta, S):
    L = [len(words(x)) for x in all_sents(S)]
    v = 100 * sum(l > 20 for l in L) / len(L)
    return round(v, 1), atmost(v, 10, 30)

@metric(2, "longest sentence (<=28 words)")
def r2_max(meta, S):
    v = max(len(words(x)) for x in all_sents(S))
    return v, atmost(v, 28, 20)

@metric(2, "Flesch reading ease (>=65)")
def r2_flesch(meta, S):
    v = flesch(" ".join(" ".join(s["narr"]) for s in S))
    return round(v, 1), min(1.0, max(0.0, (v - 35) / 30))

@metric(2, "passive constructions per 10 sentences (<=1)")
def r2_passive(meta, S):
    ss = all_sents(S)
    n = sum(len(re.findall(r"\b(was|were|been|being|is|are)\s+(\w+ly\s+)?\w+(ed|en|built|known|seen|told|held)\b", x)) for x in ss)
    v = 10 * n / len(ss)
    return round(v, 2), atmost(v, 1, 2)

NUMW = r"(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)"
MONTHS = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
def count_numbers(x):
    x = re.sub(r"\b\d{1,2}\s+" + MONTHS + r"(\s+\d{3,4})?\b", " DATE ", x)       # a date is one fact
    x = re.sub(r"\b" + NUMW + r"(?:[\s-]+(?:and\s+)?" + NUMW + r")*\b", " NUM ", x, flags=re.I)  # 'seven thousand' = one
    return len(re.findall(r"\bDATE\b|\bNUM\b|\b\d[\d,.]*\b", x))

@metric(2, "sentences with 2+ numbers (0)")
def r2_nums(meta, S):
    v = sum(count_numbers(x) >= 2 for x in all_sents(S))
    return v, atmost(v, 0, 5)

@metric(2, "stacked clauses: which/who/whom per 100 words (<=0.5)")
def r2_which(meta, S):
    t = " ".join(" ".join(s["narr"]) for s in S)
    v = 100 * len(re.findall(r"\b(which|whom|whose)\b|, who\b", t)) / len(words(t))
    return round(v, 2), atmost(v, 0.5, 1)

@metric(2, "long sentence followed by a short one (>=70%)")
def r2_follow(meta, S):
    L = [len(words(x)) for x in all_sents(S)]
    longs = [i for i, l in enumerate(L[:-1]) if l >= 18]
    if not longs: return "no long sentences", 1.0
    v = 100 * sum(L[i + 1] <= 10 for i in longs) / len(longs)
    return round(v), atleast(v, 70)


@metric(2, "rhythm: sentence-length variation CV (0.35-0.7)")
def r2_cv(meta, S):
    L = [len(words(x)) for x in all_sents(S)]
    v = st.pstdev(L) / st.mean(L)
    return round(v, 2), band(v, 0.35, 0.7, 0.25)


# Round 3: narrative drive
STORY = ["CONTEXT", "CHAPTER", "TURNING POINT"]
def story_secs(S):
    return [s for s in S if any(s["name"].startswith(k) for k in STORY)]

CAUSAL = r"^(But|So|Therefore|Yet|Still|Instead|Which meant|That meant|Because of (this|that)|Worse|Now)\b"
@metric(3, "'and then' links between beats (0)")
def r3_andthen(meta, S):
    t = " ".join(spoken(s) for s in S)
    v = len(re.findall(r"\band then\b", t, re.I)) + len(re.findall(r"(?:^|[.!?]\s+)Then\b", t))
    return v, atmost(v, 0, 5)

@metric(3, "but/therefore links per minute of story (>=2)")
def r3_causal(meta, S):
    ss = [x for s in story_secs(S) for x in sentences(" ".join(s["narr"]))]
    n = sum(bool(re.match(CAUSAL, x)) for x in ss)
    mins = secs(sum(len(words(x)) for x in ss)) / 60
    v = n / mins
    return round(v, 2), atleast(v, 2)

OBST = r"\b(could not|couldn't|cannot|can't|failed|impossible|no way|problem|refused|blocked|too (?:strong|small|few|late)|urged him to|give up|furious|unless|the only)\b"
@metric(3, "story sections with an explicit obstacle (all)")
def r3_obst(meta, S):
    ss = story_secs(S)
    hit = [s["name"] for s in ss if re.search(OBST, spoken(s), re.I)]
    return f"{len(hit)}/{len(ss)}", len(hit) / len(ss)

TEASE = r"(\?|\bbut\b|\bnot yet\b|\bsoon\b|\bwould\b|\bstill\b|\bonly the\b|\bnext\b|\bproblem\b)"
@metric(3, "sections before the climax ending on an open loop")
def r3_end(meta, S):
    ss = [s for s in S if s["name"] not in ("CLOSE", "TURNING POINT")]
    ok = [s["name"] for s in ss if re.search(TEASE, " ".join(sentences(" ".join(s["narr"]))[-2:]), re.I)]
    return f"{len(ok)}/{len(ss)}", len(ok) / len(ss)

@metric(3, "longest stretch without a question or tease (<=90s)")
def r3_gap(meta, S):
    ss = [x for s in S for x in sentences(spoken(s))]
    gap = worst = 0.0
    for x in ss:
        gap += secs(len(words(x)))
        if re.search(r"\?|\b(not yet|would soon|still to come|the real question|what (?:came|comes) next|was only the beginning|had a problem)\b", x, re.I):
            worst, gap = max(worst, gap), 0.0
    worst = max(worst, gap)
    return round(worst), atmost(worst, 90, 90)

@metric(3, "named people with a stated want (>=3)")
def r3_want(meta, S):
    ss = [x for s in S for x in sentences(spoken(s))]
    names = set()
    for x in ss:  # proper names = capitalised words not in sentence-initial position
        for w in re.findall(r"(?<!^)(?<![.!?]\s)\b([A-Z][a-z]{2,})\b", x):
            names.add(w)
    names -= set("The Byzantine Byzantines Ottoman Ottomans Roman Empire West Christian Genoese Golden Horn Sea Marmara Walls Theodosian Bosphorus Anatolia Balkans Renaissance Middle Ages Great Eleventh April May AD Hungarian European Greek Italy Istanbul Constantinople Galata".split())
    wanters = set()
    for x in ss:
        if re.search(r"\b(wanted|needed|had to|planned|hoped|begged|urged|refused|swore|chose)\b", x):
            for n in names:
                if re.search(r"\b" + n + r"\b", x): wanters.add(n)
    return ", ".join(sorted(wanters)) or "none", atleast(len(wanters), 3)


# Round 4: sound for background listening
def cues(S, pat):
    return [c for s in S for c in s["cues"] if re.search(pat, c, re.I)]

@metric(4, "story sections with their own music cue (all)")
def r4_music(meta, S):
    ss = [s for s in S if s["name"] != "PROMISE"]
    ok = [s for s in ss if any(re.search(r"MUSIC", c) for c in s["cues"])]
    return f"{len(ok)}/{len(ss)}", len(ok) / len(ss)

@metric(4, "music cues instrumental, no lyrics (all)")
def r4_lyrics(meta, S):
    m = cues(S, r"^\[MUSIC")
    if not m: return "no music cues", 0.0
    ok = [c for c in m if re.search(r"instrumental|no vocals|\bout\b|silence", c, re.I) and not re.search(r"lyric|vocal(?!s)|song", c, re.I)]
    return f"{len(ok)}/{len(m)}", len(ok) / len(m)

@metric(4, "section transitions with J/L-cut or sound bridge")
def r4_jcut(meta, S):
    trans = S[1:]
    ok = [s for s in trans if any(re.search(r"J-CUT|L-CUT|SOUND BRIDGE", c) for c in s["cues"][:2])]
    return f"{len(ok)}/{len(trans)}", len(ok) / len(trans)

@metric(4, "planned pauses: >=1 per story section, each <=3s")
def r4_pause(meta, S):
    ss = story_secs(S)
    have = sum(any("PAUSE" in c for c in s["cues"]) for s in ss)
    lens = [float(x) for c in cues(S, "PAUSE") for x in re.findall(r"PAUSE\s*([\d.]+)", c)]
    too_long = sum(l > 3 for l in lens)
    sc = (have / len(ss)) * (1.0 if too_long == 0 else 0.5)
    return f"{have}/{len(ss)} sections, {len(lens)} pauses, {too_long} over 3s", sc

@metric(4, "mix spec: music 18-24 dB under voice, -14 LUFS")
def r4_mix(meta, S):
    m = " ".join(cues(S, r"^\[MIX"))
    duck = re.search(r"music\s*-?(\d+)\s*dB", m, re.I)
    ok1 = bool(duck and 18 <= int(duck.group(1)) <= 24)
    ok2 = "-14 LUFS" in m
    return f"duck={duck.group(1) if duck else None}, lufs={ok2}", (ok1 + ok2) / 2

@metric(4, "screen-off test: visual-only phrases (0)")
def r4_deictic(meta, S):
    t = " ".join(spoken(s) for s in S)
    v = len(re.findall(r"\b(as you can see|look at|you can see|on screen|this map|shown here|right here|pictured)\b", t, re.I))
    return v, 1.0 if v == 0 else max(0.0, 1 - v / 3)

@metric(4, "music drops out before the peak reveal")
def r4_drop(meta, S):
    tp = next((s for s in S if s["name"] == "TURNING POINT"), None)
    ok = bool(tp and any(re.search(r"MUSIC:.*\bout\b|SILENCE", c, re.I) for c in tp["cues"]))
    return ok, 1.0 if ok else 0.0


# Round 5: rewatch, loyalty and series
def content_words(t):
    stop = set("the a an of in to and how why what was is it for on with by that this these those they their them his her he she its were be been had has have not no but so from at as or into over one".split())
    return {w.lower() for w in words(t) if len(w) > 3 and w.lower() not in stop}

@metric(5, "ending calls back to the hook (>=4 shared words + answer)")
def r5_callback(meta, S):
    hook = next(s for s in S if s["name"] == "HOOK"); close = next(s for s in S if s["name"] == "CLOSE")
    shared = content_words(spoken(hook)) & content_words(spoken(close))
    answered = bool(re.search(r"\b(that is how|that's how|so how did|the answer)\b", spoken(close), re.I))
    return f"{len(shared)} shared, answered={answered}", (min(1.0, len(shared) / 4) + answered) / 2

@metric(5, "peak (music-out reveal) at 60-85% of runtime")
def r5_peak(meta, S):
    total, pos, seen = 0, None, 0
    for s in S:
        for raw in s.get("order", []):
            if raw[0] == "cue" and s["name"] == "TURNING POINT" and re.search(r"MUSIC:.*\bout\b", raw[1]) and pos is None:
                pos = seen
            if raw[0] == "text": seen += len(words(raw[1]))
    total = seen
    if pos is None: return "no marked peak", 0.0
    v = 100 * pos / total
    return f"{v:.0f}%", band(v, 60, 85, 20)

@metric(5, "no generic CTA; last line is story or sign-off")
def r5_cta(meta, S):
    close = next(s for s in S if s["name"] == "CLOSE")
    t = spoken(close).lower()
    generic = len(re.findall(r"like and subscribe|smash|hit the bell|if you enjoyed this video", t))
    last = sentences(" ".join(close["narr"]))[-1]
    sign = meta.get("signoff", "")
    ok_last = bool(sign and sign.lower() in last.lower())
    return f"generic={generic}, signoff_last={ok_last}", ((generic == 0) + ok_last) / 2

@metric(5, "direct address 'you' per minute (1-4)")
def r5_you(meta, S):
    t = " ".join(spoken(s) for s in S)
    n = len(re.findall(r"\byou\b|\byour\b", t, re.I))
    v = n / (secs(len(words(t))) / 60)
    return round(v, 2), band(v, 1, 4, 1)

@metric(5, "specific next-episode tease in CLOSE")
def r5_next(meta, S):
    close = next(s for s in S if s["name"] == "CLOSE")
    ok = bool(re.search(r"\b(next (time|episode|video)|in the next)\b", spoken(close), re.I)) and bool(re.search(r"\b(?i:how|why|what)\b[^.?!]*\b[A-Z][a-z]+", spoken(close)))
    return ok, 1.0 if ok else 0.0

@metric(5, "setups paid off: names from first 40% reused in last 30% (>=4)")
def r5_payoff(meta, S):
    ws = words(" ".join(spoken(s) for s in S))
    a, b = ws[: int(len(ws) * 0.4)], ws[int(len(ws) * 0.7):]
    names = {w for w in a if w[0].isupper()} - {"The", "But", "So", "In", "On", "It", "He", "His", "They", "Then", "Now", "And", "No", "By", "How", "When", "Its", "Few", "Let's", "Still", "Even", "Inside", "Outside", "First", "Behind", "Together", "Water", "Historians", "Orban", "Mehmed"}
    reused = sorted({w for w in b if w in names})
    return ", ".join(reused), atleast(len(reused), 4)

@metric(5, "channel template sections all present")
def r5_template(meta, S):
    need = ["HOOK", "PROMISE", "CONTEXT", "CHAPTER", "TURNING POINT", "CLOSE"]
    have = [n for n in need if any(s["name"].startswith(n) for s in S)]
    return f"{len(have)}/{len(need)}", len(have) / len(need)

# ---------- runner ----------
def run(path, rounds):
    meta, S = parse(path)
    all_txt = " ".join(spoken(s) for s in S)
    nw = len(words(all_txt))
    base = {"words": nw, "est_minutes": round((secs(nw) + sum(pause_seconds(s) for s in S)) / 60, 1)}
    res = {"file": path, "base": base, "rounds": {}}
    for r in rounds:
        rows = []
        for name, f in METRICS.get(r, []):
            v, sc = f(meta, S)
            rows.append({"metric": name, "value": v, "score": round(sc, 2)})
        res["rounds"][r] = {"rows": rows, "score": round(100 * st.mean(x["score"] for x in rows), 1) if rows else None}
    return res

if __name__ == "__main__":
    args = sys.argv[1:]
    rounds = [1]
    if "--rounds" in args:
        rounds = [int(x) for x in args[args.index("--rounds") + 1].split(",")]
    files = [a for a in args if a.endswith(".md")]
    out = [run(f, rounds) for f in files]
    if "--json" in args:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        for r in out:
            print(f"== {r['file']}  {r['base']}")
            for rn, d in r["rounds"].items():
                print(f"  Round {rn}: {d['score']}")
                for x in d["rows"]:
                    print(f"    {x['score']:.2f}  {x['metric']}: {x['value']}")
