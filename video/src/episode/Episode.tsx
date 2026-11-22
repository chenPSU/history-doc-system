// One full episode from props built by pipeline/assemble.py (render/edl.json resolved to frames).
import React from 'react';
import {MapScene} from '../maps/MapScene';
import type {MapProps} from '../maps/types';
import {AbsoluteFill, Audio, Freeze, Img, interpolate, OffthreadVideo, Sequence, staticFile, useCurrentFrame} from 'remotion';

export type Motion =
  | {type: 'static' | 'play'}
  | {type: 'zoom'; scale: [number, number]}
  | {type: 'pan'; scale: number; x?: [number, number]; y?: [number, number]};

export type Shot = {
  id: string;
  kind: 'image' | 'video' | 'map' | 'card' | 'placeholder';
  map?: MapProps;
  from: number;
  dur: number;
  fadeIn: number;
  fadeOut: number;
  motion: Motion;
  src?: string;
  bg?: string;
  fit?: 'cover' | 'contain_blur';
  clipFrames?: number;
  holdLast?: boolean;
  card?: {text: string; style: 'chapter' | 'fact' | 'quote' | 'end'; source?: string};
  text?: string;
  reason?: string;
  label?: string;
  focus?: [number, number]; // where the picture is framed and where the camera pushes in (0..1)
  caption?: string;
};

export type EpisodeProps = {
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  audio: string;
  grain: string;
  shots: Shot[];
  words?: {from: number; dur: number; text: string}[]; // Shorts: big captions, a few words at a time
  endNote?: {from: number; text: string};             // Shorts: points to the long video over the music tail
};

const INK = '#efe6d2';
const GOLD = '#c9a45c';
const DARK = '#14110d';
const SERIF = "Georgia, 'Times New Roman', serif";

const transformOf = (m: Motion, t: number, w: number, h: number): string => {
  if (m.type === 'zoom') {
    return `scale(${m.scale[0] + (m.scale[1] - m.scale[0]) * t})`;
  }
  if (m.type === 'pan') {
    const slackX = ((m.scale - 1) / 2) * w;
    const slackY = ((m.scale - 1) / 2) * h;
    const x = m.x ? (m.x[0] + (m.x[1] - m.x[0]) * t) * slackX : 0;
    const y = m.y ? (m.y[0] + (m.y[1] - m.y[0]) * t) * slackY : 0;
    return `translate(${-x}px, ${-y}px) scale(${m.scale})`;
  }
  return 'none';
};

const Still: React.FC<{shot: Shot; w: number; h: number}> = ({shot, w, h}) => {
  const frame = useCurrentFrame();
  const t = shot.dur > 1 ? frame / (shot.dur - 1) : 0;
  const tf = transformOf(shot.motion, Math.min(1, Math.max(0, t)), w, h);
  const [fx, fy] = shot.focus ?? [0.5, 0.5];
  return (
    <AbsoluteFill style={{transform: tf, transformOrigin: `${fx * 100}% ${fy * 100}%`, willChange: 'transform'}}>
      {shot.bg ? <Img src={staticFile(shot.bg)} style={{position: 'absolute', width: '100%', height: '100%', objectFit: 'cover'}} /> : null}
      <Img
        src={staticFile(shot.src!)}
        style={{position: 'absolute', width: '100%', height: '100%', objectFit: shot.fit === 'cover' ? 'cover' : 'contain', objectPosition: `${fx * 100}% ${fy * 100}%`}}
      />
    </AbsoluteFill>
  );
};

const Clip: React.FC<{shot: Shot}> = ({shot}) => {
  const n = shot.clipFrames ?? shot.dur;
  const video = <OffthreadVideo src={staticFile(shot.src!)} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />;
  if (!shot.holdLast || n >= shot.dur) return video;
  return (
    <>
      <Sequence durationInFrames={n}>{video}</Sequence>
      <Sequence from={n}>
        <Freeze frame={n - 1}>{video}</Freeze>
      </Sequence>
    </>
  );
};

