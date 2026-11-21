import React from 'react';
import {Composition} from 'remotion';
import {MapScene} from './maps/MapScene';
import type {MapProps} from './maps/types';

// A tiny stand-in so the studio opens without props; real renders pass --props=<file> from tools/map.py.
const demo: MapProps = {
  width: 1920,
  height: 1080,
  fps: 30,
  durationSec: 4,
  palette: 'parchment',
  view: [28.88, 40.97, 29.04, 41.06],
  land: {type: 'FeatureCollection', features: []},
  layers: [{type: 'label', text: 'Run tools/map.py to render a real map', at: [28.96, 41.015], kind: 'place'}],
};

export const Root: React.FC = () => (
  <Composition
    id="MapScene"
    component={MapScene as unknown as React.FC<Record<string, unknown>>}
    durationInFrames={120}
    fps={30}
    width={1920}
    height={1080}
    defaultProps={demo as unknown as Record<string, unknown>}
    calculateMetadata={({props}) => {
      const p = props as unknown as MapProps;
      return {durationInFrames: Math.max(1, Math.round(p.durationSec * p.fps)), fps: p.fps, width: p.width, height: p.height};
    }}
  />
);
