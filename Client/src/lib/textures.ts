// Texturas dos três corpos, montadas no navegador a partir de tiles abertos da NASA:
//   Terra  -> NASA GIBS (WMTS, EPSG:4326)
//   Lua    -> Moon Trek (WMTS equirretangular)
//   Marte  -> Mars Trek (WMTS equirretangular)
// Os tiles são colados em um canvas equirretangular (2:1) que vira a textura do globo.
// Se a rede falhar, cai em uma textura procedural para a demo não ficar em branco.

import type { Body, EarthGrid } from './types.ts';
import type { RgbSampler } from './mockGrid.ts';

export interface TileSource {
  kind: 'trek' | 'gibs';
  url: (z: number, row: number, col: number) => string;
  credit: string;
}

const GIBS = 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best';
const TREK = 'https://trek.nasa.gov/tiles';

export const SOURCES: Record<string, TileSource> = {
  earth_sat: {
    kind: 'gibs',
    url: (z, r, c) => `${GIBS}/BlueMarble_ShadedRelief_Bathymetry/default/500m/${z}/${r}/${c}.jpeg`,
    credit: 'NASA GIBS – Blue Marble',
  },
  earth_foliage: {
    kind: 'gibs',
    url: (z, r, c) => `${GIBS}/MODIS_Terra_NDVI_8Day/default/default/250m/${z}/${r}/${c}.png`,
    credit: 'NASA GIBS – MODIS Terra NDVI (8 dias)',
  },
  earth_heat: {
    kind: 'gibs',
    // Média mensal (MOD11C3): sem os buracos de nuvem e de órbita da imagem diária.
    url: (z, r, c) => `${GIBS}/MODIS_Terra_L3_Land_Surface_Temp_Monthly_Day/default/2022-07-01/2km/${z}/${r}/${c}.png`,
    credit: 'NASA GIBS – MODIS Terra LST (média mensal diurna, jul/2022)',
  },
  moon_sat: {
    kind: 'trek',
    url: (z, r, c) => `${TREK}/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/default/default028mm/${z}/${r}/${c}.jpg`,
    credit: 'NASA Moon Trek – LRO WAC',
  },
  mars_sat: {
    kind: 'trek',
    url: (z, r, c) => `${TREK}/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/${z}/${r}/${c}.jpg`,
    credit: 'NASA Mars Trek – Viking MDIM 2.1',
  },
};

function loadImage(url: string, timeoutMs = 20000): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    const timer = setTimeout(() => { img.src = ''; reject(new Error('timeout')); }, timeoutMs);
    img.onload = () => { clearTimeout(timer); resolve(img); };
    img.onerror = () => { clearTimeout(timer); reject(new Error('tile ' + url)); };
    img.src = url;
  });
}

/** Monta um canvas equirretangular (width x width/2) a partir dos tiles de um nível. */
export async function composeEquirect(
  src: TileSource,
  level: number,
  width: number,
  under?: { canvas: HTMLCanvasElement; alpha: number },
): Promise<HTMLCanvasElement> {
  const height = width / 2;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d')!;
  ctx.fillStyle = '#0a1326';
  ctx.fillRect(0, 0, width, height);
  if (under) {
    ctx.globalAlpha = under.alpha;
    ctx.drawImage(under.canvas, 0, 0, width, height);
    ctx.globalAlpha = 1;
  }

  const span = (src.kind === 'trek' ? 180 : 288) / Math.pow(2, level); // graus por tile
  const cols = Math.ceil(360 / span - 1e-9);
  const rows = Math.ceil(180 / span - 1e-9);
  const ppd = width / 360;
  const size = span * ppd;

  const jobs: Promise<void>[] = [];
  let failed = 0;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      jobs.push(
        loadImage(src.url(level, r, c))
          .then((img) => { ctx.drawImage(img, c * size, r * size, size, size); })
          .catch(() => { failed++; }),
      );
    }
  }
  await Promise.all(jobs);
  if (failed > rows * cols * 0.25) throw new Error(`tiles indisponíveis (${failed}/${rows * cols})`);
  // Garante que o canvas não ficou "tainted" por CORS (lança erro se ficou).
  ctx.getImageData(0, 0, 1, 1);
  return canvas;
}

export function canvasToUrl(canvas: HTMLCanvasElement): Promise<string> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(URL.createObjectURL(blob));
      else reject(new Error('toBlob'));
    }, 'image/jpeg', 0.9);
  });
}

