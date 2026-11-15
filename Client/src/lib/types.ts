// Formato de dados do Analog Finder (igual ao plano do projeto).
// Tudo o que hoje é mock segue este formato; o pipeline real só precisa gerar os mesmos campos.

export type Body = 'earth' | 'moon' | 'mars';
export type Lang = 'pt' | 'en';
export type Layer = 'sat' | 'foliage' | 'heat' | 'sim';
export type Text2 = { pt: string; en: string };

export type ParamKey =
  | 'slope_deg' | 'roughness_m' | 'temp_range_k' | 'temp_min_k'
  | 'precip_mm' | 'ground_ice' | 'ndvi' | 'albedo' | 'illumination';

export type DimKey = 'relevo' | 'termica' | 'superficie' | 'agua' | 'operacao';

export type EarthIllumination = 'tropical' | 'mid' | 'polar';

export interface EarthParams {
  slope_deg: number;
  roughness_m: number;
  temp_range_k: number;
  temp_min_k: number;
  precip_mm: number;
  ndvi: number;
  albedo: number;
  illumination: EarthIllumination;
  ground_ice: boolean;
}

export interface TargetParams {
  slope_deg: number | null;
  roughness_m: number | null;
  temp_range_k: number | null;
  temp_min_k: number | null;
  precip_mm: number | null;
  ndvi: number | null;
  albedo: number | null;
  illumination: string | null; // null = não se aplica (N/A)
  ground_ice: boolean | null;
}

export interface Target {
  id: string;
  body: 'moon' | 'mars';
  name: Text2;
  short: Text2;
  lat: number;
  lon: number;
  blurb: Text2;
  params: TargetParams;
  never_on_earth: { pt: string[]; en: string[] };
  _mock?: boolean;
}

export interface ParamCfg {
  sigma?: number;
  dim: DimKey;
  unit?: string;
  one_sided?: boolean;
  categorical?: boolean;
}

export interface Sigmas {
  params: Record<ParamKey, ParamCfg>;
  illumination_match: Record<string, Record<EarthIllumination, number>>;
  ground_ice_match: { match: number; mismatch: number };
  weights: Record<DimKey, number>;
}

export interface Cell {
  lat: number; // centro da célula
  lon: number;
  p: EarthParams;
}

export interface EarthGrid {
  res: number;          // resolução em graus
  cols: number;
  rows: number;
  cells: (Cell | null)[]; // null = oceano / sem dado; índice = row * cols + col
  land: Cell[];
  mock: boolean;
  hasLandMask: boolean;
}

export interface ParamResult {
  key: ParamKey;
  dim: DimKey;
  score: number | null; // null = N/A
  earth: number | string | boolean;
  target: number | string | boolean | null;
  unit: string;
}

export interface DimResult {
  id: DimKey;
  score: number | null;
  params: ParamResult[];
}

export interface Comparison {
  total: number;
  dims: DimResult[];
}

export interface Curated {
  id: string;
  name: Text2;
  lat: number;
  lon: number;
  pair: string;
  discovery: boolean;
  why: Text2;
  breaks: Text2;
  _mock?: boolean;
}

export interface Place {
  pt: string;
  en: string;
  lat: number;
  lon: number;
  r: number;
}
