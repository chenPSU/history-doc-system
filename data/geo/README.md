# Map geography (TASKS P3.3)

Land polygons in lon/lat, built by `tools/geodata.py`. Raw downloads go to `cache/` (not in git).

| File | Source | Licence | Credit on screen / in the description |
|---|---|---|---|
| `constantinople.geojson` | OpenStreetMap coastline via the Overpass API (bbox 28.86,40.96,29.08,41.09) | ODbL 1.0 | "© OpenStreetMap contributors" (the map renderer adds it to the frame and to the episode manifest) |
| `bosphorus.geojson` | OpenStreetMap coastline via Overpass (bbox 28.55,40.88,29.55,41.36) | ODbL 1.0 | "© OpenStreetMap contributors" |
| `med.geojson` | Natural Earth 10m land (bbox -12,24,52,57, tolerance 0.03) | Public domain | "Made with Natural Earth" |
| `eastmed.geojson` | Natural Earth 10m land (bbox 12,30,46,49) | Public domain | "Made with Natural Earth" (optional, we add it anyway) |

Natural Earth is used for regional maps. It is too coarse for cities: at 10m the Golden Horn does not exist,
so city maps use OpenStreetMap. Both are modern shorelines; note landfill where it matters (e.g. the
Marmara shore of Istanbul).

Rebuild:

```
python tools/geodata.py osm constantinople --bbox 28.86,40.96,29.08,41.09
python tools/geodata.py ne eastmed --bbox 12,30,46,49
python tools/geodata.py osm bosphorus --bbox 28.55,40.88,29.55,41.36
python tools/geodata.py ne med --bbox=-12,24,52,57 --tolerance 0.03
```
