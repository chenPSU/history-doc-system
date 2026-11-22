import React, {useMemo} from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {palette as getPalette, SIDES} from './palettes';
import {fitProjection, pathD, pointAt, polylineLength} from './projection';
import type {CameraKey, Layer, LonLat, MapProps, Timing} from './types';

const FONT = "Georgia, 'Times New Roman', serif";
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const ease = Easing.inOut(Easing.cubic);

type XY = [number, number];

const titlePlace = (pos: 'bl' | 'br' | 'tl' | 'tr', m: number): React.CSSProperties =>
  ({bl: {left: m, bottom: m}, br: {right: m, bottom: m}, tl: {left: m, top: m}, tr: {right: m, top: m}})[pos];

function visibility(t: number, l: Timing): number {
  const timed = l as Timing & {grow?: [number, number]; run?: [number, number]};
  const start = l.appear ?? l.draw?.[0] ?? timed.grow?.[0] ?? timed.run?.[0] ?? 0;
  let v = interpolate(t, [start, start + 0.6], [0, 1], clamp);
  if (l.hide !== undefined) v *= interpolate(t, [l.hide, l.hide + 0.6], [1, 0], clamp);
  return v;
}

function drawn(t: number, l: Timing): number {
  if (!l.draw) return 1;
  return interpolate(t, l.draw, [0, 1], {...clamp, easing: ease});
}

function cameraAt(keys: CameraKey[] | undefined, t: number): {center?: LonLat; zoom: number} {
  if (!keys || !keys.length) return {zoom: 1};
  if (t <= keys[0].t) return keys[0];
  for (let i = 1; i < keys.length; i++) {
    const a = keys[i - 1];
    const b = keys[i];
    if (t <= b.t) {
      const f = ease((t - a.t) / Math.max(1e-6, b.t - a.t));
      return {
        center: [a.center[0] + (b.center[0] - a.center[0]) * f, a.center[1] + (b.center[1] - a.center[1]) * f],
        zoom: a.zoom + (b.zoom - a.zoom) * f,
      };
    }
  }
  return keys[keys.length - 1];
}

// The part of a polyline from its start to fraction f of its length.
function partial(points: XY[], f: number): XY[] {
  if (f >= 1) return points;
  if (f <= 0 || points.length < 2) return [];
  const total = polylineLength(points);
  let left = total * f;
  const out: XY[] = [points[0]];
  for (let i = 1; i < points.length; i++) {
    const seg = Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]);
    if (left >= seg) {
      out.push(points[i]);
      left -= seg;
    } else {
      const k = seg ? left / seg : 0;
      out.push([points[i - 1][0] + (points[i][0] - points[i - 1][0]) * k, points[i - 1][1] + (points[i][1] - points[i - 1][1]) * k]);
      break;
    }
  }
  return out;
}

