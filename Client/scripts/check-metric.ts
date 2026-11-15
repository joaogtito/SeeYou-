// Checagem rápida da métrica, sem navegador:  node scripts/check-metric.ts   (Node 22.18+ ou 24)
import { readFileSync } from 'node:fs';
import { compare, scoreGrid, topAnalogs, cellAt } from '../src/lib/metric.ts';
import { generateMockGrid } from '../src/lib/mockGrid.ts';

const load = (f: string) => JSON.parse(readFileSync(new URL('../src/data/' + f, import.meta.url), 'utf8'));
const targets = load('targets.json');
const sigmas = load('sigmas.json');

let fails = 0;
const ok = (name: string, cond: boolean) => { if (!cond) fails++; console.log((cond ? 'ok   ' : 'FALHA') + ' ' + name); };

const jezero = targets.find((t: any) => t.id === 'mars_jezero');
const ridge = targets.find((t: any) => t.id === 'moon_shackleton_ridge');

// 1. Uma "Terra" idêntica ao alvo dá 100% nos parâmetros numéricos.
const twin: any = { ...jezero.params, illumination: 'mid' };
const c1 = compare(twin, jezero, sigmas);
ok('gêmeo de Jezero = 100%', Math.abs(c1.total - 1) < 1e-9);
ok('operação é N/A para Marte', c1.dims.find((d: any) => d.id === 'operacao')!.score === null);

// 2. Fórmulas do plano.
const e: any = { ...twin, slope_deg: 9 }; // alvo 4, sigma 5 -> exp(-1)
const c2 = compare(e, jezero, sigmas);
const slope = c2.dims[0].params.find((p: any) => p.key === 'slope_deg')!.score!;
ok('bilateral exp(-((9-4)/5)^2) = e^-1', Math.abs(slope - Math.exp(-1)) < 1e-9);
const e3: any = { ...twin, precip_mm: 50 }; // sigma 50 -> exp(-1)
const pr = compare(e3, jezero, sigmas).dims.find((d: any) => d.id === 'agua')!.params.find((p: any) => p.key === 'precip_mm')!.score!;
ok('unilateral exp(-50/50) = e^-1', Math.abs(pr - Math.exp(-1)) < 1e-9);

// 3. Floresta tropical tem nota baixa para a Lua.
const forest: any = { slope_deg: 3, roughness_m: 40, temp_range_k: 10, temp_min_k: 293, precip_mm: 2200, ndvi: 0.8, albedo: 0.13, illumination: 'tropical', ground_ice: false };
const c3 = compare(forest, ridge, sigmas);
ok('floresta x Shackleton < 20%', c3.total < 0.2);
ok('térmica quebra para a Lua', c3.dims.find((d: any) => d.id === 'termica')!.score! < 0.05);

// 4. Grade mock e ranking.
const grid = generateMockGrid(null, 2);
ok('grade mock tem células', grid.land.length > 1000);
for (const t of targets) {
  const s = scoreGrid(grid, t, sigmas);
  const top = topAnalogs(grid, s, 5);
  const allValid = Array.from(s).every((v) => v >= 0 && v <= 1 && !Number.isNaN(v));
  ok(`notas válidas para ${t.id}`, allValid && top.length === 5 && top[0].score >= top[4].score);
  console.log('      top: ' + top.map((r) => `${r.cell.lat.toFixed(0)},${r.cell.lon.toFixed(0)}=${(r.score * 100).toFixed(0)}%`).join('  '));
}
ok('cellAt encontra a célula', cellAt(grid, -16.78, -52.98) !== null);

console.log(fails === 0 ? '\nTudo certo.' : `\n${fails} falha(s).`);
process.exit(fails === 0 ? 0 : 1);
