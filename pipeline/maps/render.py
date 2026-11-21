"""Turn a map library clip (data/maps/<name>.yaml) into Remotion props and render it (TASKS P3.3).

A library holds the land source, named features (lines, areas, markers, labels) and clips. A clip picks
features and gives each a time: `appear` (fade in), `draw` [start, end] (lines draw on), `hide` (fade out),
plus the view box, an optional camera move and a title. Remotion (video/src/maps) draws the frames.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml
from shapely.geometry import box, mapping, shape

from pipeline.assets.common import read_manifest, write_manifest

ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "video"
REMOTION_CLI = VIDEO / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
TIMING_KEYS = ("appear", "draw", "hide", "grow", "run")
RANGE_KEYS = ("draw", "grow", "run")


class MapError(ValueError):
    pass


def load_library(path: Path) -> dict:
    """A library may `extends: <other>.yaml` (same folder): it inherits that file's land and features."""
    path = Path(path)
    lib = yaml.safe_load(path.read_text(encoding="utf-8"))
    if lib.get("extends"):
        base = load_library(path.parent / lib["extends"])
        lib["features"] = {**base.get("features", {}), **lib.get("features", {})}
        lib.setdefault("land", base.get("land"))
    return lib


def _round(obj, nd=5):
    if isinstance(obj, float):
        return round(obj, nd)
    if isinstance(obj, (list, tuple)):
        return [_round(x, nd) for x in obj]
    if isinstance(obj, dict):
        return {k: _round(v, nd) for k, v in obj.items()}
    return obj


def land_for_view(land_name: str, view, margin: float = 0.4) -> tuple[dict, str]:
    """Land polygons cut to the view box plus a margin (room for camera moves), and the data credit."""
    fc = json.loads((ROOT / "data" / "geo" / f"{land_name}.geojson").read_text(encoding="utf-8"))
    w, s, e, n = view
    dx, dy = (e - w) * margin, (n - s) * margin
    frame = box(w - dx, s - dy, e + dx, n + dy)
    feats = []
    for f in fc["features"]:
        g = shape(f["geometry"]).intersection(frame)
        if not g.is_empty:
            feats.append({"type": "Feature", "properties": {}, "geometry": _round(mapping(g))})
    return {"type": "FeatureCollection", "features": feats}, fc.get("properties", {}).get("credit", "")


def build_props(library: dict, clip: str, width: int = 1920, height: int = 1080, fps: int = 30,
                palette: str = "parchment") -> dict:
    clips = library.get("clips", {})
    if clip not in clips:
        raise MapError(f"no clip {clip!r}; have: {', '.join(clips)}")
    c, feats = clips[clip], library.get("features", {})
    layers = []
    for item in c.get("show", []):
        name = item.get("use")
        if name not in feats:
            raise MapError(f"clip {clip}: unknown feature {name!r}")
        layer = dict(feats[name])
        layer.update({k: item[k] for k in TIMING_KEYS if k in item})
        for k in RANGE_KEYS:
            v = layer.get(k)
            if v is not None and (len(v) != 2 or v[0] >= v[1]):
                raise MapError(f"clip {clip}: {name}: {k} must be [start, end] with start < end")
        layers.append(layer)
    view = c["view"]
    land, credit = land_for_view(c.get("land", library["land"]), view)   # a clip may use other geography
    props = {"width": width, "height": height, "fps": fps, "durationSec": float(c["duration"]),
             "palette": c.get("palette", palette), "view": view, "land": land, "layers": layers}
    if c.get("camera"):
        props["camera"] = c["camera"]
    if c.get("title"):
        props["title"] = c["title"]
    if credit and "OpenStreetMap" in credit:
        props["credit"] = "© OpenStreetMap contributors"   # ODbL asks for it where the map is shown
    props["_credit_full"] = credit
    return props


def write_props(props: dict, name: str) -> Path:
    out = VIDEO / "out" / "props" / f"{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({k: v for k, v in props.items() if not k.startswith("_")}), encoding="utf-8")
    return out


def remotion(args: list[str]) -> None:
    """Call the Remotion CLI with node directly: the Windows shell would strip quotes from arguments."""
    if not REMOTION_CLI.exists():
        raise MapError("Remotion is not installed: run `npm install` in video/")
    r = subprocess.run(["node", str(REMOTION_CLI), *args], cwd=VIDEO)
    if r.returncode != 0:
        raise MapError(f"remotion {args[0]} failed (exit {r.returncode})")


def render(props_file: Path, out: Path, still_at: float | None = None, fps: int = 30) -> Path:
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    if still_at is not None:
        remotion(["still", "src/index.ts", "MapScene", str(out), f"--props={props_file}", f"--frame={int(still_at * fps)}"])
    else:
        remotion(["render", "src/index.ts", "MapScene", str(out), f"--props={props_file}"])
    return out


