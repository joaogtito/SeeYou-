// GRADE MOCKADA DA TERRA — NÃO É DADO REAL.
// Gera valores plausíveis a partir de: (1) latitude, (2) ruído determinístico e,
// quando disponível, (3) a cor do mosaico Blue Marble (verde = vegetação, bege = árido, branco = gelo).
// Serve só para a interface e a métrica funcionarem antes do pipeline.
// Para usar dados reais: coloque public/data/earth_grid.json (formato no README) e este gerador é ignorado.

import type { Cell, EarthGrid, EarthIllumination, EarthParams } from './types.ts';

export type RgbSampler = (lat: number, lon: number) => [number, number, number] | null;

function hash(x: number, y: number, seed: number): number {
  let h = (x * 374761393 + y * 668265263 + seed * 2147483647) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  h = h ^ (h >>> 16);
  return (h >>> 0) / 4294967295;
}

function smooth(t: number): number { return t * t * (3 - 2 * t); }

function valueNoise(x: number, y: number, seed: number): number {
  const xi = Math.floor(x), yi = Math.floor(y);
  const xf = smooth(x - xi), yf = smooth(y - yi);
  const a = hash(xi, yi, seed), b = hash(xi + 1, yi, seed);
  const c = hash(xi, yi + 1, seed), d = hash(xi + 1, yi + 1, seed);
  return a + (b - a) * xf + (c - a) * yf + (a - b - c + d) * xf * yf;
}

function fbm(x: number, y: number, seed: number): number {
  return 0.55 * valueNoise(x, y, seed) + 0.3 * valueNoise(x * 2.1, y * 2.1, seed + 7) + 0.15 * valueNoise(x * 4.3, y * 4.3, seed + 19);
}

const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
const round = (v: number, d: number) => { const k = Math.pow(10, d); return Math.round(v * k) / k; };

export function illuminationOf(lat: number): EarthIllumination {
  const a = Math.abs(lat);
  return a >= 66.5 ? 'polar' : a >= 23.5 ? 'mid' : 'tropical';
}

function mockParams(lat: number, lon: number, rgb: [number, number, number] | null): EarthParams | null {
  const alat = Math.abs(lat);
  let ndvi: number;
  let albedo: number;
  let ice = false;

  if (rgb) {
    const [r, g, b] = rgb;
    const bright = (r + g + b) / 3;
    const sat = Math.max(r, g, b) - Math.min(r, g, b);
    ice = bright > 185 && sat < 40;
    const ocean = !ice && b > r * 1.25 && b > g * 1.02;
    if (ocean) return null;
    const v = (g - r) / (g + r + 1);
    ndvi = ice ? 0.02 : clamp(0.15 + v * 3, 0.02, 0.9);
    albedo = ice ? 0.8 : clamp((bright / 255) * 0.6, 0.05, 0.6);
  } else {
    // Sem textura: cinturões desérticos perto de 15–32° e gelo acima de 72°.
    ice = alat > 72;
    const belt = Math.exp(-Math.pow((alat - 24) / 9, 2));
    const n = fbm(lon / 14, lat / 14, 3);
    ndvi = ice ? 0.02 : clamp(0.75 - belt * 0.8 * (0.5 + n) - (alat > 55 ? (alat - 55) / 40 : 0), 0.02, 0.9);
    albedo = ice ? 0.8 : clamp(0.14 + (0.6 - ndvi) * 0.35, 0.08, 0.5);
  }

  const arid = clamp(1 - ndvi / 0.6, 0, 1);
  const n1 = fbm(lon / 9, lat / 9, 11);
  const n2 = fbm(lon / 5, lat / 5, 29);

  const precip = ice
    ? 60 + n1 * 120
    : 15 + Math.pow(1 - arid, 1.5) * 2200 + n1 * 60 * (1 - arid);

  const sinLat = Math.sin((alat * Math.PI) / 180);
  let tMean = 300 - 50 * sinLat * sinLat - n2 * 6;
  if (ice && lat < -60) tMean -= 25;
  if (ice && lat > 60) tMean -= 10;

  const tRange = ice ? 6 + n1 * 6 : 8 + 22 * arid + n1 * 6;
  const tMin = tMean - tRange / 2 - 4;

  const rough = Math.pow(n2, 2.2);
  const slope = 0.5 + 18 * rough;
  const roughness = 10 + 380 * Math.pow(n2, 2);

  return {
    slope_deg: round(slope, 1),
    roughness_m: Math.round(roughness),
    temp_range_k: round(tRange, 1),
    temp_min_k: round(tMin, 1),
    precip_mm: Math.round(precip),
    ndvi: round(ndvi, 2),
    albedo: round(albedo, 2),
    illumination: illuminationOf(lat),
    ground_ice: ice || lat > 62 || lat < -60,
  };
}

export function generateMockGrid(sampler: RgbSampler | null, res = 1): EarthGrid {
  const cols = Math.round(360 / res);
  const rows = Math.round(180 / res);
  const cells: (Cell | null)[] = new Array(cols * rows).fill(null);
  const land: Cell[] = [];
  for (let row = 0; row < rows; row++) {
    const lat = 90 - (row + 0.5) * res;
    for (let col = 0; col < cols; col++) {
      const lon = -180 + (col + 0.5) * res;
      const rgb = sampler ? sampler(lat, lon) : null;
      if (sampler && !rgb) continue;
      const p = mockParams(lat, lon, rgb);
      if (!p) continue;
      const cell: Cell = { lat, lon, p };
      cells[row * cols + col] = cell;
      land.push(cell);
    }
  }
  return { res, cols, rows, cells, land, mock: true, hasLandMask: !!sampler };
}

/** Converte o arquivo real do pipeline (ver README) para o formato interno. */
export function gridFromFile(raw: any): EarthGrid {
  const res: number = raw.res_deg;
  const cols = Math.round(360 / res);
  const rows = Math.round(180 / res);
  const f: string[] = raw.fields;
  const cells: (Cell | null)[] = new Array(cols * rows).fill(null);
  const land: Cell[] = [];
  for (const rowArr of raw.cells as number[][]) {
    const lat = rowArr[0];
    const lon = rowArr[1];
    const o: any = {};
    f.forEach((name, i) => { o[name] = rowArr[i + 2]; });
    // null (ou campo ausente) = sem dado; a métrica trata como N/A.
    const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);
    const p: EarthParams = {
      slope_deg: num(o.slope_deg), roughness_m: num(o.roughness_m),
      temp_range_k: num(o.temp_range_k), temp_min_k: num(o.temp_min_k),
      precip_mm: num(o.precip_mm), ndvi: num(o.ndvi), albedo: num(o.albedo),
      illumination: illuminationOf(lat),
      ground_ice: o.ground_ice === null || o.ground_ice === undefined ? null : !!o.ground_ice,
    };
    const cell: Cell = { lat, lon, p };
    const col = Math.min(cols - 1, Math.floor((lon + 180) / res));
    const row = Math.min(rows - 1, Math.max(0, Math.floor((90 - lat) / res)));
    cells[row * cols + col] = cell;
    land.push(cell);
  }
  return { res, cols, rows, cells, land, mock: !!raw._mock, hasLandMask: true };
}
