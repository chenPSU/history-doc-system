import type {LonLat} from './types';

// Web Mercator, fitted so the view box covers the frame (like CSS object-fit: cover).
const mercY = (lat: number) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));

export type Projector = (p: LonLat) => [number, number];

// cover: the view fills the frame (16:9 episodes); contain: the whole view shows, more land/sea around it (9:16 Shorts)
export function fitProjection(view: [number, number, number, number], width: number, height: number, mode: 'cover' | 'contain' = 'cover'): Projector {
  const [w, s, e, n] = view;
  const x0 = (w * Math.PI) / 180;
  const x1 = (e * Math.PI) / 180;
  const y0 = mercY(n);
  const y1 = mercY(s);
  const scale = (mode === 'contain' ? Math.min : Math.max)(width / (x1 - x0), height / (y0 - y1));
  const cx = (x0 + x1) / 2;
  const cy = (y0 + y1) / 2;
  return ([lon, lat]) => [width / 2 + ((lon * Math.PI) / 180 - cx) * scale, height / 2 - (mercY(lat) - cy) * scale];
}

export function pathD(points: [number, number][], close = false): string {
  if (!points.length) return '';
  const body = points.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join('');
  return close ? body + 'Z' : body;
}

export function polylineLength(points: [number, number][]): number {
  let len = 0;
  for (let i = 1; i < points.length; i++) len += Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]);
  return len;
}

// Point and heading (radians) at fraction f of a polyline's length.
export function pointAt(points: [number, number][], f: number): {x: number; y: number; angle: number} {
  const total = polylineLength(points);
  let target = Math.max(0, Math.min(1, f)) * total;
  for (let i = 1; i < points.length; i++) {
    const [ax, ay] = points[i - 1];
    const [bx, by] = points[i];
    const seg = Math.hypot(bx - ax, by - ay);
    if (target <= seg || i === points.length - 1) {
      const t = seg ? Math.min(1, target / seg) : 0;
      return {x: ax + (bx - ax) * t, y: ay + (by - ay) * t, angle: Math.atan2(by - ay, bx - ax)};
    }
    target -= seg;
  }
  const [x, y] = points[points.length - 1];
  return {x, y, angle: 0};
}