def log_to_manifest(out: Path, clip: str, credit: str) -> bool:
    """When the render lands inside an episode folder, record it in that episode's manifest (rights gate)."""
    out = Path(out).resolve()
    for parent in out.parents:
        if parent.parent.name == "episodes":
            ep = parent
            break
    else:
        return False
    mpath = ep / "assets" / "manifest.csv"
    rows = [r for r in read_manifest(mpath) if r["asset_id"] != f"map-{clip}"]
    rows.append({"asset_id": f"map-{clip}", "file": out.relative_to(ep).as_posix(), "source": "own map",
                 "source_url": f"own:tools/map.py {clip}",   # the upload preflight needs a source on every row "licence": "own work; map data as credited",
                 "credit": credit or "own work", "ai_generated": "n", "notes": "class=own; tools/map.py"})
    write_manifest(mpath, rows)
    return True


# ---------------------------------------------------------------- episode binding (P4.4)
def library_ref(library_path: Path, clip: str) -> str:
    """How an inline map is named in an episode manifest: <library path from the repo root>#<clip>."""
    return f"{Path(library_path).resolve().relative_to(ROOT).as_posix()}#{clip}"


def bind(library_path: Path, ep: Path) -> dict:
    """Clips with `shot: sNNN.k` (or a list) become the asset of those shots: `map-<clip>` in the shot list
    cell and a manifest row with the map-data credit. The episode render draws them inline (no mp4)."""
    import csv
    library_path, ep = Path(library_path), Path(ep)
    lib = load_library(library_path)
    want: dict[tuple[int, int], str] = {}
    for name, c in lib.get("clips", {}).items():
        shots = c.get("shot") or []
        for sid in [shots] if isinstance(shots, str) else shots:
            no, _, k = sid.lstrip("s").partition(".")
            key = (int(no), int(k or 1) - 1)
            if key in want:
                raise MapError(f"shot {sid} bound twice: {want[key]} and {name}")
            want[key] = name
    path = ep / "shotlist.csv"
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        cols, rows = reader.fieldnames, list(reader)
    done, problems = [], []
    for r in rows:
        no = int(r["sentence_no"])
        terms = [t.strip() for t in r["search_terms"].split("|") if t.strip()]
        vts = [v.strip() for v in r["visual_type"].split("|")]
        ids = [x.strip() for x in (r.get("asset_id") or "").split("|")]
        ids += [""] * (len(terms) - len(ids))
        for j in range(len(terms)):
            name = want.pop((no, j), None)
            if not name:
                continue
            vt = vts[j] if len(vts) > 1 else vts[0]
            if vt != "map":
                problems.append(f"s{no:03d}.{j + 1} is {vt}, not map (clip {name})")
                continue
            ids[j] = f"map-{name}"
            done.append(f"s{no:03d}.{j + 1}")
        r["asset_id"] = " | ".join(ids[:len(terms)]) if len(terms) > 1 else ids[0]
    problems += [f"s{no:03d}.{j + 1}: no such shot (clip {n})" for (no, j), n in want.items()]
    if problems:
        raise MapError("; ".join(problems))
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    mpath = ep / "assets" / "manifest.csv"
    keep = [m for m in read_manifest(mpath) if not m["asset_id"].startswith("map-") or "#" not in m["file"]]
    for name, c in lib.get("clips", {}).items():
        if not c.get("shot"):
            continue
        fc = json.loads((ROOT / "data" / "geo" / f"{c.get('land', lib['land'])}.geojson").read_text(encoding="utf-8"))
        credit = fc.get("properties", {}).get("credit", "") or "own work"
        keep.append({"asset_id": f"map-{name}", "file": library_ref(library_path, name), "source": "own map",
                     "source_url": f"own:tools/map.py {name}", "licence": "own work; map data as credited",
                     "credit": credit, "ai_generated": "n",
                     "notes": "class=own; drawn inline by the episode render" + ("; borders approximate" if c.get("approximate") else "")})
    write_manifest(mpath, keep)
    return {"bound": done}


def contact_sheet(library: dict, names: list[str], out: Path, at: float | None = None, cols: int = 3) -> Path:
    """All clips side by side at 960x540 (end state, or `at` seconds): one bundle for every still."""
    from PIL import Image, ImageDraw
    if not REMOTION_CLI.exists():
        raise MapError("Remotion is not installed: run `npm install` in video/")
    tmp = VIDEO / "out" / "sheet"
    tmp.mkdir(parents=True, exist_ok=True)
    jobs = []
    for name in names:
        props = build_props(library, name, 960, 540, 30)
        pf = tmp / f"{name}.json"
        pf.write_text(json.dumps({k: v for k, v in props.items() if not k.startswith("_")}), encoding="utf-8")
        sec = at if at is not None else props["durationSec"] - 0.05
        jobs.append({"props": str(pf), "out": str(tmp / f"{name}.png"), "frame": max(0, int(sec * 30))})
    jf = tmp / "jobs.json"
    jf.write_text(json.dumps(jobs), encoding="utf-8")
    r = subprocess.run(["node", "scripts/stills.mjs", str(jf)], cwd=VIDEO)
    if r.returncode != 0:
        raise MapError("stills failed")
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 960, rows * 570), "white")
    d = ImageDraw.Draw(sheet)
    for i, name in enumerate(names):
        x, y = (i % cols) * 960, (i // cols) * 570
        with Image.open(tmp / f"{name}.png") as im:
            sheet.paste(im.convert("RGB"), (x, y + 30))
        d.text((x + 8, y + 6), name, fill="black")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out
