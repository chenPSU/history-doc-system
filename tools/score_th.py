#!/usr/bin/env python3
"""Thai scorer (TASKS P1.5): the same 5 rounds as tools/score.py, measured for Thai narration.

Thai has no spaces between words and no capital letters, so the English counts are replaced:
- time comes from syllables (PyThaiNLP, digits read out as Thai words) at TH_SPS syllables per second,
  not from words at 150 wpm;
- a sentence is one script line (Thai scripts put one sentence per line; ? ! . also end one);
- a breath group is a space-separated phrase inside a sentence (Thai writing puts a space where the reader
  pauses), and replaces Flesch: short breath groups are what makes Thai easy on the ear;
- names come from the script's CAST: (people) and PLACES: header lines, not from capital letters.

Cues ([MUSIC], [PAUSE], ...) stay in English, so round 4 reuses the English cue metrics.
Usage: python tools/score.py <thai script.md> --rounds 1,2,3,4,5   (score.py detects Thai and calls this module)
"""
from __future__ import annotations

import re
import statistics as st
from functools import lru_cache

import score as EN
from score import band, atleast, atmost, parse, spoken, pause_seconds

# Calm documentary Thai, slower than news (config/voice.yaml th style). 4.0 syllables/s makes the Thai v5 fixture
# run about as long as the English one (6.3 vs 6.6 min). Estimate only: calibrate against the first Thai
# narration's audio/narration_timing.json and note the change in docs/narration-experiment.md.
TH_SPS = 4.0

THAI = re.compile(r"[฀-๿]")
ABBR = {"ค.ศ.": "คริสต์ศักราช", "พ.ศ.": "พุทธศักราช", "กม.": "กิโลเมตร", "ฯลฯ": "และอื่นๆ", "ร.": "รัชกาลที่"}
MONTHS = "มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม"
NUMW = "สอง|สาม|สี่|ห้า|หก|เจ็ด|แปด|เก้า|สิบ|ยี่สิบ|ร้อย|พัน|หมื่น|แสน|ล้าน|เอ็ด"
QWORDS = r"(ไหม|มั้ย|หรือเปล่า|หรือไม่|อย่างไร|ยังไง|ทำไม|อะไร|ใคร|ที่ไหน|เมื่อไร|เมื่อไหร่|แค่ไหน|เท่าไร|เท่าไหร่)"


def is_thai(text: str) -> bool:
    letters = re.findall(r"[A-Za-z฀-๿]", text)
    return bool(letters) and sum(bool(THAI.match(c)) for c in letters) / len(letters) > 0.3


# ---------- reading time ----------
def _say_numbers(t: str) -> str:
    from pythainlp.util import num_to_thaiword
    for a, b in ABBR.items():
        t = t.replace(a, b)

    def num(m):
        s = m.group(0).replace(",", "")
        if "." in s:
            a, b = s.split(".", 1)
            return num_to_thaiword(int(a)) + "จุด" + "".join(num_to_thaiword(int(d)) for d in b if d.isdigit())
        return num_to_thaiword(int(s))
    return re.sub(r"\d[\d,]*(?:\.\d+)?", num, t)


@lru_cache(maxsize=None)
def syllables(t: str) -> int:
    from pythainlp.tokenize import syllable_tokenize
    t = _say_numbers(t)
    n = sum(EN.syllables(w) for w in re.findall(r"[A-Za-z]+", t))
    for chunk in re.findall(r"[฀-๿]+", t):
        for s in syllable_tokenize(chunk, engine="dict"):
            # a lone consonant ('ต' of เมห์เมต) is a final or cluster sound, not its own syllable
            if len(s) > 1 or re.search(r"[ะ-๎]", s):
                n += 1
    return n


def secs(t: str) -> float:
    return syllables(t) / TH_SPS


@lru_cache(maxsize=None)
def words(t: str) -> tuple[str, ...]:
    from pythainlp.tokenize import word_tokenize
    return tuple(w for w in word_tokenize(t, engine="newmm", keep_whitespace=False) if w.strip())


@lru_cache(maxsize=1)
def _stop() -> frozenset:
    from pythainlp.corpus import thai_stopwords
    return frozenset(thai_stopwords())


def content_words(t: str) -> set[str]:
    return {w for w in words(t) if (len(w) > 1 and THAI.search(w) and w not in _stop()) or w.isdigit()}


# ---------- units ----------
def sentences(t: str) -> list[str]:
    out = []
    for line in t.splitlines():
        out += [p.strip() for p in re.split(r"(?<=[?!.])\s+(?!\d)", line.strip()) if p.strip() and not re.fullmatch(r"[\d.]+", p.strip())]
    return [s for s in out if THAI.search(s) or re.search(r"[A-Za-z]", s)]


