import React, { useMemo, useState } from 'react';
import type { Body, Comparison, Curated, EarthParams, Lang, Layer, ParamResult, Target } from '../lib/types.ts';
import { DIM_NAMES, PARAM_NAMES, fmtCoord, fmtValue, similarPrefix, tr } from '../i18n.ts';
import {
  IconAlert, IconArrowRight, IconCenter, IconCheck, IconClear, IconClose, IconCompass, IconGlobe, IconInfo,
  IconLayers, IconLeaf, IconMinus, IconPin, IconPlus, IconSearch, IconSpark, IconTarget, IconThermo, IconTrophy,
} from './Icons.tsx';
import logoUrl from '../assets/logo-seeyou.png';

const pct = (v: number) => `${Math.round(v * 100)}%`;

/* ---------- miniaturas (gradientes; sem fotos no MVP) ---------- */

export function earthThumb(p: EarthParams): React.CSSProperties {
  let g: string;
  if (p.albedo > 0.6) g = 'linear-gradient(160deg,#f1f6ff 0%,#b9cde6 55%,#7f9cc0 100%)';
  else if (p.ndvi > 0.45) g = 'linear-gradient(160deg,#9fd08a 0%,#3f8a4a 55%,#1f5a34 100%)';
  else if (p.ndvi > 0.2) g = 'linear-gradient(160deg,#d8cf8f 0%,#9a9a55 55%,#5f6b3a 100%)';
  else if (p.albedo > 0.3) g = 'linear-gradient(160deg,#f3d9a4 0%,#d9a866 55%,#a8703d 100%)';
  else g = 'linear-gradient(160deg,#a9a096 0%,#6f655c 55%,#3f3a37 100%)';
  return { backgroundImage: `radial-gradient(circle at 75% 20%,rgba(255,255,255,.45),transparent 40%),${g}` };
}

export function bodyThumb(body: 'moon' | 'mars'): React.CSSProperties {
  return {
    backgroundImage:
      body === 'mars'
        ? 'radial-gradient(circle at 30% 30%,#f0a070,#b5532a 60%,#5a2413)'
        : 'radial-gradient(circle at 30% 30%,#e3e6ec,#8d93a0 60%,#3d414b)',
  };
}

/* ---------- barra superior ---------- */

export function ViewSwitch({ body, onChange, lang }: { body: Body; onChange: (b: Body) => void; lang: Lang }) {
  const items: { id: Body; label: string }[] = [
    { id: 'earth', label: tr('earth', lang) },
    { id: 'mars', label: tr('mars', lang) },
    { id: 'moon', label: tr('moonName', lang) },
  ];
  return (
    <div className="panel pill view-switch" role="tablist">
      {items.map((it) => (
        <button
          key={it.id}
          role="tab"
          aria-selected={body === it.id}
          title={it.label}
          className={`planet-btn planet-${it.id}${body === it.id ? ' on' : ''}`}
          onClick={() => onChange(it.id)}
        >
          <span className="planet" />
        </button>
      ))}
    </div>
  );
}

export function LayerSwitch({ layer, onChange, lang }: { layer: Layer; onChange: (l: Layer) => void; lang: Lang }) {
  const items: { id: Layer; label: string; icon: React.ReactNode }[] = [
    { id: 'sat', label: tr('layerSat', lang), icon: <IconLayers size={20} /> },
    { id: 'foliage', label: tr('layerFoliage', lang), icon: <IconLeaf size={20} /> },
    { id: 'heat', label: tr('layerHeat', lang), icon: <IconThermo size={20} /> },
    { id: 'sim', label: tr('layerSim', lang), icon: <IconSpark size={20} /> },
  ];
  return (
    <div className="panel pill layer-switch">
      {items.map((it) => (
        <button key={it.id} className={`layer-btn${layer === it.id ? ' on' : ''}`} onClick={() => onChange(it.id)}>
          {it.icon}
          <span>{it.label}</span>
        </button>
      ))}
    </div>
  );
}

export interface SearchItem { key: string; label: string; sub: string; }