const Card: React.FC<{shot: Shot; h: number}> = ({shot, h}) => {
  const frame = useCurrentFrame();
  const c = shot.card!;
  const show = interpolate(frame, [4, 16], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const grow = 1 + 0.03 * Math.min(1, frame / Math.max(1, shot.dur));
  const base: React.CSSProperties = {fontFamily: SERIF, color: INK, textAlign: 'center', opacity: show};
  let body: React.ReactNode;
  if (c.style === 'chapter') {
    const [when, where] = c.text.split(' · ');
    body = (
      <div style={base}>
        <div style={{fontSize: h * 0.034, letterSpacing: h * 0.006, color: GOLD, textTransform: 'uppercase'}}>{when}</div>
        <div style={{width: h * 0.12, height: Math.max(2, h * 0.002), background: GOLD, margin: `${h * 0.022}px auto`}} />
        <div style={{fontSize: h * 0.075, fontStyle: 'italic'}}>{where}</div>
      </div>
    );
  } else if (c.style === 'quote') {
    body = (
      <div style={{...base, maxWidth: '72%'}}>
        <div style={{fontSize: h * 0.058, fontStyle: 'italic', lineHeight: 1.25}}>&ldquo;{c.text}&rdquo;</div>
        {c.source ? <div style={{fontSize: h * 0.026, color: GOLD, marginTop: h * 0.035, letterSpacing: h * 0.002}}>{c.source}</div> : null}
      </div>
    );
  } else if (c.style === 'end') {
    body = <div style={{...base, fontSize: h * 0.05, fontStyle: 'italic'}}>{c.text}</div>;
  } else {
    body = (
      <div style={{...base, fontSize: c.text.length > 24 ? h * 0.06 : h * 0.09, maxWidth: '78%', lineHeight: 1.15}}>
        {c.text}
      </div>
    );
  }
  return (
    <AbsoluteFill style={{background: `radial-gradient(ellipse at center, #2a231a 0%, ${DARK} 75%)`, alignItems: 'center', justifyContent: 'center'}}>
      <div style={{transform: `scale(${grow})`, display: 'flex', justifyContent: 'center', width: '100%'}}>{body}</div>
    </AbsoluteFill>
  );
};

const Placeholder: React.FC<{shot: Shot; h: number}> = ({shot, h}) => (
  <AbsoluteFill style={{background: '#1d2a33', alignItems: 'center', justifyContent: 'center'}}>
    <div style={{border: `${Math.max(2, h * 0.002)}px dashed #6f8797`, padding: h * 0.04, maxWidth: '70%', textAlign: 'center', fontFamily: SERIF, color: '#c8d4dc'}}>
      <div style={{fontSize: h * 0.022, letterSpacing: h * 0.004, color: '#8fa6b5'}}>PLACEHOLDER · {shot.reason}</div>
      <div style={{fontSize: h * 0.045, marginTop: h * 0.02}}>{shot.text}</div>
    </div>
  </AbsoluteFill>
);

// A short story label on the picture (who, when, how many): gold rule + serif text, eases in after the cut.
const Caption: React.FC<{text: string; h: number}> = ({text, h}) => {
  const frame = useCurrentFrame();
  const show = interpolate(frame, [8, 22], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', left: h * 0.06, bottom: h * 0.1, opacity: show, transform: `translateY(${(1 - show) * h * 0.012}px)`}}>
      <div style={{width: h * 0.05, height: Math.max(2, h * 0.0025), background: GOLD, marginBottom: h * 0.012}} />
      <div style={{fontFamily: SERIF, fontSize: h * 0.042, color: INK, textShadow: '0 0 12px rgba(0,0,0,0.95), 0 0 3px rgba(0,0,0,0.9)'}}>{text}</div>
    </div>
  );
};

const Label: React.FC<{text: string; h: number}> = ({text, h}) => (
  <div
    style={{
      // Readable on light engravings too: a dark translucent tab behind the word.
      position: 'absolute', right: h * 0.04, bottom: h * 0.04, fontFamily: SERIF, fontSize: h * 0.024,
      letterSpacing: h * 0.003, color: INK, background: 'rgba(20,17,13,0.62)', padding: `${h * 0.006}px ${h * 0.014}px`,
      borderRadius: h * 0.004,
    }}
  >
    {text}
  </div>
);

const ShotView: React.FC<{shot: Shot; w: number; h: number}> = ({shot, w, h}) => {
  const frame = useCurrentFrame();
  let opacity = 1;
  if (shot.fadeIn > 0) opacity = Math.min(opacity, interpolate(frame, [0, shot.fadeIn], [0, 1], {extrapolateRight: 'clamp'}));
  if (shot.fadeOut > 0) opacity = Math.min(opacity, interpolate(frame, [shot.dur - shot.fadeOut, shot.dur], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  let inner: React.ReactNode;
  if (shot.kind === 'image') inner = <Still shot={shot} w={w} h={h} />;
  else if (shot.kind === 'video') inner = <Clip shot={shot} />;
  else if (shot.kind === 'map') inner = <MapScene {...shot.map!} />;
  else if (shot.kind === 'card') inner = <Card shot={shot} h={h} />;
  else inner = <Placeholder shot={shot} h={h} />;
  return (
    <AbsoluteFill style={{opacity, overflow: 'hidden'}}>
      {inner}
      {shot.caption ? <Caption text={shot.caption} h={h} /> : null}
      {shot.label ? <Label text={shot.label} h={h} /> : null}
    </AbsoluteFill>
  );
};

const Grain: React.FC<{src: string}> = ({src}) => {
  const frame = useCurrentFrame();
  // A fixed noise tile shifted every frame: cheap, and different on every frame like real film grain.
  const x = (frame * 7919) % 512;
  const y = (frame * 104729) % 512;
  return (
    <AbsoluteFill
      style={{
        backgroundImage: `url(${staticFile(src)})`, backgroundPosition: `${x}px ${y}px`,
        opacity: 0.07, mixBlendMode: 'overlay', pointerEvents: 'none',
      }}
    />
  );
};

// Shorts: one big caption at a time, low in the frame, gold underline for the line being spoken.
const Words: React.FC<{words: NonNullable<EpisodeProps['words']>; w: number}> = ({words, w}) => {
  const frame = useCurrentFrame();
  const cur = words.find((x) => frame >= x.from && frame < x.from + x.dur);
  if (!cur) return null;
  const k = frame - cur.from;
  const pop = interpolate(k, [0, 4], [0.92, 1], {extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', left: w * 0.06, right: w * 0.06, top: '66%', textAlign: 'center', transform: `scale(${pop})`}}>
      <span style={{fontFamily: SERIF, fontWeight: 700, fontSize: w * 0.085, lineHeight: 1.12, color: INK,
        textShadow: '0 0 18px rgba(0,0,0,0.95), 0 0 4px rgba(0,0,0,1)', borderBottom: `${Math.max(3, w * 0.006)}px solid ${GOLD}`}}>
        {cur.text}
      </span>
    </div>
  );
};

const EndNote: React.FC<{note: NonNullable<EpisodeProps['endNote']>; w: number; h: number}> = ({note, w, h}) => {
  const frame = useCurrentFrame();
  const k = frame - note.from;
  if (k < 0 || !note.text) return null;
  const show = interpolate(k, [0, 12], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: `rgba(20,17,13,${0.55 * show})`, alignItems: 'center', justifyContent: 'center'}}>
      <div style={{opacity: show, fontFamily: SERIF, color: INK, textAlign: 'center', padding: `0 ${w * 0.1}px`}}>
        <div style={{width: h * 0.05, height: Math.max(3, h * 0.003), background: GOLD, margin: `0 auto ${h * 0.02}px`}} />
        <div style={{fontSize: w * 0.065, lineHeight: 1.2}}>{note.text}</div>
      </div>
    </AbsoluteFill>
  );
};

export const Episode: React.FC<EpisodeProps> = ({shots, audio, grain, width, height, words, endNote}) => (
  <AbsoluteFill style={{background: '#000'}}>
    {shots.map((s) => (
      <Sequence key={s.id} from={s.from} durationInFrames={Math.max(1, s.dur)} layout="none">
        <ShotView shot={s} w={width} h={height} />
      </Sequence>
    ))}
    <Img src={staticFile(grain)} style={{display: 'none'}} />
    <Grain src={grain} />
    {words ? <Words words={words} w={width} /> : null}
    {endNote ? <EndNote note={endNote} w={width} h={height} /> : null}
    <Audio src={staticFile(audio)} />
  </AbsoluteFill>
);