def _glue(tok: str) -> bool:
    return bool(re.fullmatch(r"[\d,.]+", tok)) or tok in ABBR


def phrases(sentence: str) -> list[str]:
    """Space-separated breath groups. Spaces around numbers and abbreviations are not pauses."""
    out: list[str] = []
    for tok in sentence.split():
        if out and (_glue(tok) or _glue(out[-1].split()[-1]) or re.search(r"\d$", out[-1])):
            out[-1] += " " + tok
        else:
            out.append(tok)
    return out


def narr_text(sec) -> str:
    return "\n".join(sec["narr"])


def spoken_lines(sec) -> str:
    return "\n".join(sec["narr"] + sec["voice"])


def all_sents(S):
    return [x for s in S for x in sentences(narr_text(s))]


def names(meta: dict, key: str) -> list[str]:
    return [n.strip() for n in re.split(r"[,،]", meta.get(key, "")) if n.strip()]


def has_name(name: str, text: str, all_names: list[str]) -> bool:
    """`name` in `text`, not counting it inside a longer listed name (คอนสแตนติน in คอนสแตนติโนเปิล)."""
    for longer in all_names:
        if name != longer and name in longer:
            text = text.replace(longer, " ")
    return name in text


def is_question(x: str) -> bool:
    return "?" in x or bool(re.search(QWORDS + r"\s*$", x.strip()))


def first_secs_text(S, seconds):
    out, t = [], 0.0
    for s in S:
        for x in sentences(spoken_lines(s)):
            if t >= seconds:
                return "\n".join(out)
            out.append(x)
            t += secs(x)
    return "\n".join(out)


METRICS: dict = {}


def metric(rnd, name):
    def deco(f):
        METRICS.setdefault(rnd, []).append((name, f))
        return f
    return deco


# ---------- Round 1: hook and first 30 seconds ----------
@metric(1, "seconds to first open question")
def r1_gap(meta, S):
    t = 0.0
    for x in [x for s in S for x in sentences(spoken_lines(s))]:
        if is_question(x):
            return round(t, 1), atmost(t, 12, 20)
        t += secs(x)
    return 999, 0.0


@metric(1, "hook + promise length (s)")
def r1_len(meta, S):
    v = sum(secs(spoken_lines(s)) for s in S if s["name"] in ("HOOK", "PROMISE"))
    return round(v, 1), band(v, 20, 40, 30)


@metric(1, "opening sentence: seconds (≤5.5) & concrete")
def r1_open(meta, S):
    first = sentences(spoken_lines(S[0]))[0]
    v = secs(first)
    concrete = bool(re.search(r"\d|เที่ยงคืน|ตี\S|รุ่งสาง|ฟ้าสาง|เช้ามืด|กลางคืน|ค่ำ|พลบ|" + MONTHS, first)
                    or any(n in first for n in names(meta, "cast") + names(meta, "places")))
    return f"{v:.1f}s, concrete={concrete}", atmost(v, 5.5, 5.5) * (1.0 if concrete else 0.5)


@metric(1, "promise: phrases in its longest sentence (spoiler list ≤4)")
def r1_toc(meta, S):
    p = next((narr_text(s) for s in S if s["name"] == "PROMISE"), "")
    v = max([len(phrases(x)) for x in sentences(p)] or [0])
    return v, atmost(v, 4, 6)


@metric(1, "banned openers (สวัสดี / ในคลิปนี้ / วันนี้เราจะ)")
def r1_banned(meta, S):
    t = first_secs_text(S, 45)
    hits = len(re.findall(r"สวัสดี|ยินดีต้อนรับ|วันนี้เราจะ|ในคลิปนี้|ในวิดีโอนี้|ในตอนนี้เราจะ|ก่อนอื่น|ก่อนจะเริ่ม|กดติดตาม|กดไลก์|กดไลค์", t))
    return hits, 1.0 if hits == 0 else 0.0


@metric(1, "title/thumbnail words confirmed in first 30s")
def r1_match(meta, S):
    if "title" not in meta:
        return "no title", 0.0
    keys = content_words(meta["title"] + " " + meta.get("thumb", ""))
    t = first_secs_text(S, 30)
    hit = [k for k in keys if k in t]
    return f"{len(hit)}/{len(keys)}", len(hit) / max(1, len(keys))


