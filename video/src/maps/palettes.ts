// Map colour sets. Rotate the base palette between consecutive videos (policy gate: vary map colours),
// but keep the side colours fixed across the channel (style guide: one side deep red, the other blue-grey).
export type Palette = {
  land: string;
  landEdge: string;
  water: string;
  waterDeep: string;
  ink: string;
  labelLand: string;
  labelWater: string;
  paperGrain: number; // 0..1 opacity of the paper texture on land
};

export const SIDES = {
  byz: '#3d5a78', // blue-grey: the defenders / the side being attacked
  ott: '#8e1b1b', // deep red: the attackers / the expanding power
  neutral: '#6b5a3e',
};

export const PALETTES: Record<string, Palette> = {
  parchment: {
    land: '#d9c59b', landEdge: '#8a7550', water: '#2d3f4d', waterDeep: '#1d2a34',
    ink: '#2a2118', labelLand: '#3b2d1f', labelWater: '#c8d5dc', paperGrain: 0.22,
  },
  slate: {
    land: '#cfc8b6', landEdge: '#7d7663', water: '#26323b', waterDeep: '#161e24',
    ink: '#1f1d1a', labelLand: '#2e2a24', labelWater: '#b9c6cc', paperGrain: 0.15,
  },
  sepia: {
    land: '#e4d3ad', landEdge: '#9b7f52', water: '#8d9c97', waterDeep: '#6d7d79',
    ink: '#2b2015', labelLand: '#3d2c18', labelWater: '#f1ead9', paperGrain: 0.28,
  },
};

export const palette = (name: string): Palette => PALETTES[name] ?? PALETTES.parchment;
