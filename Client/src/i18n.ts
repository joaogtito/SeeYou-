import type { DimKey, Lang, ParamKey } from './lib/types.ts';

type Dict = Record<string, { pt: string; en: string }>;

export const STR: Dict = {
  search: { pt: 'Pesquise aqui…', en: 'Search here…' },
  topLocations: { pt: 'Top Locais', en: 'Top Locations' },
  targets: { pt: 'Alvos', en: 'Targets' },
  seeAll: { pt: 'Ver todos', en: 'See all' },
  seeLess: { pt: 'Ver menos', en: 'See less' },
  similarTo: { pt: 'Similar a', en: 'Similar to' },
  mars: { pt: 'Marte', en: 'Mars' },
  moon: { pt: 'Lua', en: 'the Moon' },
  moonName: { pt: 'Lua', en: 'Moon' },
  earth: { pt: 'Terra', en: 'Earth' },
  target: { pt: 'Alvo', en: 'Target' },
  bestAnalog: { pt: 'Melhor análogo', en: 'Best analog' },
  why: { pt: 'Por quê?', en: 'Why?' },
  whyNot: { pt: 'Por que não?', en: 'Why not?' },
  whyNotAccent: { pt: 'não', en: 'not' },
  neverOnEarth: { pt: 'O que a Terra nunca reproduz', en: 'What Earth never reproduces' },
  noneWhy: { pt: 'Nenhum parâmetro passa de 50% aqui.', en: 'No parameter scores above 50% here.' },
  noneWhyNot: { pt: 'Nenhum parâmetro abaixo de 50%.', en: 'No parameter scores below 50%.' },
  earthVal: { pt: 'Terra', en: 'Earth' },
  targetVal: { pt: 'Alvo', en: 'Target' },
  na: { pt: 'N/A', en: 'N/A' },
  naHint: { pt: 'não se aplica a este alvo', en: 'does not apply to this target' },
  similarity: { pt: 'similaridade', en: 'similarity' },
  compareWith: { pt: 'Comparar com', en: 'Compare with' },
  curated: { pt: 'Ponto curado', en: 'Curated site' },
  discovery: { pt: 'Descoberta', en: 'Discovery' },
  whyInteresting: { pt: 'Por que é interessante', en: 'Why it is interesting' },
  whereBreaks: { pt: 'Onde a analogia quebra', en: 'Where the analogy breaks' },
  pairedWith: { pt: 'Par', en: 'Paired with' },
  clickHint: { pt: 'Clique em qualquer ponto da Terra para comparar', en: 'Click anywhere on Earth to compare' },
  clickTargetHint: { pt: 'Clique em um alvo para ver seus análogos', en: 'Click a target to see its analogs' },
  ocean: { pt: 'Oceano: sem dados de superfície aqui', en: 'Ocean: no surface data here' },
  viewOnEarth: { pt: 'Ver análogos na Terra', en: 'See analogs on Earth' },
  mock: { pt: 'Dados fictícios (mock)', en: 'Mock data' },
  loadingImagery: { pt: 'Carregando imagens da NASA…', en: 'Loading NASA imagery…' },
  offline: { pt: 'Sem acesso aos tiles da NASA: usando textura de reserva', en: 'NASA tiles unreachable: using fallback texture' },
  layerSat: { pt: 'SAT', en: 'SAT' },
  layerFoliage: { pt: 'FOLHAGEM', en: 'FOLIAGE' },
  layerHeat: { pt: 'CALOR', en: 'HEAT' },
  layerSim: { pt: 'SIMILAR.', en: 'MATCH' },
  tipClear: { pt: 'Limpar|Remove a seleção', en: 'Clear|Remove the selection' },
  tipMarkers: { pt: 'Marcadores|Mostrar/ocultar pontos', en: 'Markers|Show/hide points' },
  tipExplore: { pt: 'Explorar|Vai a um bom análogo', en: 'Explore|Jump to a good analog' },
  tipAbout: { pt: 'Sobre|Método e fontes', en: 'About|Method and sources' },
  tipLang: { pt: 'Idioma|Switch to English', en: 'Language|Mudar para português' },
  tipZoomOut: { pt: 'Zoom|Diminui o zoom', en: 'Zoom|Zoom out' },
  tipZoomIn: { pt: 'Zoom|Aumenta o zoom', en: 'Zoom|Zoom in' },
  tipCenter: { pt: 'Centralizar|Foca no globo', en: 'Center|Reset the view' },
  altitude: { pt: 'km de altitude', en: 'km altitude' },
  aboutTitle: { pt: 'Sobre o SeeYou! Finder', en: 'About SeeYou! Finder' },
  about1: {
    pt: 'Compara qualquer ponto da Terra com 6 alvos na Lua e em Marte. Cada parâmetro recebe uma nota de 0 a 1; os parâmetros se agrupam em dimensões e a nota final é a média ponderada das dimensões.',
    en: 'Compares any point on Earth with 6 targets on the Moon and Mars. Each parameter gets a 0–1 score; parameters are grouped into dimensions and the final score is the weighted mean of the dimensions.',
  },
  about2: {
    pt: 'Bilateral: s = exp(−((terra − alvo) / σ)²). Unilateral (alvo = 0, como chuva e NDVI): s = exp(−terra / σ). Dimensão que não se aplica vira N/A e sai da média.',
    en: 'Two-sided: s = exp(−((earth − target) / σ)²). One-sided (target = 0, e.g. rain and NDVI): s = exp(−earth / σ). A dimension that does not apply becomes N/A and leaves the mean.',
  },
  about3: {
    pt: 'ATENÇÃO: nesta versão os valores da Terra e dos alvos são FICTÍCIOS. A grade da Terra é estimada pela cor do mosaico Blue Marble, pela latitude e por ruído. As tolerâncias σ e os pesos são provisórios.',
    en: 'WARNING: in this version the Earth and target values are MOCK. The Earth grid is estimated from Blue Marble colour, latitude and noise. The σ tolerances and weights are provisional.',
  },
  about4: {
    pt: 'Imagens: NASA GIBS (Terra), NASA Moon Trek e Mars Trek (Lua e Marte). Não existe um padrão oficial de parâmetros para análogos: variáveis vêm de produtos de dados da NASA, pesos e tolerâncias são escolha do time.',
    en: 'Imagery: NASA GIBS (Earth), NASA Moon Trek and Mars Trek (Moon and Mars). There is no official standard of analog parameters: variables come from NASA data products, weights and tolerances are the team\'s choice.',
  },
  close: { pt: 'Fechar', en: 'Close' },
  yes: { pt: 'sim', en: 'yes' },
  no: { pt: 'não', en: 'no' },
};