export const MapScene: React.FC<MapProps> = (props) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const t = frame / fps;
  const pal = getPalette(props.palette);
  const uid = props.uid ?? 'map'; // unique per scene: two maps can be on screen during a dissolve
  const u = height / 1080; // size unit: 1 px at 1080p
  const base = useMemo(() => fitProjection(props.view, width, height, props.fit ?? 'cover'), [props.view, width, height, props.fit]);

  const cam = cameraAt(props.camera, t);
  const c = cam.center ? base(cam.center) : [width / 2, height / 2];
  const P = (p: LonLat): XY => {
    const [x, y] = base(p);
    return [width / 2 + (x - c[0]) * cam.zoom, height / 2 + (y - c[1]) * cam.zoom];
  };

  const land = props.land.features
    .map((f) => {
      const polys = (f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates) as number[][][][];
      return polys.map((rings) => rings.map((ring) => pathD(ring.map((p) => P(p as LonLat)), true)).join('')).join('');
    })
    .join('');

  const layers = props.layers.map((l, i) => <LayerView key={i} l={l} t={t} P={P} u={u} pal={pal} P0={{w: width, h: height}} uid={uid} />);
  const titleOpacity = props.title ? interpolate(t, [props.title.appear ?? 0.2, (props.title.appear ?? 0.2) + 0.8], [0, 1], clamp) : 0;

  return (
    <AbsoluteFill style={{backgroundColor: pal.water}}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <defs>
          <radialGradient id={`${uid}-sea`} cx="50%" cy="50%" r="75%">
            <stop offset="0%" stopColor={pal.water} />
            <stop offset="100%" stopColor={pal.waterDeep} />
          </radialGradient>
          <radialGradient id={`${uid}-vignette`} cx="50%" cy="50%" r="72%">
            <stop offset="60%" stopColor="#000" stopOpacity={0} />
            <stop offset="100%" stopColor="#000" stopOpacity={0.45} />
          </radialGradient>
          <filter id={`${uid}-paper`} x="0" y="0" width="100%" height="100%">
            <feTurbulence type="fractalNoise" baseFrequency={0.9 / u} numOctaves={2} seed={7} />
            <feColorMatrix type="matrix" values="0 0 0 0 0.25  0 0 0 0 0.18  0 0 0 0 0.1  0 0 0 0.9 -0.25" />
          </filter>
          <filter id={`${uid}-blur6`}>
            <feGaussianBlur stdDeviation={6 * u} />
          </filter>
          <clipPath id={`${uid}-landclip`}>
            <path d={land} fillRule="evenodd" />
          </clipPath>
        </defs>
        <rect width={width} height={height} fill={`url(#${uid}-sea)`} />
        {/* soft shadow of the coast on the water */}
        <path d={land} fill="none" stroke={pal.waterDeep} strokeWidth={14 * u} strokeOpacity={0.55} filter={`url(#${uid}-blur6)`} />
        <path d={land} fill={pal.land} fillRule="evenodd" />
        <rect width={width} height={height} filter={`url(#${uid}-paper)`} opacity={pal.paperGrain} clipPath={`url(#${uid}-landclip)`} />
        <path d={land} fill="none" stroke={pal.landEdge} strokeWidth={1.6 * u} fillRule="evenodd" />
        {layers}
        <rect width={width} height={height} fill={`url(#${uid}-vignette)`} />
      </svg>
      {props.title ? (
        <div
          style={{
            position: 'absolute', ...titlePlace(props.title.position ?? 'bl', 70 * u), opacity: titleOpacity, fontFamily: FONT, color: pal.ink,
            background: `${pal.land}e6`, padding: `${18 * u}px ${30 * u}px`, borderLeft: `${5 * u}px solid ${SIDES.ott}`,
            boxShadow: `0 ${4 * u}px ${18 * u}px rgba(0,0,0,0.35)`,
          }}
        >
          <div style={{fontSize: 44 * u, letterSpacing: 6 * u, textTransform: 'uppercase'}}>{props.title.text}</div>
          {props.title.sub ? <div style={{fontSize: 28 * u, fontStyle: 'italic', marginTop: 4 * u}}>{props.title.sub}</div> : null}
        </div>
      ) : null}
      {props.credit ? (
        <div style={{position: 'absolute', right: 24 * u, bottom: 16 * u, fontFamily: FONT, fontSize: 16 * u, color: '#fff', opacity: 0.7}}>
          {props.credit}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

const LayerView: React.FC<{l: Layer; t: number; P: (p: LonLat) => XY; u: number; pal: ReturnType<typeof getPalette>; P0: {w: number; h: number}; uid: string}> = ({l, t, P, u, pal, P0, uid}) => {
  const vis = visibility(t, l);
  if (vis <= 0) return null;
  const side = 'side' in l && l.side ? SIDES[l.side] : SIDES.neutral;
  const halo = {paintOrder: 'stroke' as const, stroke: pal.land, strokeWidth: 6 * u, strokeLinejoin: 'round' as const};

  if (l.type === 'line') {
    const pts = partial(l.coords.map(P), drawn(t, l));
    if (pts.length < 2) return null;
    const d = pathD(pts);
    if (l.style === 'wall') {
      const towers: XY[] = [];
      const len = polylineLength(pts);
      for (let s = 0; s <= len; s += 34 * u) {
        const p = pointAt(pts, len ? s / len : 0);
        towers.push([p.x, p.y]);
      }
      return (
        <g opacity={vis}>
          <path d={d} fill="none" stroke={pal.ink} strokeWidth={11 * u} strokeLinejoin="round" strokeLinecap="round" />
          <path d={d} fill="none" stroke={side} strokeWidth={5 * u} strokeLinejoin="round" strokeLinecap="round" />
          {towers.map(([x, y], i) => (
            <rect key={i} x={x - 5 * u} y={y - 5 * u} width={10 * u} height={10 * u} fill={pal.ink} />
          ))}
        </g>
      );
    }
    if (l.style === 'chain') {
      return (
        <g opacity={vis}>
          <path d={d} fill="none" stroke={pal.ink} strokeWidth={8 * u} strokeLinecap="round" />
          <path d={d} fill="none" stroke="#d8d2c4" strokeWidth={4 * u} strokeDasharray={`${9 * u} ${5 * u}`} strokeLinecap="round" />
        </g>
      );
    }
    if (l.style === 'route') {
      const tip = pointAt(pts, 1);
      const a = 22 * u;
      const head = [
        [tip.x + Math.cos(tip.angle) * a * 0.6, tip.y + Math.sin(tip.angle) * a * 0.6],
        [tip.x + Math.cos(tip.angle + 2.5) * a, tip.y + Math.sin(tip.angle + 2.5) * a],
        [tip.x + Math.cos(tip.angle - 2.5) * a, tip.y + Math.sin(tip.angle - 2.5) * a],
      ] as XY[];
      return (
        <g opacity={vis}>
          <path d={d} fill="none" stroke={pal.land} strokeOpacity={0.85} strokeWidth={11 * u} strokeLinecap="round" strokeLinejoin="round" />
          <path d={d} fill="none" stroke={side} strokeWidth={6 * u} strokeLinecap="round" strokeLinejoin="round" />
          {l.arrow ? <path d={pathD(head, true)} fill={side} stroke={pal.ink} strokeWidth={1.5 * u} /> : null}
        </g>
      );
    }
    return <path d={d} opacity={vis} fill="none" stroke={side} strokeWidth={3 * u} strokeDasharray={`${12 * u} ${8 * u}`} />;
  }

  if (l.type === 'area') {
    const pts = l.coords.map(P);
    const cx = pts.reduce((s, p) => s + p[0], 0) / pts.length;
    const cy = pts.reduce((s, p) => s + p[1], 0) / pts.length;
    let clip: string | undefined;
    let reveal: React.ReactNode = null;
    if (l.grow) {
      // Territory growth: a circle from the origin uncovers the area.
      const [ox, oy] = l.origin ? P(l.origin) : [cx, cy];
      const reach = Math.max(...pts.map(([x, y]) => Math.hypot(x - ox, y - oy))) * 1.05;
      const r = interpolate(t, l.grow, [0, reach], {...clamp, easing: ease});
      const id = `${uid}-grow-${Math.round(ox)}-${Math.round(oy)}-${pts.length}`;
      clip = `url(#${id})`;
      reveal = (
        <clipPath id={id}>
          <circle cx={ox} cy={oy} r={Math.max(0.01, r)} />
        </clipPath>
      );
    }
    return (
      <g opacity={vis}>
        {reveal}
        {/* territories stop at the coast */}
        <g clipPath={`url(#${uid}-landclip)`}>
          <path d={pathD(pts, true)} clipPath={clip} fill={side} fillOpacity={0.42} stroke={side} strokeWidth={3 * u} strokeDasharray={`${8 * u} ${5 * u}`} />
        </g>
        {l.label ? (
          <text x={cx} y={cy} textAnchor="middle" fontFamily={FONT} fontSize={24 * u} fill={pal.labelLand} fontStyle="italic" {...halo}>
            {l.label}
          </text>
        ) : null}
      </g>
    );
  }

  if (l.type === 'counter') {
    const n = Math.round(interpolate(t, l.run, [l.from, l.to], {...clamp, easing: Easing.out(Easing.quad)}));
    return (
      <g opacity={vis}>
        <rect x={P0.w - 400 * u} y={50 * u} width={330 * u} height={128 * u} fill={pal.land} fillOpacity={0.9} />
        <rect x={P0.w - 400 * u} y={50 * u} width={5 * u} height={128 * u} fill={SIDES.ott} />
        <text x={P0.w - 100 * u} y={145 * u} textAnchor="end" fontFamily={FONT} fontSize={84 * u} fill={pal.ink}
          style={{fontVariantNumeric: 'tabular-nums'}}>
          {`${l.prefix ?? ''}${n}${l.suffix ?? ''}`}
        </text>
      </g>
    );
  }

  if (l.type === 'marker') {
    const [x, y] = P(l.at);
    return (
      <g opacity={vis}>
        <circle cx={x} cy={y} r={12 * u} fill={pal.land} fillOpacity={0.85} />
        <circle cx={x} cy={y} r={9 * u} fill={side} stroke={pal.ink} strokeWidth={2 * u} />
        {l.label ? (
          <text x={x + 18 * u} y={y + 8 * u} fontFamily={FONT} fontSize={24 * u} fill={pal.labelLand} {...halo}>
            {l.label}
          </text>
        ) : null}
      </g>
    );
  }

  // label
  const [x, y] = P(l.at);
  const look = {
    city: {size: 38, spacing: 8, upper: true, italic: false, fill: pal.labelLand, halo: true},
    region: {size: 44, spacing: 14, upper: true, italic: false, fill: pal.labelLand, halo: true},
    place: {size: 24, spacing: 1, upper: false, italic: false, fill: pal.labelLand, halo: true},
    water: {size: 30, spacing: 6, upper: false, italic: true, fill: pal.labelWater, halo: false},
  }[l.kind];
  return (
    <text
      x={x}
      y={y}
      opacity={vis}
      textAnchor="middle"
      fontFamily={FONT}
      fontSize={look.size * u}
      letterSpacing={look.spacing * u}
      fontStyle={look.italic ? 'italic' : 'normal'}
      fill={look.fill}
      transform={l.angle ? `rotate(${l.angle} ${x} ${y})` : undefined}
      {...(look.halo ? halo : {})}
    >
      {look.upper ? l.text.toUpperCase() : l.text}
    </text>
  );
};