@metric(1, "hook question asks HOW/WHY (ending is known)")
def r1_how(meta, S):
    ok = any(is_question(q) and re.search(r"ทำไม|อย่างไร|ยังไง|เพราะอะไร", q) for q in sentences(spoken_lines(S[0])))
    return ok, 1.0 if ok else 0.0


# ---------- Round 2: writing for the ear ----------
def sent_secs(S):
    return [secs(x) for x in all_sents(S)]


@metric(2, "mean sentence length (3-6.5 s)")
def r2_mean(meta, S):
    v = st.mean(sent_secs(S))
    return round(v, 1), band(v, 3, 6.5, 3.5)


@metric(2, "% sentences over 8 s (<=10%)")
def r2_long(meta, S):
    L = sent_secs(S)
    v = 100 * sum(x > 8 for x in L) / len(L)
    return round(v, 1), atmost(v, 10, 30)


@metric(2, "longest sentence (<=11 s)")
def r2_max(meta, S):
    v = max(sent_secs(S))
    return round(v, 1), atmost(v, 11, 8)


@metric(2, "breath groups: mean length (1-3 s)")
def r2_breath(meta, S):
    P = [secs(p) for x in all_sents(S) for p in phrases(x)]
    v = st.mean(P)
    return round(v, 2), band(v, 1.0, 3.0, 1.5)


@metric(2, "breath groups over 4 s (<=10%)")
def r2_breath_long(meta, S):
    P = [secs(p) for x in all_sents(S) for p in phrases(x)]
    v = 100 * sum(p > 4 for p in P) / len(P)
    return round(v, 1), atmost(v, 10, 30)


@metric(2, "passive (ถูก/โดน/ได้รับการ) per 10 sentences (<=1)")
def r2_passive(meta, S):
    ss = all_sents(S)
    n = sum(len(re.findall(r"ถูก(?!ต้อง|ใจ|กว่า)|โดน|ได้รับการ", x)) for x in ss)
    v = 10 * n / len(ss)
    return round(v, 2), atmost(v, 1, 2)


def count_numbers(x: str) -> int:
    x = re.sub(r"\d{1,2}\s*(?:" + MONTHS + r")(\s*(?:ค\.ศ\.|พ\.ศ\.)?\s*\d{3,4})?", " DATE ", x)  # a date is one fact
    x = re.sub(r"(?:ค\.ศ\.|พ\.ศ\.)\s*\d+", " DATE ", x)
    x = re.sub(r"ที่(?:" + NUMW + r")+", " ", x)                      # ordinals: คอนสแตนตินที่สิบเอ็ด, วันที่...
    x = re.sub(r"(?:หลาย|ไม่กี่|นับ)(?:" + NUMW + r")+", " ", x)       # vague: หลายร้อย is not a number to remember
    x = re.sub(r"(?:" + NUMW + r"|หนึ่ง)+", lambda m: " NUM " if m.group(0) != "หนึ่ง" else " ", x)  # เจ็ดพัน = one
    return len(re.findall(r"DATE|NUM|\d[\d,.]*", x))


@metric(2, "sentences with 2+ numbers (0)")
def r2_nums(meta, S):
    v = sum(count_numbers(x) >= 2 for x in all_sents(S))
    return v, atmost(v, 0, 5)


@metric(2, "stacked clauses: ซึ่ง/โดยที่/อันเป็น per 100 words (<=0.5)")
def r2_which(meta, S):
    t = "\n".join(narr_text(s) for s in S)
    v = 100 * len(re.findall(r"ซึ่ง|โดยที่|อันเป็น|อันซึ่ง", t)) / max(1, len(words(t)))
    return round(v, 2), atmost(v, 0.5, 1)


@metric(2, "long sentence followed by a short one (>=70%)")
def r2_follow(meta, S):
    L = sent_secs(S)
    longs = [i for i, l in enumerate(L[:-1]) if l >= 7]
    if not longs:
        return "no long sentences", 1.0
    v = 100 * sum(L[i + 1] <= 4 for i in longs) / len(longs)
    return round(v), atleast(v, 70)


@metric(2, "rhythm: sentence-length variation CV (0.35-0.7)")
def r2_cv(meta, S):
    L = sent_secs(S)
    v = st.pstdev(L) / st.mean(L)
    return round(v, 2), band(v, 0.35, 0.7, 0.25)


# ---------- Round 3: narrative drive ----------
STORY = EN.STORY


def story_secs(S):
    return [s for s in S if any(s["name"].startswith(k) for k in STORY)]


