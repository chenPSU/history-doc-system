"""Audio mix (TASKS P2.3): narration + music beds (ducked under the voice) + sound effects -> loudness-normalised mix.

Plan: audio/mix_plan.yaml (times in seconds on the episode timeline)

    music:   [{asset: wm-1, from: 0, to: 48.6, offset: 0, fade_in: 1.5, fade_out: 2.5, level_db: 0, loop: false}]
    sfx:     [{asset: wm-2, at: 23.6, dur: 7, level_db: -20, fade_in: 0.3, fade_out: 1.5, lowpass: 900}]

- Music is set to sit `MUSIC_BED_DB` below the narration's loudness, then a sidechain compressor keyed by the
  voice pushes it down further while someone speaks and lets it swell in the pauses (style guide: -20 to -25 dB
  under the voice). `level_db` nudges one bed.
- SFX `level_db` is relative to the narration loudness.
- Two-pass loudnorm to -14 LUFS integrated, -1 dBTP; `audio/mix_report.json` records ebur128 measurements (AC).
Everything is ffmpeg; nothing is sent anywhere.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import yaml

from pipeline.assets.common import read_manifest

MUSIC_BED_DB = -9.0           # bed level vs voice before ducking; ducking takes ~8 dB more under speech
TARGET_LUFS, TARGET_TP, TARGET_LRA = -14.0, -1.0, 11.0
SR = 48000


class MixError(RuntimeError):
    pass


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise MixError("ffmpeg not found")
    return exe


def loudness(path: Path, start: float | None = None, dur: float | None = None) -> dict:
    """Integrated loudness (LUFS), range (LU) and true peak (dBTP) via ebur128."""
    cmd = [_ffmpeg(), "-hide_banner", "-nostats"]
    if start is not None:
        cmd += ["-ss", f"{start}"]
    if dur is not None:
        cmd += ["-t", f"{dur}"]
    cmd += ["-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    summary = err[err.rfind("Summary:"):]
    get = lambda key: float(re.search(rf"{key}:\s+(-?[\d.]+|-inf)", summary).group(1).replace("-inf", "-99"))
    return {"integrated_lufs": get("I"), "lra_lu": get("LRA"), "true_peak_dbtp": get("Peak")}


def load_plan(ep: Path) -> dict:
    p = Path(ep) / "audio" / "mix_plan.yaml"
    if not p.exists():
        raise MixError(f"{p} missing")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def build_graph(ep: Path, plan: dict, start: float, end: float, voice_lufs: float, files: dict[str, Path],
                music_lufs: dict[str, float], voice_until: float | None = None) -> tuple[list[str], str]:
    """ffmpeg inputs + filter_complex for the window [start, end) of the episode timeline."""
    dur = end - start
    inputs = ["-ss", f"{start}", "-t", f"{dur}", "-i", str(Path(ep) / "audio" / "narration.wav")]
    # pad the voice to the window: the picture runs ~2 s past the last word and the music tail must too
    cut = "" if voice_until is None else f",volume=0:enable='gte(t,{voice_until - start:.3f})'"   # Shorts: music-only tail
    chains = [f"[0:a]aresample={SR},aformat=channel_layouts=stereo,apad=whole_dur={dur:.3f}{cut},asplit=2[voice][key]"]
    music_labels, sfx_labels, n = [], [], 1
    for k, m in enumerate(plan.get("music") or []):
        a, b = max(start, float(m["from"])), min(end, float(m["to"]))
        if b <= a:
            continue
        offset = float(m.get("offset", 0)) + (a - float(m["from"]))
        inputs += (["-stream_loop", "-1"] if m.get("loop") else []) + ["-ss", f"{offset}", "-t", f"{b - a}", "-i", str(files[m["asset"]])]
        gain = voice_lufs + MUSIC_BED_DB + float(m.get("level_db", 0)) - music_lufs[m["asset"]]
        fi = float(m.get("fade_in", 1.5)) if a == float(m["from"]) else 0.0
        fo = float(m.get("fade_out", 2.0)) if b == float(m["to"]) else 0.0
        f = f"[{n}:a]aresample={SR},aformat=channel_layouts=stereo,volume={gain:.2f}dB"
        if fi:
            f += f",afade=t=in:d={fi}"
        if fo:
            f += f",afade=t=out:st={max(0, b - a - fo):.3f}:d={fo}"
        f += f",adelay={int((a - start) * 1000)}:all=1[m{k}]"
        chains.append(f)
        music_labels.append(f"[m{k}]")
        n += 1
    for k, s in enumerate(plan.get("sfx") or []):
        a = float(s["at"])
        b = a + float(s.get("dur", 5))
        if b <= start or a >= end:
            continue
        cut_in = max(0.0, start - a)
        inputs += (["-stream_loop", "-1"] if s.get("loop") else []) + ["-ss", f"{float(s.get('offset', 0)) + cut_in}",
                                                                     "-t", f"{min(b, end) - max(a, start)}", "-i", str(files[s["asset"]])]
        f = f"[{n}:a]aresample={SR},aformat=channel_layouts=stereo"
        if s.get("lowpass"):
            f += f",lowpass=f={s['lowpass']}"
        f += f",volume={voice_lufs + float(s.get('level_db', -20)) - music_lufs.get(s['asset'], voice_lufs):.2f}dB"
        if s.get("fade_in"):
            f += f",afade=t=in:d={s['fade_in']}"
        if s.get("fade_out"):
            f += f",afade=t=out:st={max(0, min(b, end) - max(a, start) - float(s['fade_out'])):.3f}:d={s['fade_out']}"
        f += f",adelay={int((max(a, start) - start) * 1000)}:all=1[s{k}]"
        chains.append(f)
        sfx_labels.append(f"[s{k}]")
        n += 1
    mix_in = ["[voice]"]
    if music_labels:
        chains.append(f"{''.join(music_labels)}amix=inputs={len(music_labels)}:normalize=0[mus]")
        chains.append("[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=600:knee=4[duck]")
        mix_in.append("[duck]")
    else:
        chains.append("[key]anullsink")
    mix_in += sfx_labels
    chains.append(f"{''.join(mix_in)}amix=inputs={len(mix_in)}:normalize=0:duration=first[mix]")
    return inputs, ";".join(chains)


def mix(ep: Path, start: float = 0.0, end: float | None = None, out: Path | None = None, log=print,
        voice_until: float | None = None, write_report: bool = True) -> dict:
    ep = Path(ep)
    plan = load_plan(ep)
    man = {m["asset_id"]: m for m in read_manifest(ep / "assets" / "manifest.csv")}
    assets = {x["asset"] for x in (plan.get("music") or []) + (plan.get("sfx") or [])}
    missing = [a for a in assets if a not in man or not (ep / man[a]["file"]).exists()]
    if missing:
        raise MixError(f"assets not in the manifest or missing on disk: {missing}")
    files = {a: ep / man[a]["file"] for a in assets}
    narration = ep / "audio" / "narration.wav"
    if end is None:
        end = float(json.loads((ep / "audio" / "narration_timing.json").read_text(encoding="utf-8"))["total_seconds"]) + 2.0
    voice = loudness(narration)["integrated_lufs"]
    levels = {a: loudness(f)["integrated_lufs"] for a, f in files.items()}
    inputs, graph = build_graph(ep, plan, start, end, voice, files, levels, voice_until)
    out = Path(out or ep / "audio" / ("final_mix.wav" if start == 0 and end is None else f"mix_{int(start)}-{int(end)}.wav"))
    raw = out.with_suffix(".raw.wav")
    run = lambda args: subprocess.run([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], check=True)
    run([*inputs, "-filter_complex", graph, "-map", "[mix]", "-ar", str(SR), str(raw)])
    # two-pass loudnorm
    first = subprocess.run([_ffmpeg(), "-hide_banner", "-i", str(raw), "-af",
                            f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    m = json.loads(first[first.rfind("{"):first.rfind("}") + 1])
    run(["-i", str(raw), "-af",
         f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA={TARGET_LRA}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
         f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true",
         "-ar", str(SR), str(out)])
    raw.unlink()
    final = loudness(out)
    report = {"file": out.relative_to(ep).as_posix(), "window": [start, end], "narration_lufs": voice,
              "asset_lufs": levels, "music_bed_db_vs_voice": MUSIC_BED_DB, "target": {"lufs": TARGET_LUFS, "true_peak": TARGET_TP},
              "measured": final, "passed": abs(final["integrated_lufs"] - TARGET_LUFS) <= 1.0 and final["true_peak_dbtp"] <= TARGET_TP + 0.2}
    if write_report:                  # the episode's report (AC of P2.3); Shorts mixes do not overwrite it
        (ep / "audio" / "mix_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    log(f"{out}: {final}")
    return report


def mux(video: Path, audio: Path, out: Path) -> Path:
    """Replace the video's audio with the mix (video stream copied, AAC 192k)."""
    subprocess.run([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-i", str(audio),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
    return out
