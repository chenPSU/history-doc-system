// Props for one animated map clip. Python (tools/map.py) builds this JSON; Remotion draws it.
export type LonLat = [number, number];
export type Side = 'byz' | 'ott' | 'neutral';

export type Timing = {
  appear?: number; // seconds: fade in from here
  draw?: [number, number]; // seconds: lines draw on between these times
  hide?: number; // seconds: fade out from here
};

export type LineLayer = Timing & {
  type: 'line';
  coords: LonLat[];
  style: 'wall' | 'chain' | 'route' | 'border';
  side?: Side;
  arrow?: boolean;
  label?: string;
};

export type AreaLayer = Timing & {
  type: 'area';
  coords: LonLat[];
  side?: Side;
  label?: string;
  grow?: [number, number]; // seconds: territory spreads out from `origin` between these times
  origin?: LonLat;
};

export type CounterLayer = Timing & {
  type: 'counter';
  from: number;
  to: number;
  run: [number, number]; // seconds: count from `from` to `to` between these times
  prefix?: string; // e.g. "Day "
  suffix?: string; // e.g. " AD"
};

export type LabelLayer = Timing & {
  type: 'label';
  text: string;
  at: LonLat;
  kind: 'city' | 'water' | 'region' | 'place';
  angle?: number;
};

export type MarkerLayer = Timing & {
  type: 'marker';
  at: LonLat;
  side?: Side;
  label?: string;
};

export type Layer = LineLayer | AreaLayer | LabelLayer | MarkerLayer | CounterLayer;

export type LandGeo = {
  type: 'FeatureCollection';
  features: {geometry: {type: 'MultiPolygon' | 'Polygon'; coordinates: number[][][] | number[][][][]}}[];
};

export type CameraKey = {t: number; center: LonLat; zoom: number};

export type MapProps = {
  width: number;
  height: number;
  fps: number;
  durationSec: number;
  palette: string;
  view: [number, number, number, number]; // west, south, east, north: what fills the frame at zoom 1
  camera?: CameraKey[];
  land: LandGeo;
  layers: Layer[];
  title?: {text: string; sub?: string; appear?: number; position?: 'bl' | 'br' | 'tl' | 'tr'};
  credit?: string;
  uid?: string; // prefix for SVG ids when several maps share a page (episode render)
};