AND_THEN = r"แล้วก็|(?:^|\n)\s*(?:จากนั้น|หลังจากนั้น|ต่อมา|แล้วต่อมา)"
CAUSAL = (r"^(แต่|ดังนั้น|เพราะฉะนั้น|เพราะอย่างนั้น|เพราะแบบนั้น|ผลก็คือ|นั่นทำให้|และนั่นทำให้|ถึงอย่างนั้น|ถึงกระนั้น|"
          r"แม้กระนั้น|ทว่า|กระนั้น|ซ้ำร้าย|ยิ่งไปกว่านั้น|แทนที่|ตอนนี้|นี่จึง|จึง|เขากลับ|พวกเขากลับ|แล้วอะไร)")


@metric(3, "'and then' links between beats (0)")
def r3_andthen(meta, S):
    t = "\n".join(x for s in S for x in sentences(spoken_lines(s)))
    v = len(re.findall(AND_THEN, t))
    return v, atmost(v, 0, 5)


@metric(3, "but/therefore links per minute of story (>=2)")
def r3_causal(meta, S):
    ss = [x for s in story_secs(S) for x in sentences(narr_text(s))]
    n = sum(bool(re.match(CAUSAL, x)) for x in ss)
    v = n / (sum(secs(x) for x in ss) / 60)
    return round(v, 2), atleast(v, 2)


OBST = (r"ไม่ได้|ไม่พอ|ล้มเหลว|เป็นไปไม่ได้|ไม่มีทาง|ปัญหา|ปฏิเสธ|ขวาง|กันไว้|แข็งแรงเกิน|น้อยเกิน|สายเกิน|ยอมแพ้|โกรธ|"
        r"เว้นแต่|ทางเดียว|ไม่ยอม|ผิดแผน|ไม่มีเงิน|ล้อม")


@metric(3, "story sections with an explicit obstacle (all)")
def r3_obst(meta, S):
    ss = story_secs(S)
    hit = [s["name"] for s in ss if re.search(OBST, spoken_lines(s))]
    return f"{len(hit)}/{len(ss)}", len(hit) / len(ss)


TEASE = r"\?|แต่|ยังไม่|อีกไม่นาน|กำลังจะ|จะ|ต่อไป|ปัญหา|ไม่รู้เลยว่า|คำถาม|" + QWORDS


@metric(3, "sections before the climax ending on an open loop")
def r3_end(meta, S):
    ss = [s for s in S if s["name"] not in ("CLOSE", "TURNING POINT")]
    ok = [s["name"] for s in ss if re.search(TEASE, " ".join(sentences(narr_text(s))[-2:]))]
    return f"{len(ok)}/{len(ss)}", len(ok) / len(ss)


@metric(3, "longest stretch without a question or tease (<=90s)")
def r3_gap(meta, S):
    gap = worst = 0.0
    for x in [x for s in S for x in sentences(spoken_lines(s))]:
        gap += secs(x)
        if is_question(x) or re.search(r"ยังไม่จบ|อีกไม่นาน|คำถามที่แท้จริง|เกิดอะไรขึ้นต่อ|เป็นแค่จุดเริ่มต้น|มีปัญหา|จะต้องเสียใจ|สิ่งที่เขาไม่รู้", x):
            worst, gap = max(worst, gap), 0.0
    worst = max(worst, gap)
    return round(worst), atmost(worst, 90, 90)


WANT = r"ต้องการ|อยาก|จำต้อง|วางแผน|หวัง|วิงวอน|ขอร้อง|เร่ง|ปฏิเสธ|สาบาน|เลือก|ตั้งใจ|ยืนกราน|ตัดสินใจ|ไม่ยอม"


@metric(3, "named people with a stated want (>=3)")
def r3_want(meta, S):
    cast = names(meta, "cast")
    if not cast:
        return "no CAST: header", 0.0
    ss = [x for s in S for x in sentences(spoken_lines(s))]
    every = cast + names(meta, "places")
    wanters = {n for x in ss if re.search(WANT, x) for n in cast if has_name(n, x, every)}
    return ", ".join(sorted(wanters)) or "none", atleast(len(wanters), 3)


# ---------- Round 4: sound (cues are English; only the screen-off test reads Thai) ----------
for _name, _f in EN.METRICS[4]:
    if "screen-off" not in _name:
        METRICS.setdefault(4, []).append((_name, _f))


@metric(4, "screen-off test: visual-only phrases (0)")
def r4_deictic(meta, S):
    t = "\n".join(spoken_lines(s) for s in S)
    v = len(re.findall(r"อย่างที่เห็น|อย่างที่คุณเห็น|ดูนี่|ดูตรงนี้|ที่เห็นอยู่|ที่เห็นในภาพ|บนจอ|บนหน้าจอ|แผนที่นี้|ในภาพนี้|ตรงนี้", t))
    return v, 1.0 if v == 0 else max(0.0, 1 - v / 3)


