import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import GlobeView from './components/GlobeView.tsx';
import type { GlobeHandle, Marker, Pov } from './components/GlobeView.tsx';
import {
  AboutModal, BottomBar, LayerSwitch, LocationMenu, SearchBox, SelectedCard, TargetDetail, TargetSelect,
  TopLeft, ViewSwitch, WhyPanel, bodyThumb, earthThumb,
} from './components/Panels.tsx';
import type { MenuItem, SearchItem } from './components/Panels.tsx';
import type { Body, Cell, Curated, DataMetadata, EarthGrid, Lang, Layer, Place, Sigmas, Target } from './lib/types.ts';
import { angularDistDeg, cellAt, compare, scoreGrid, topAnalogs } from './lib/metric.ts';
import type { Ranked } from './lib/metric.ts';
import { generateMockGrid, gridFromFile } from './lib/mockGrid.ts';
import { SOURCES, composeEquirect, drawSimilarity, makeSampler, proceduralTexture } from './lib/textures.ts';
import { fmtCoord, similarPrefix, tr } from './i18n.ts';
import targetsJson from './data/targets.json';
import sigmasJson from './data/sigmas.json';
import curatedJson from './data/curated.json';
import gazetteerJson from './data/gazetteer.json';

const TARGETS = targetsJson as unknown as Target[];
const SIGMAS = sigmasJson as unknown as Sigmas;
const CURATED = curatedJson as unknown as Curated[];
const PLACES = gazetteerJson as unknown as Place[];

const RADIUS_KM: Record<Body, number> = { earth: 6371, moon: 1737.4, mars: 3389.5 };
const ACCENT: Record<Body, string> = { earth: '#3c8cea', mars: '#d6753d', moon: '#9ea7b3' };
const HOME: Pov = { lat: -12, lng: -52, altitude: 2.3 };

const norm = (s: string) => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');

function placeName(lat: number, lon: number, lang: Lang): { name: string; known: boolean } {
  const c = CURATED.find((x) => angularDistDeg(lat, lon, x.lat, x.lon) < 1.2);
  if (c) return { name: c.name[lang], known: true };
  let best: Place | null = null;
  let bestK = 1;
  for (const p of PLACES) {
    const k = angularDistDeg(lat, lon, p.lat, p.lon) / p.r;
    if (k < bestK) { bestK = k; best = p; }
  }
  return best ? { name: best[lang], known: true } : { name: fmtCoord(lat, lon), known: false };
}

function niceScale(kmPerPx: number): { km: number; px: number } {
  const want = kmPerPx * 110;
  const pow = Math.pow(10, Math.floor(Math.log10(Math.max(want, 1e-6))));
  const n = want / pow;
  const km = (n >= 5 ? 5 : n >= 2 ? 2 : 1) * pow;
  return { km, px: Math.max(20, Math.min(160, km / kmPerPx)) };
}

