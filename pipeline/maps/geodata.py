"""Geography for our animated maps (TASKS P3.3).

Two sources, both free and keyless:
- Natural Earth 10m land (public domain): coasts for regional maps (Balkans, Anatolia, Southeast Asia).
  Too coarse for a city: at 10m the Golden Horn does not exist.
- OpenStreetMap coastline through the Overpass API (ODbL): coasts for city maps. Any video that shows it
  must credit "Map data © OpenStreetMap contributors"; the geojson carries that credit and the map renderer
  copies it into the episode manifest.

Outputs are GeoJSON FeatureCollections of land polygons in lon/lat, written to data/geo/<name>.geojson.
"""
from __future__ import annotations

import json
from pathlib import Path

from shapely import STRtree
from shapely.geometry import LineString, MultiPolygon, Polygon, box, mapping, shape
from shapely.ops import linemerge, polygonize, unary_union

from pipeline.assets.common import Http

ROOT = Path(__file__).resolve().parents[2]
GEO_DIR = ROOT / "data" / "geo"
CACHE = GEO_DIR / "cache"
NE_LAND_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_land.geojson"
OVERPASS = "https://overpass-api.de/api/interpreter"
CREDIT_OSM = "Map data © OpenStreetMap contributors (ODbL)"
CREDIT_NE = "Made with Natural Earth (public domain)"


def overpass_coastlines(http: Http, bbox: tuple[float, float, float, float]) -> list[list[tuple[float, float]]]:
    """Coastline ways that touch bbox (west, south, east, north), full geometry, as lon/lat lists."""
    w, s, e, n = bbox
    q = f'[out:json][timeout:90];way["natural"="coastline"]({s},{w},{n},{e});out geom;'
    data = http.json(OVERPASS, {"data": q})
    return [[(p["lon"], p["lat"]) for p in el["geometry"]] for el in data.get("elements", []) if el.get("geometry")]


def land_from_coastlines(ways: list[list[tuple[float, float]]], bbox) -> MultiPolygon:
    """Cut the bbox into faces along the coastlines and keep the land faces.

    OSM rule: land is on the LEFT of a coastline way. Each face is classified by the coastline segment
    nearest to a point inside it: left of that segment = land.
    """
    frame = box(*bbox)
    merged = linemerge([LineString(w) for w in ways if len(w) >= 2])
    inside = merged.intersection(frame)
    faces = list(polygonize(unary_union([frame.boundary, inside])))
    segs, dirs = [], []
    for w in ways:
        for a, b in zip(w, w[1:]):
            if a != b:
                segs.append(LineString([a, b]))
                dirs.append((a, b))
    tree = STRtree(segs)
    land = []
    for f in faces:
        p = f.representative_point()
        i = int(tree.nearest(p))
        (ax, ay), (bx, by) = dirs[i]
        cross = (bx - ax) * (p.y - ay) - (by - ay) * (p.x - ax)
        if cross > 0:
            land.append(f)
    u = unary_union(land)
    return u if isinstance(u, MultiPolygon) else MultiPolygon([u]) if isinstance(u, Polygon) else MultiPolygon()


def ne_land(http: Http, bbox) -> MultiPolygon:
    CACHE.mkdir(parents=True, exist_ok=True)
    raw = CACHE / "ne_10m_land.geojson"
    if not raw.exists():
        raw.write_bytes(http.get(NE_LAND_URL))
    frame = box(*bbox)
    parts = []
    for feat in json.loads(raw.read_text(encoding="utf-8"))["features"]:
        g = shape(feat["geometry"])
        if g.intersects(frame):
            parts.append(g.intersection(frame))
    u = unary_union(parts)
    return u if isinstance(u, MultiPolygon) else MultiPolygon([u]) if isinstance(u, Polygon) else MultiPolygon(
        [g for g in getattr(u, "geoms", []) if isinstance(g, Polygon)])


def write_land(name: str, geom: MultiPolygon, bbox, source: str, credit: str, tolerance: float) -> Path:
    geom = geom.simplify(tolerance, preserve_topology=True)
    GEO_DIR.mkdir(parents=True, exist_ok=True)
    out = GEO_DIR / f"{name}.geojson"
    fc = {"type": "FeatureCollection", "bbox": list(bbox),
          "properties": {"source": source, "credit": credit, "simplify_deg": tolerance},
          "features": [{"type": "Feature", "properties": {"kind": "land"}, "geometry": mapping(geom)}]}
    out.write_text(json.dumps(fc, separators=(",", ":")), encoding="utf-8")
    return out


def load_land(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