export const DIM_NAMES: Record<DimKey, { pt: string; en: string }> = {
  relevo: { pt: 'Relevo', en: 'Terrain' },
  termica: { pt: 'Térmica', en: 'Thermal' },
  superficie: { pt: 'Superfície', en: 'Surface' },
  agua: { pt: 'Água / gelo', en: 'Water / ice' },
  operacao: { pt: 'Operação', en: 'Operations' },
};

export const PARAM_NAMES: Record<ParamKey, { pt: string; en: string }> = {
  slope_deg: { pt: 'Declividade média', en: 'Mean slope' },
  roughness_m: { pt: 'Rugosidade', en: 'Roughness' },
  temp_range_k: { pt: 'Amplitude térmica dia–noite', en: 'Day–night thermal range' },
  temp_min_k: { pt: 'Temperatura mínima', en: 'Minimum temperature' },
  precip_mm: { pt: 'Chuva anual (aridez)', en: 'Annual rainfall (aridity)' },
  ground_ice: { pt: 'Gelo no subsolo', en: 'Ground ice' },
  ndvi: { pt: 'Vegetação (NDVI)', en: 'Vegetation (NDVI)' },
  albedo: { pt: 'Albedo', en: 'Albedo' },
  illumination: { pt: 'Regime de iluminação', en: 'Illumination regime' },
};

export const ILLUM_NAMES: Record<string, { pt: string; en: string }> = {
  tropical: { pt: 'tropical', en: 'tropical' },
  mid: { pt: 'latitude média', en: 'mid-latitude' },
  polar: { pt: 'polar', en: 'polar' },
  polar_grazing: { pt: 'sol rasante polar', en: 'polar grazing sun' },
  permanent_shadow: { pt: 'sombra permanente', en: 'permanent shadow' },
  long_day_night: { pt: 'dia e noite de 14 dias', en: '14-day day and night' },
};

export function tr(key: string, lang: Lang): string {
  const e = STR[key];
  return e ? e[lang] : key;
}

/** "Similar a Marte" / "Similar à Lua" / "Similar to Mars" / "Similar to the Moon". */
export function similarPrefix(lang: Lang, body: string): string {
  return lang === 'pt' && body === 'moon' ? 'Similar à' : STR.similarTo[lang];
}

export function fmtCoord(lat: number, lon: number): string {
  const a = `${Math.abs(lat).toFixed(1)}°${lat >= 0 ? 'N' : 'S'}`;
  const b = `${Math.abs(lon).toFixed(1)}°${lon >= 0 ? 'E' : 'W'}`;
  return `${a} ${b}`;
}

export function fmtValue(v: number | string | boolean | null, unit: string, lang: Lang): string {
  if (v === null || v === undefined) return tr('na', lang);
  if (typeof v === 'boolean') return tr(v ? 'yes' : 'no', lang);
  if (typeof v === 'string') return ILLUM_NAMES[v] ? ILLUM_NAMES[v][lang] : v;
  const n = Math.abs(v) >= 100 ? Math.round(v).toString() : (Math.round(v * 100) / 100).toString();
  return unit ? `${n} ${unit}` : n;
}
