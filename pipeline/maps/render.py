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
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


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
    land, credit = land_for_view(library["land"], view)
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
                 "source_url": "", "licence": "own work; map data as credited",
                 "credit": credit or "own work", "ai_generated": "n", "notes": "class=own; tools/map.py"})
    write_manifest(mpath, rows)
    return True
