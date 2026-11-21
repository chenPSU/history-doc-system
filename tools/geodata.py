#!/usr/bin/env python3
"""Build land polygons for animated maps (TASKS P3.3). Free sources, no API keys.

  python tools/geodata.py osm constantinople --bbox 28.86,40.96,29.08,41.09     # city coast (OSM, ODbL)
  python tools/geodata.py ne eastmed --bbox 12,30,46,49 --tolerance 0.01        # region (Natural Earth, PD)

Writes data/geo/<name>.geojson. City maps need OSM: Natural Earth has no Golden Horn.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.assets import episode as assets_cfg  # noqa: E402
from pipeline.assets.common import Http  # noqa: E402
from pipeline.maps import geodata  # noqa: E402


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", choices=["osm", "ne"])
    ap.add_argument("name")
    ap.add_argument("--bbox", required=True, help="west,south,east,north in degrees")
    ap.add_argument("--tolerance", type=float, help="simplify, degrees (default osm 0.00004, ne 0.005)")
    a = ap.parse_args(argv)
    bbox = tuple(float(x) for x in a.bbox.split(","))
    http = Http(assets_cfg.user_agent(assets_cfg.load_config()), delay=1.0)
    if a.source == "osm":
        ways = geodata.overpass_coastlines(http, bbox)
        land = geodata.land_from_coastlines(ways, bbox)
        out = geodata.write_land(a.name, land, bbox, "OpenStreetMap coastline via Overpass API", geodata.CREDIT_OSM,
                                 a.tolerance or 0.00004)
        print(f"{len(ways)} coastline ways -> {len(land.geoms)} land polygons")
    else:
        land = geodata.ne_land(http, bbox)
        out = geodata.write_land(a.name, land, bbox, "Natural Earth 10m land", geodata.CREDIT_NE, a.tolerance or 0.005)
        print(f"{len(land.geoms)} land polygons")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
