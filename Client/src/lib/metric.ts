// Métrica de similaridade do plano:
//   bilateral:   s = exp(-((terra - alvo) / sigma)^2)
//   unilateral:  s = exp(-terra / sigma)            (alvo = 0: chuva, NDVI)
//   categórico:  tabela em sigmas.json
// Parâmetros se agrupam em dimensões; a nota final é a média ponderada das dimensões.
// Dimensão sem parâmetro aplicável vira N/A (null) e sai da média, nunca vira zero.
// Dados mínimos: se faltar dado da Terra em mais de sigmas.min_data.max_missing parâmetros que se aplicam
// ao alvo, a célula fica sem nota (total = null). Sem isso, uma célula com só 2 ou 3 parâmetros
// (ex.: plataformas de gelo antárticas) tiraria 100% só porque o resto saiu da média.

import type {
  Cell, Comparison, DimKey, DimResult, EarthGrid, EarthParams, ParamKey, ParamResult, Sigmas, Target,
} from './types.ts';

export const DIM_ORDER: DimKey[] = ['relevo', 'termica', 'superficie', 'agua', 'operacao'];

export const PARAM_ORDER: ParamKey[] = [
  'slope_deg', 'roughness_m', 'temp_range_k', 'temp_min_k',
  'ndvi', 'albedo', 'precip_mm', 'ground_ice', 'illumination',
];

export function paramScore(key: ParamKey, earth: EarthParams, target: Target, cfg: Sigmas): number | null {
  const pc = cfg.params[key];
  const tv = target.params[key];
  if (tv === null || tv === undefined) return null;

  if (key === 'illumination') {
    const row = cfg.illumination_match[String(tv)];
    if (!row) return null;
    const v = row[earth.illumination];
    return typeof v === 'number' ? v : null;
  }
  if (key === 'ground_ice') {
    if (earth.ground_ice === null || earth.ground_ice === undefined) return null; // sem dado = N/A
    return earth.ground_ice === tv ? cfg.ground_ice_match.match : cfg.ground_ice_match.mismatch;
  }

  const ev = earth[key] as number | null;
  if (ev === null || ev === undefined || Number.isNaN(ev)) return null; // sem dado = N/A, nunca zero
  const sigma = pc.sigma || 1;
  if (pc.one_sided) return Math.exp(-Math.max(0, ev) / sigma);
  const d = (ev - (tv as number)) / sigma;
  return Math.exp(-d * d);
}

export function compare(earth: EarthParams, target: Target, cfg: Sigmas): Comparison {
  const dims: DimResult[] = DIM_ORDER.map((id) => ({ id, score: null, params: [] }));
  const byId: Record<string, DimResult> = {};
  dims.forEach((d) => { byId[d.id] = d; });

  for (const key of PARAM_ORDER) {
    const pc = cfg.params[key];
    const res: ParamResult = {
      key,
      dim: pc.dim,
      score: paramScore(key, earth, target, cfg),
      earth: earth[key],
      target: target.params[key],
      unit: pc.unit || '',
    };
    byId[pc.dim].params.push(res);
  }

  const missing = dims
    .flatMap((d) => d.params)
    .filter((p) => p.score === null && p.target !== null && p.target !== undefined)
    .map((p) => p.key);
  const maxMissing = cfg.min_data?.max_missing ?? 1;

  let wsum = 0;
  let acc = 0;
  for (const d of dims) {
    const valid = d.params.filter((p) => p.score !== null);
    if (valid.length === 0) { d.score = null; continue; }
    d.score = valid.reduce((s, p) => s + (p.score as number), 0) / valid.length;
    const w = cfg.weights[d.id] ?? 1;
    wsum += w;
    acc += w * d.score;
  }
  const total = missing.length > maxMissing ? null : wsum > 0 ? acc / wsum : 0;
  return { total, dims, missing };
}

/** Nota total de cada célula de terra para um alvo (mesma ordem de grid.land). NaN = dados insuficientes. */
export function scoreGrid(grid: EarthGrid, target: Target, cfg: Sigmas): Float32Array {
  const out = new Float32Array(grid.land.length);
  for (let i = 0; i < grid.land.length; i++) {
    const t = compare(grid.land[i].p, target, cfg).total;
    out[i] = t === null ? NaN : t;
  }
  return out;
}

export function angularDistDeg(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const r = Math.PI / 180;
  const a =
    Math.sin(lat1 * r) * Math.sin(lat2 * r) +
    Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.cos((lon1 - lon2) * r);
  return Math.acos(Math.max(-1, Math.min(1, a))) / r;
}

export interface Ranked { cell: Cell; score: number; }

/** Melhores células para o alvo, com separação mínima para não listar vizinhas repetidas. */
export function topAnalogs(grid: EarthGrid, scores: Float32Array, n = 8, minSepDeg = 7): Ranked[] {
  const idx = Array.from(scores.keys())
    .filter((i) => !Number.isNaN(scores[i])) // sem nota não entra no ranking
    .sort((a, b) => scores[b] - scores[a]);
  const picked: Ranked[] = [];
  for (const i of idx) {
    const c = grid.land[i];
    if (picked.every((p) => angularDistDeg(p.cell.lat, p.cell.lon, c.lat, c.lon) >= minSepDeg)) {
      picked.push({ cell: c, score: scores[i] });
      if (picked.length >= n) break;
    }
  }
  return picked;
}

export function cellAt(grid: EarthGrid, lat: number, lon: number): Cell | null {
  let l = ((lon + 180) % 360 + 360) % 360;
  const col = Math.min(grid.cols - 1, Math.floor(l / grid.res));
  const row = Math.min(grid.rows - 1, Math.max(0, Math.floor((90 - lat) / grid.res)));
  return grid.cells[row * grid.cols + col];
}