export function SearchBox({ lang, find, onPick }: { lang: Lang; find: (q: string) => SearchItem[]; onPick: (key: string) => void }) {
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const results = useMemo(() => (q.trim().length >= 2 ? find(q) : []), [q, find]);
  const pick = (key: string) => { onPick(key); setQ(''); setOpen(false); };
  return (
    <div className="search-wrap">
      <div className="panel search">
        <IconSearch />
        <input
          value={q}
          placeholder={tr('search', lang)}
          onChange={(e) => { setQ(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          onKeyDown={(e) => { if (e.key === 'Enter' && results[0]) pick(results[0].key); }}
        />
      </div>
      {open && results.length > 0 && (
        <div className="panel search-results">
          {results.map((r) => (
            <button key={r.key} onMouseDown={(e) => e.preventDefault()} onClick={() => pick(r.key)}>
              <span>{r.label}</span>
              <small>{r.sub}</small>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function TargetSelect({ targets, value, onChange, lang }: { targets: Target[]; value: string; onChange: (id: string) => void; lang: Lang }) {
  return (
    <label className="panel target-select">
      <IconTarget size={20} />
      <span className="muted">{tr('target', lang)}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <optgroup label={tr('moonName', lang)}>
          {targets.filter((t) => t.body === 'moon').map((t) => <option key={t.id} value={t.id}>{t.name[lang]}</option>)}
        </optgroup>
        <optgroup label={tr('mars', lang)}>
          {targets.filter((t) => t.body === 'mars').map((t) => <option key={t.id} value={t.id}>{t.name[lang]}</option>)}
        </optgroup>
      </select>
    </label>
  );
}

export function TopLeft({ children }: { children: React.ReactNode }) {
  return (
    <div className="top-left">
      <img className="brand-logo" src={logoUrl} alt="SeeYou! Finder" />
      {children}
    </div>
  );
}

/* ---------- Top Locais / Alvos (componente "Location Menu" do Figma) ---------- */

export interface MenuItem {
  key: string;
  name: string;
  subPrefix: string;
  subAccent: string;
  accent: 'mars' | 'moon' | 'earth';
  score: number;
  right: string;
  thumb: React.CSSProperties;
  active?: boolean;
}

export function LocationMenu(props: {
  title: string;
  icon: 'trophy' | 'target';
  items: MenuItem[];
  lang: Lang;
  onPick: (key: string) => void;
  collapsible: boolean;
}) {
  const [all, setAll] = useState(false);
  return (
    <section className={`panel location-menu${all ? ' expanded' : ''}`}>
      <header>
        <div className="lm-title">
          {props.icon === 'trophy' ? <IconTrophy /> : <IconTarget />}
          <span>{props.title}</span>
        </div>
        {props.collapsible && (
          <button className="see-all" onClick={() => setAll(!all)}>
            {tr(all ? 'seeLess' : 'seeAll', props.lang)} <IconArrowRight />
          </button>
        )}
      </header>
      <div className="divider" />
      <div className="lm-list">
        {props.items.map((it) => (
          <button key={it.key} className={`loc-card${it.active ? ' active' : ''}`} onClick={() => props.onPick(it.key)}>
            <span className="thumb" style={it.thumb} />
            <span className="loc-body">
              <span className="loc-top">
                <span className="loc-name">{it.name}</span>
                <span className="loc-pct">{pct(it.score)}</span>
              </span>
              <span className="loc-sub">
                <span>{it.subPrefix} <em className={`accent-${it.accent}`}>{it.subAccent}</em></span>
                <span>{it.right}</span>
              </span>
              <span className="bar"><span style={{ width: pct(it.score) }} /></span>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

/* ---------- comparação ---------- */

function ParamCard({ p, lang }: { p: ParamResult; lang: Lang }) {
  return (
    <div className="param-card">
      <div className="param-head">
        <span className="param-name">{PARAM_NAMES[p.key][lang]}</span>
        <span className="param-pct">{p.score === null ? tr('na', lang) : pct(p.score)}</span>
      </div>
      <div className="param-vals">
        <span>{tr('earthVal', lang)}: <b>{fmtValue(p.earth, p.unit, lang)}</b></span>
        <span>{tr('targetVal', lang)}: <b>{fmtValue(p.target, p.unit, lang)}</b></span>
      </div>
      <span className="bar"><span style={{ width: p.score === null ? '0%' : pct(p.score) }} /></span>
    </div>
  );
}

export function WhyPanel({ mode, cmp, target, lang }: { mode: 'why' | 'whynot'; cmp: Comparison; target: Target; lang: Lang }) {
  const all = cmp.dims.flatMap((d) => d.params);
  const list = all
    .filter((p) => p.score !== null && (mode === 'why' ? p.score >= 0.5 : p.score < 0.5))
    .sort((a, b) => (mode === 'why' ? (b.score as number) - (a.score as number) : (a.score as number) - (b.score as number)));
  const nas = all.filter((p) => p.score === null);
  const dims = cmp.dims.filter((d) => d.score !== null && (mode === 'why' ? d.score >= 0.5 : d.score < 0.5));
  return (
    <section className={`panel why-panel ${mode}`}>
      <header>
        {mode === 'why' ? <IconCheck /> : <IconAlert />}
        {mode === 'why' ? (
          <h2>{tr('why', lang)}</h2>
        ) : lang === 'pt' ? (
          <h2>Por que <em>não</em>?</h2>
        ) : (
          <h2>Why <em>not</em>?</h2>
        )}
      </header>
      <div className="divider" />
      <div className="why-scroll">
        {dims.length > 0 && (
          <div className="dim-chips">
            {dims.map((d) => (
              <span key={d.id} className="chip">{DIM_NAMES[d.id][lang]} <b>{pct(d.score as number)}</b></span>
            ))}
          </div>
        )}
        {list.length === 0 && <p className="muted small">{tr(mode === 'why' ? 'noneWhy' : 'noneWhyNot', lang)}</p>}
        {list.map((p) => <ParamCard key={p.key} p={p} lang={lang} />)}
        {mode === 'whynot' && nas.length > 0 && (
          <p className="muted small">
            {tr('na', lang)}: {nas.map((p) => PARAM_NAMES[p.key][lang]).join(', ')} ({tr('naHint', lang)}).
          </p>
        )}
        {mode === 'whynot' && (
          <div className="never">
            <h3>{tr('neverOnEarth', lang)}</h3>
            <ul>{target.never_on_earth[lang].map((s) => <li key={s}>{s}</li>)}</ul>
          </div>
        )}
      </div>
    </section>
  );
}

export function SelectedCard(props: {
  name: string;
  lat: number;
  lon: number;
  total: number;
  target: Target;
  targets: Target[];
  scores: Record<string, number>;
  curated: Curated | null;
  lang: Lang;
  onTarget: (id: string) => void;
  onClose: () => void;
}) {
  const { lang, target, curated } = props;
  return (
    <section className="panel selected-card">
      <header>
        <IconPin />
        <div className="sel-title">
          <h2>{props.name}</h2>
          <small>{fmtCoord(props.lat, props.lon)}</small>
        </div>
        <button className="icon-btn" onClick={props.onClose} aria-label={tr('close', lang)}><IconClose size={18} /></button>
      </header>
      <div className="sel-score">
        <strong>{pct(props.total)}</strong>
        <span>
          {similarPrefix(lang, target.body)} <em className={`accent-${target.body}`}>{target.body === 'mars' ? tr('mars', lang) : tr('moon', lang)}</em>
          <br />
          <small>{target.name[lang]}</small>
        </span>
      </div>
      <span className="bar big"><span style={{ width: pct(props.total) }} /></span>
      <div className="target-chips">
        <small className="muted">{tr('compareWith', lang)}</small>
        <div>
          {props.targets.map((t) => (
            <button key={t.id} className={`chip body-${t.body}${t.id === target.id ? ' on' : ''}`} onClick={() => props.onTarget(t.id)}>
              {t.short[lang]} <b>{pct(props.scores[t.id] || 0)}</b>
            </button>
          ))}
        </div>
      </div>
      {curated && (
        <div className="curated">
          <span className={`tag${curated.discovery ? ' discovery' : ''}`}>{tr(curated.discovery ? 'discovery' : 'curated', lang)}</span>
          <h3>{tr('whyInteresting', lang)}</h3>
          <p>{curated.why[lang]}</p>
          <h3>{tr('whereBreaks', lang)}</h3>
          <p>{curated.breaks[lang]}</p>
        </div>
      )}
    </section>
  );
}

export function TargetDetail({ target, best, lang, onViewEarth }: { target: Target; best: { name: string; score: number } | null; lang: Lang; onViewEarth: () => void }) {
  const keys = Object.keys(target.params) as (keyof Target['params'])[];
  return (
    <section className="panel why-panel target-detail">
      <header>
        <IconTarget />
        <h2>{target.name[lang]}</h2>
      </header>
      <div className="divider" />
      <div className="why-scroll">
        <p>{target.blurb[lang]}</p>
        <table>
          <tbody>
            {keys.map((k) => (
              <tr key={k}>
                <td>{PARAM_NAMES[k][lang]}</td>
                <td><b>{fmtValue(target.params[k], unitOf(k), lang)}</b></td>
              </tr>
            ))}
          </tbody>
        </table>
        {best && (
          <p className="small">{tr('bestAnalog', lang)}: <b>{best.name}</b> ({pct(best.score)})</p>
        )}
        <div className="never">
          <h3>{tr('neverOnEarth', lang)}</h3>
          <ul>{target.never_on_earth[lang].map((s) => <li key={s}>{s}</li>)}</ul>
        </div>
        <button className="cta" onClick={onViewEarth}>{tr('viewOnEarth', lang)} <IconArrowRight size={20} /></button>
      </div>
    </section>
  );
}

function unitOf(k: string): string {
  return ({ slope_deg: '°', roughness_m: 'm', temp_range_k: 'K', temp_min_k: 'K', precip_mm: 'mm' } as Record<string, string>)[k] || '';
}

/* ---------- barra inferior ---------- */

function ToolBtn({ tip, onClick, on, children }: { tip: string; onClick: () => void; on?: boolean; children: React.ReactNode }) {
  const [a, b] = tip.split('|');
  return (
    <button className={`tool-btn${on ? ' on' : ''}`} onClick={onClick} aria-label={a}>
      {children}
      <span className="tip"><b>{a}</b>{b}</span>
    </button>
  );
}

export function BottomBar(props: {
  lang: Lang;
  body: Body;
  altitudeKm: number;
  centerLat: number;
  centerLon: number;
  scale: { km: number; px: number };
  markersOn: boolean;
  isMock: boolean;
  onClear: () => void;
  onMarkers: () => void;
  onExplore: () => void;
  onAbout: () => void;
  onLang: () => void;
  onZoom: (f: number) => void;
  onCenter: () => void;
}) {
  const { lang } = props;
  const km = props.scale.km >= 1 ? props.scale.km.toLocaleString(lang === 'pt' ? 'pt-BR' : 'en-US') : props.scale.km.toString();
  return (
    <>
      <div className="scale-row">
        <div className="panel scale-pill">
          <span className="scale-bar" style={{ width: props.scale.px }} />
          <b>{km}</b> km
        </div>
        {props.isMock && <div className="panel mock-pill">{tr('mock', lang)}</div>}
      </div>
      <footer className="panel bottom-bar">
        <div className="tools">
          <ToolBtn tip={tr('tipClear', lang)} onClick={props.onClear}><IconClear /></ToolBtn>
          <ToolBtn tip={tr('tipMarkers', lang)} onClick={props.onMarkers} on={props.markersOn}><IconPin /></ToolBtn>
          <ToolBtn tip={tr('tipExplore', lang)} onClick={props.onExplore}><IconCompass /></ToolBtn>
          <ToolBtn tip={tr('tipAbout', lang)} onClick={props.onAbout}><IconInfo /></ToolBtn>
          <ToolBtn tip={tr('tipLang', lang)} onClick={props.onLang}><span className="lang-code">{lang === 'pt' ? 'PT' : 'EN'}</span></ToolBtn>
        </div>
        <div className="tools right">
          <ToolBtn tip={tr('tipZoomOut', lang)} onClick={() => props.onZoom(1.45)}><IconMinus /></ToolBtn>
          <ToolBtn tip={tr('tipZoomIn', lang)} onClick={() => props.onZoom(1 / 1.45)}><IconPlus /></ToolBtn>
          <ToolBtn tip={tr('tipCenter', lang)} onClick={props.onCenter}><IconCenter /></ToolBtn>
          <span className="readout"><IconGlobe size={18} /> {Math.round(props.altitudeKm).toLocaleString(lang === 'pt' ? 'pt-BR' : 'en-US')} {tr('altitude', lang)}</span>
          <span className="sep" />
          <span className="readout coords">{fmtCoord(props.centerLat, props.centerLon)}</span>
        </div>
      </footer>
    </>
  );
}

export function AboutModal({ lang, credits, onClose }: { lang: Lang; credits: string[]; onClose: () => void }) {
  return (
    <div className="modal-back" onClick={onClose}>
      <div className="panel modal" onClick={(e) => e.stopPropagation()}>
        <header>
          <h2>{tr('aboutTitle', lang)}</h2>
          <button className="icon-btn" onClick={onClose} aria-label={tr('close', lang)}><IconClose size={18} /></button>
        </header>
        <p>{tr('about1', lang)}</p>
        <p className="mono">{tr('about2', lang)}</p>
        <p className="warn">{tr('about3', lang)}</p>
        <p>{tr('about4', lang)}</p>
        <p className="muted small">{credits.join(' · ')}</p>
      </div>
    </div>
  );
}