/** Lê a cor do mosaico em (lat, lon). Usado pelo gerador de dados mock. */
export function makeSampler(canvas: HTMLCanvasElement): RgbSampler {
  const w = canvas.width, h = canvas.height;
  const data = canvas.getContext('2d')!.getImageData(0, 0, w, h).data;
  return (lat, lon) => {
    const x = Math.min(w - 1, Math.max(0, Math.floor(((lon + 180) / 360) * w)));
    const y = Math.min(h - 1, Math.max(0, Math.floor(((90 - lat) / 180) * h)));
    const i = (y * w + x) * 4;
    return [data[i], data[i + 1], data[i + 2]];
  };
}

const BASE_COLORS: Record<Body, [string, string]> = {
  earth: ['#123a6b', '#2f6d4f'],
  moon: ['#6f7480', '#a9adb6'],
  mars: ['#7a3b22', '#c8713f'],
};

/** Textura de emergência, sem rede. */
export function proceduralTexture(body: Body): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 512;
  const ctx = canvas.getContext('2d')!;
  const [a, b] = BASE_COLORS[body];
  ctx.fillStyle = a;
  ctx.fillRect(0, 0, 1024, 512);
  let seed = body.length * 9973;
  const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  for (let i = 0; i < 260; i++) {
    const x = rnd() * 1024, y = rnd() * 512, r = 8 + rnd() * 60;
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, b);
    g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.globalAlpha = 0.25 + rnd() * 0.35;
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
  return canvas;
}

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.replace('#', ''), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** Rampa de cor da similaridade: azul escuro -> cor do alvo -> amarelo -> branco. */
export function simColor(score: number, accent: string): [number, number, number] {
  const stops: [number, [number, number, number]][] = [
    [0, [22, 34, 78]],
    [0.4, hexToRgb(accent)],
    [0.7, [253, 223, 132]],
    [1, [255, 255, 255]],
  ];
  const s = Math.max(0, Math.min(1, score));
  for (let i = 1; i < stops.length; i++) {
    if (s <= stops[i][0]) {
      const [t0, c0] = stops[i - 1];
      const [t1, c1] = stops[i];
      const k = (s - t0) / (t1 - t0);
      return [c0[0] + (c1[0] - c0[0]) * k, c0[1] + (c1[1] - c0[1]) * k, c0[2] + (c1[2] - c0[2]) * k];
    }
  }
  return stops[stops.length - 1][1];
}

/** Camada SIMILARIDADE: pinta cada célula da grade com a nota para o alvo ativo. */
export function drawSimilarity(
  base: HTMLCanvasElement,
  grid: EarthGrid,
  scores: Float32Array,
  accent: string,
): HTMLCanvasElement {
  const width = 2048, height = 1024;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d')!;
  ctx.fillStyle = '#060b18';
  ctx.fillRect(0, 0, width, height);
  ctx.globalAlpha = 0.4;
  ctx.drawImage(base, 0, 0, width, height);

  // Estica as notas entre o mínimo e o máximo para o mapa ter contraste.
  let min = 1, max = 0;
  for (let i = 0; i < scores.length; i++) {
    if (Number.isNaN(scores[i])) continue;
    if (scores[i] < min) min = scores[i];
    if (scores[i] > max) max = scores[i];
  }
  const range = Math.max(1e-6, max - min);
  const ppd = width / 360;
  const size = grid.res * ppd;
  for (let i = 0; i < grid.land.length; i++) {
    const c = grid.land[i];
    if (Number.isNaN(scores[i])) {
      // dados insuficientes: cinza discreto, fora da escala de cor
      ctx.globalAlpha = 0.18;
      ctx.fillStyle = 'rgb(140,140,150)';
      ctx.fillRect((c.lon - grid.res / 2 + 180) * ppd, (90 - c.lat - grid.res / 2) * ppd, size + 0.6, size + 0.6);
      continue;
    }
    const s = (scores[i] - min) / range;
    const [r, g, b] = simColor(s, accent);
    ctx.globalAlpha = 0.25 + 0.7 * s;
    ctx.fillStyle = `rgb(${r | 0},${g | 0},${b | 0})`;
    ctx.fillRect((c.lon - grid.res / 2 + 180) * ppd, (90 - c.lat - grid.res / 2) * ppd, size + 0.6, size + 0.6);
  }
  ctx.globalAlpha = 1;
  return canvas;
}