export default function App() {
  const [lang, setLang] = useState<Lang>('pt');
  const [body, setBody] = useState<Body>('earth');
  const [layer, setLayer] = useState<Layer>('sat');
  const [targetId, setTargetId] = useState<string>('mars_jezero');
  const [grid, setGrid] = useState<EarthGrid | null>(null);
  const [meta, setMeta] = useState<DataMetadata | null>(null);
  const [sel, setSel] = useState<{ lat: number; lon: number; cell: Cell } | null>(null);
  const [pov, setPov] = useState<Pov>(HOME);
  const [tex, setTex] = useState<HTMLCanvasElement | null>(null);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [markersOn, setMarkersOn] = useState(true);
  const [about, setAbout] = useState(false);

  const globe = useRef<GlobeHandle>(null);
  const basePromise = useRef<Partial<Record<Body, Promise<HTMLCanvasElement>>>>({});
  const realTexture = useRef<Partial<Record<Body, boolean>>>({});
  const upgraded = useRef<Partial<Record<Body, boolean>>>({});
  const texCache = useRef<Map<string, HTMLCanvasElement>>(new Map());
  const placeholders = useRef<Partial<Record<Body, HTMLCanvasElement>>>({});
  const currentKey = useRef('');
  const shownBody = useRef<Body | null>(null);
  const toastTimer = useRef(0);

  const target = TARGETS.find((t) => t.id === targetId) || TARGETS[0];

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 2600);
  }, []);

  /* ---------- texturas ---------- */

  const getBase = useCallback((b: Body): Promise<HTMLCanvasElement> => {
    if (!basePromise.current[b]) {
      basePromise.current[b] = composeEquirect(SOURCES[`${b}_sat`], 2, 2048)
        .then((c) => { realTexture.current[b] = true; return c; })
        .catch(() => { realTexture.current[b] = false; setOffline(true); return proceduralTexture(b); });
    }
    return basePromise.current[b] as Promise<HTMLCanvasElement>;
  }, []);

  /* ---------- grade da Terra: arquivo real se existir, senão mock ---------- */

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(import.meta.env.BASE_URL + 'data/earth_grid.json');
        if (r.ok) {
          const raw = await r.json();
          if (raw && Array.isArray(raw.cells) && raw.cells.length > 0) {
            if (!cancelled) setGrid(gridFromFile(raw));
            return;
          }
        }
      } catch { /* sem arquivo real: usa o mock */ }
      const base = await getBase('earth');
      const sampler = realTexture.current.earth ? makeSampler(base) : null;
      if (!cancelled) setGrid(generateMockGrid(sampler, 1));
    })();
    return () => { cancelled = true; };
  }, [getBase]);

  /* ---------- metadata.json do pipeline (créditos de cada campo) ---------- */

  useEffect(() => {
    let cancelled = false;
    fetch(import.meta.env.BASE_URL + 'data/metadata.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((m) => { if (!cancelled && m && m.fields) setMeta(m as DataMetadata); })
      .catch(() => { /* sem metadata: o modal mostra só os créditos das imagens */ });
    return () => { cancelled = true; };
  }, []);

  const scores = useMemo(() => (grid ? scoreGrid(grid, target, SIGMAS) : null), [grid, targetId]);
  const top: Ranked[] = useMemo(() => (grid && scores ? topAnalogs(grid, scores, 8) : []), [grid, scores]);
  const bestByTarget = useMemo(() => {
    const out: Record<string, Ranked> = {};
    if (!grid) return out;
    for (const t of TARGETS) {
      const b = topAnalogs(grid, scoreGrid(grid, t, SIGMAS), 1)[0];
      if (b) out[t.id] = b;
    }
    return out;
  }, [grid]);

  const texKey =
    body !== 'earth' ? `${body}:sat` : layer === 'sim' ? `earth:sim:${targetId}:${grid ? 1 : 0}` : `earth:${layer}`;
  currentKey.current = texKey;

  useEffect(() => {
    let cancelled = false;
    const cached = texCache.current.get(texKey);
    if (cached) { shownBody.current = body; setTex(cached); setLoading(false); return; }
    setLoading(true);
    // Ao trocar de corpo, mostra na hora uma textura provisória do corpo novo
    // (nunca a do corpo anterior, nunca um globo vazio) enquanto os tiles carregam.
    if (shownBody.current !== body) {
      if (!placeholders.current[body]) placeholders.current[body] = proceduralTexture(body);
      shownBody.current = body;
      setTex(placeholders.current[body] as HTMLCanvasElement);
    }
    (async () => {
      const base = await getBase(body);
      let canvas = base;
      let cacheable = true;
      if (body === 'earth' && (layer === 'foliage' || layer === 'heat')) {
        try {
          canvas = await composeEquirect(SOURCES[`earth_${layer}`], 2, 2048, { canvas: base, alpha: 0.3 });
        } catch {
          cacheable = false;
        }
      } else if (body === 'earth' && layer === 'sim') {
        if (grid && scores) canvas = drawSimilarity(base, grid, scores, ACCENT[target.body]);
        else cacheable = false;
      }
      if (cacheable) texCache.current.set(texKey, canvas);
      if (!cancelled) { shownBody.current = body; setTex(canvas); setLoading(false); }

      // Depois da primeira imagem, busca uma versão com o dobro da resolução em segundo plano.
      const satKey = body === 'earth' ? 'earth:sat' : `${body}:sat`;
      if (texKey === satKey && realTexture.current[body] && !upgraded.current[body]) {
        upgraded.current[body] = true;
        composeEquirect(SOURCES[`${body}_sat`], 3, 4096)
          .then((hi) => {
            texCache.current.set(satKey, hi);
            if (currentKey.current === satKey) setTex(hi);
          })
          .catch(() => { /* fica com a resolução menor */ });
      }
    })().catch(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [texKey]);

  /* ---------- seleção ---------- */

  const selectPoint = useCallback((lat: number, lon: number, fly = true) => {
    if (!grid) return;
    const cell = cellAt(grid, lat, lon);
    if (!cell) { showToast(tr('ocean', lang)); return; }
    setSel({ lat: cell.lat, lon: cell.lon, cell });
    if (fly && globe.current) globe.current.flyTo(cell.lat, cell.lon, 0.9);
  }, [grid, lang, showToast]);

  const goTarget = useCallback((id: string) => {
    const t = TARGETS.find((x) => x.id === id);
    if (!t) return;
    setTargetId(id);
    setBody(t.body);
    if (globe.current) globe.current.flyTo(t.lat, t.lon, 1.3);
  }, []);

  const goCurated = useCallback((id: string) => {
    const c = CURATED.find((x) => x.id === id);
    if (!c) return;
    setBody('earth');
    setTargetId(c.pair);
    selectPoint(c.lat, c.lon);
  }, [selectPoint]);

  const onGlobeClick = (lat: number, lon: number) => {
    if (body === 'earth') { selectPoint(lat, lon, false); return; }
    const near = TARGETS.filter((t) => t.body === body)
      .map((t) => ({ t, d: angularDistDeg(lat, lon, t.lat, t.lon) }))
      .sort((a, b) => a.d - b.d)[0];
    if (near && near.d < 12) goTarget(near.t.id);
    else showToast(tr('clickTargetHint', lang));
  };

  const onMarker = (id: string) => {
    if (body === 'earth') goCurated(id);
    else goTarget(id);
  };

  const changeBody = (b: Body) => {
    setBody(b);
    if (b === 'earth') {
      if (globe.current) globe.current.flyTo(sel ? sel.lat : HOME.lat, sel ? sel.lon : HOME.lng, sel ? 0.9 : HOME.altitude);
      return;
    }
    const t = target.body === b ? target : TARGETS.find((x) => x.body === b);
    if (t) {
      setTargetId(t.id);
      if (globe.current) globe.current.flyTo(t.lat, t.lon, 2.0);
    }
  };

  const viewOnEarth = () => {
    setBody('earth');
    setLayer('sim');
    const b = bestByTarget[target.id];
    if (b) selectPoint(b.cell.lat, b.cell.lon);
  };

  const explore = () => {
    if (body === 'earth') {
      if (top.length === 0) return;
      const i = sel ? (top.findIndex((r) => r.cell === sel.cell) + 1) % top.length : 0;
      selectPoint(top[i].cell.lat, top[i].cell.lon);
    } else {
      const list = TARGETS.filter((t) => t.body === body);
      const i = (list.findIndex((t) => t.id === targetId) + 1) % list.length;
      goTarget(list[i].id);
    }
  };

  /* ---------- dados para os painéis ---------- */

  const cmp = useMemo(() => (sel ? compare(sel.cell.p, target, SIGMAS) : null), [sel, targetId]);
  const selScores = useMemo(() => {
    const o: Record<string, number | null> = {};
    if (sel) for (const t of TARGETS) o[t.id] = compare(sel.cell.p, t, SIGMAS).total;
    return o;
  }, [sel]);
  const selCurated = sel ? CURATED.find((c) => angularDistDeg(sel.lat, sel.lon, c.lat, c.lon) < 1.2) || null : null;

  const refLat = sel ? sel.lat : pov.lat;
  const refLon = sel ? sel.lon : pov.lng;
  const bodyWord = (b: string) => (b === 'mars' ? tr('mars', lang) : tr('moon', lang));

  const menuItems: MenuItem[] = useMemo(() => {
    if (body === 'earth') {
      return top.map((r, i) => {
        const pn = placeName(r.cell.lat, r.cell.lon, lang);
        const km = Math.round((angularDistDeg(refLat, refLon, r.cell.lat, r.cell.lon) * Math.PI / 180) * RADIUS_KM.earth);
        return {
          key: String(i),
          name: pn.known ? `${pn.name} · ${fmtCoord(r.cell.lat, r.cell.lon)}` : pn.name,
          subPrefix: similarPrefix(lang, target.body),
          subAccent: bodyWord(target.body),
          accent: target.body,
          score: r.score,
          right: `${km.toLocaleString(lang === 'pt' ? 'pt-BR' : 'en-US')} km`,
          thumb: earthThumb(r.cell.p),
          active: !!sel && sel.cell === r.cell,
        };
      });
    }
    return TARGETS.filter((t) => t.body === body).map((t) => {
      const b = bestByTarget[t.id];
      return {
        key: t.id,
        name: t.name[lang],
        subPrefix: `${tr('bestAnalog', lang)}:`,
        subAccent: b ? placeName(b.cell.lat, b.cell.lon, lang).name : '…',
        accent: 'earth' as const,
        score: b ? b.score : 0,
        right: '',
        thumb: bodyThumb(t.body),
        active: t.id === targetId,
      };
    });
  }, [body, top, lang, targetId, sel, bestByTarget, Math.round(refLat), Math.round(refLon)]);

  const onMenuPick = (key: string) => {
    if (body === 'earth') {
      const r = top[Number(key)];
      if (r) selectPoint(r.cell.lat, r.cell.lon);
    } else {
      goTarget(key);
    }
  };

  const markers: Marker[] = useMemo(() => {
    if (!markersOn) return [];
    if (body === 'earth') {
      return CURATED.map((c) => ({
        id: c.id, lat: c.lat, lon: c.lon,
        label: c.name[lang].split(' (')[0].split(' – ')[0],
        kind: c.discovery ? 'discovery' as const : 'curated' as const,
      }));
    }
    return TARGETS.filter((t) => t.body === body).map((t) => ({
      id: t.id, lat: t.lat, lon: t.lon, label: t.short[lang], kind: 'target' as const, active: t.id === targetId,
    }));
  }, [body, lang, markersOn, targetId]);

  const find = useCallback((q: string): SearchItem[] => {
    const n = norm(q);
    const out: SearchItem[] = [];
    for (const t of TARGETS) {
      if (norm(t.name.pt + ' ' + t.name.en).includes(n)) out.push({ key: `t:${t.id}`, label: t.name[lang], sub: t.body === 'mars' ? tr('mars', lang) : tr('moonName', lang) });
    }
    for (const c of CURATED) {
      if (norm(c.name.pt + ' ' + c.name.en).includes(n)) out.push({ key: `c:${c.id}`, label: c.name[lang], sub: tr('curated', lang) });
    }
    PLACES.forEach((p, i) => {
      if (norm(p.pt + ' ' + p.en).includes(n)) out.push({ key: `p:${i}`, label: p[lang], sub: tr('earth', lang) });
    });
    return out.slice(0, 8);
  }, [lang]);

  const onSearchPick = (key: string) => {
    const [kind, id] = [key.slice(0, 1), key.slice(2)];
    if (kind === 't') goTarget(id);
    else if (kind === 'c') goCurated(id);
    else {
      const p = PLACES[Number(id)];
      if (p) { setBody('earth'); selectPoint(p.lat, p.lon); }
    }
  };

  const kmPerPx = (2 * Math.tan((25 * Math.PI) / 180) * pov.altitude * RADIUS_KM[body]) / Math.max(1, window.innerHeight);
  const credits = [SOURCES[`${body}_sat`].credit, ...(body === 'earth' ? [SOURCES.earth_foliage.credit, SOURCES.earth_heat.credit] : [])];
  const selName = sel ? placeName(sel.lat, sel.lon, lang).name : '';
  const bestForTarget = bestByTarget[target.id];

  return (
    <div className="app" data-theme={body}>
      <div className="stars" />
      <div className="globe-layer">
        <GlobeView
          ref={globe}
          body={body}
          texture={tex}
          markers={markers}
          selection={body === 'earth' && sel && grid ? { lat: sel.lat, lon: sel.lon, res: grid.res } : null}
          onClick={onGlobeClick}
          onMarker={onMarker}
          onPov={setPov}
        />
      </div>

      <div className="ui">
        <TopLeft>
          <ViewSwitch body={body} onChange={changeBody} lang={lang} />
          {body === 'earth' && <LayerSwitch layer={layer} onChange={setLayer} lang={lang} />}
        </TopLeft>

        <div className="top-center">
          <SearchBox lang={lang} find={find} onPick={onSearchPick} />
          <TargetSelect targets={TARGETS} value={targetId} lang={lang} onChange={(id) => (body === 'earth' ? setTargetId(id) : goTarget(id))} />
        </div>

        <aside className="left-col">
          {body === 'earth' && sel && cmp && (
            <>
              <SelectedCard
                name={selName}
                lat={sel.lat}
                lon={sel.lon}
                total={cmp.total}
                target={target}
                targets={TARGETS}
                scores={selScores}
                curated={selCurated}
                lang={lang}
                onTarget={setTargetId}
                onClose={() => setSel(null)}
              />
              <WhyPanel mode="whynot" cmp={cmp} target={target} lang={lang} />
            </>
          )}
        </aside>

        <aside className="right-col">
          <LocationMenu
            title={tr(body === 'earth' ? 'topLocations' : 'targets', lang)}
            icon={body === 'earth' ? 'trophy' : 'target'}
            items={menuItems}
            lang={lang}
            onPick={onMenuPick}
            collapsible={body === 'earth'}
          />
          {body === 'earth' && sel && cmp && <WhyPanel mode="why" cmp={cmp} target={target} lang={lang} />}
          {body !== 'earth' && (
            <TargetDetail
              target={target}
              lang={lang}
              best={bestForTarget ? { name: placeName(bestForTarget.cell.lat, bestForTarget.cell.lon, lang).name, score: bestForTarget.score } : null}
              onViewEarth={viewOnEarth}
            />
          )}
        </aside>

        {body === 'earth' && !sel && <div className="panel hint-pill">{tr('clickHint', lang)}</div>}

        <BottomBar
          lang={lang}
          body={body}
          altitudeKm={pov.altitude * RADIUS_KM[body]}
          centerLat={pov.lat}
          centerLon={pov.lng}
          scale={niceScale(kmPerPx)}
          markersOn={markersOn}
          isMock={!grid || grid.mock}
          onClear={() => setSel(null)}
          onMarkers={() => setMarkersOn(!markersOn)}
          onExplore={explore}
          onAbout={() => setAbout(true)}
          onLang={() => setLang(lang === 'pt' ? 'en' : 'pt')}
          onZoom={(f) => globe.current && globe.current.zoomBy(f)}
          onCenter={() => globe.current && globe.current.flyTo(pov.lat, pov.lng, HOME.altitude, 800)}
        />
      </div>

      {loading && <div className="panel loading">{tr('loadingImagery', lang)}</div>}
      {(toast || offline) && <div className="panel toast">{toast || tr('offline', lang)}</div>}
      {about && <AboutModal lang={lang} credits={credits} isMock={!grid || grid.mock} meta={meta} onClose={() => setAbout(false)} />}
    </div>
  );
}