# ---------- Round 5: rewatch, loyalty and series ----------
@metric(5, "ending calls back to the hook (>=4 shared words + answer)")
def r5_callback(meta, S):
    hook = next(s for s in S if s["name"] == "HOOK")
    close = next(s for s in S if s["name"] == "CLOSE")
    shared = content_words(spoken_lines(hook)) & content_words(spoken_lines(close))
    answered = bool(re.search(r"นั่นคือวิธีที่|นี่คือวิธีที่|คำตอบคือ|นั่นคือเหตุผลที่|นี่คือเหตุผลที่|นั่นคือคำตอบ|นี่คือคำตอบ", spoken_lines(close)))
    return f"{len(shared)} shared, answered={answered}", (min(1.0, len(shared) / 4) + answered) / 2


@metric(5, "peak (music-out reveal) at 60-85% of runtime")
def r5_peak(meta, S):
    pos, seen = None, 0.0
    for s in S:
        for kind, text in s.get("order", []):
            if kind == "cue" and s["name"] == "TURNING POINT" and re.search(r"MUSIC:.*\bout\b", text) and pos is None:
                pos = seen
            if kind == "text":
                seen += secs(text)
    if pos is None:
        return "no marked peak", 0.0
    v = 100 * pos / seen
    return f"{v:.0f}%", band(v, 60, 85, 20)


@metric(5, "no generic CTA; last line is story or sign-off")
def r5_cta(meta, S):
    close = next(s for s in S if s["name"] == "CLOSE")
    t = spoken_lines(close)
    generic = len(re.findall(r"กดไลก์|กดไลค์|กดกระดิ่ง|ถ้าชอบคลิปนี้|ถ้าคุณชอบคลิปนี้|ฝากกดติดตาม|อย่าลืมกดติดตาม|คอมเมนต์", t))
    last = sentences(narr_text(close))[-1]
    sign = meta.get("signoff", "")
    ok_last = bool(sign and sign in last)
    return f"generic={generic}, signoff_last={ok_last}", ((generic == 0) + ok_last) / 2


@metric(5, "direct address 'คุณ' per minute (1-4)")
def r5_you(meta, S):
    t = "\n".join(spoken_lines(s) for s in S)
    v = len(re.findall(r"คุณ(?!หญิง|ภาพ|ค่า|สมบัติ|ธรรม|ประโยชน์)", t)) / (secs(t) / 60)
    return round(v, 2), band(v, 1, 4, 1)


@metric(5, "specific next-episode tease in CLOSE")
def r5_next(meta, S):
    close = next(s for s in S if s["name"] == "CLOSE")
    t = spoken_lines(close)
    named = names(meta, "cast") + names(meta, "places")
    q = [x for x in sentences(t) if is_question(x)]
    ok = bool(re.search(r"ตอนหน้า|คลิปหน้า|ตอนต่อไป|คราวหน้า|ครั้งหน้า", t)) and any(not named or any(n in x for n in named) for x in q)
    return ok, 1.0 if ok else 0.0


@metric(5, "setups paid off: names from first 40% reused in last 30% (>=4)")
def r5_payoff(meta, S):
    named = names(meta, "cast") + names(meta, "places")
    if not named:
        return "no CAST:/PLACES: header", 0.0
    t = "\n".join(spoken_lines(s) for s in S)
    a, b = t[: int(len(t) * 0.4)], t[int(len(t) * 0.7):]
    reused = sorted(n for n in named if has_name(n, a, named) and has_name(n, b, named))
    return ", ".join(reused), atleast(len(reused), 4)


METRICS.setdefault(5, []).append(("channel template sections all present", EN.r5_template))


# ---------- runner ----------
def run(path, rounds):
    meta, S = parse(path)
    t = "\n".join(spoken_lines(s) for s in S)
    base = {"language": "th", "syllables": syllables(t), "words": len(words(t)),
            "est_minutes": round((secs(t) + sum(pause_seconds(s) for s in S)) / 60, 1)}
    res = {"file": path, "base": base, "rounds": {}}
    for r in rounds:
        rows = []
        for name, f in METRICS.get(r, []):
            v, sc = f(meta, S)
            rows.append({"metric": name, "value": v, "score": round(sc, 2)})
        res["rounds"][r] = {"rows": rows, "score": round(100 * st.mean(x["score"] for x in rows), 1) if rows else None}
    return res
