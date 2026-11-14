import React, { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react';
import Globe from 'react-globe.gl';
import * as THREE from 'three';
import type { Body } from '../lib/types.ts';

export interface Marker {
  id: string;
  lat: number;
  lon: number;
  label: string;
  kind: 'curated' | 'discovery' | 'target';
  active?: boolean;
}

export interface Pov { lat: number; lng: number; altitude: number; }

export interface GlobeHandle {
  flyTo: (lat: number, lon: number, altitude?: number, ms?: number) => void;
  zoomBy: (factor: number) => void;
}

interface Props {
  body: Body;
  texture: HTMLCanvasElement | null;
  markers: Marker[];
  selection: { lat: number; lon: number; res: number } | null;
  onClick: (lat: number, lon: number) => void;
  onMarker: (id: string) => void;
  onPov: (pov: Pov) => void;
}

const ATMOSPHERE: Record<Body, { show: boolean; color: string; alt: number }> = {
  earth: { show: true, color: '#6fb3ff', alt: 0.17 },
  mars: { show: true, color: '#e8946a', alt: 0.1 },
  moon: { show: false, color: '#c2c7cf', alt: 0.05 },
};

const SEL = '#6dff8f';
const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));

const GlobeView = forwardRef<GlobeHandle, Props>(function GlobeView(props, ref) {
  const g = useRef<any>(null);
  const cb = useRef(props);
  cb.current = props;
  const raf = useRef(0);

  const [size, setSize] = useState({ w: window.innerWidth, h: window.innerHeight });
  useEffect(() => {
    const f = () => setSize({ w: window.innerWidth, h: window.innerHeight });
    window.addEventListener('resize', f);
    return () => window.removeEventListener('resize', f);
  }, []);

  useImperativeHandle(ref, () => ({
    flyTo(lat, lon, altitude = 1.1, ms = 1200) {
      if (g.current) g.current.pointOfView({ lat, lng: lon, altitude }, ms);
    },
    zoomBy(factor) {
      if (!g.current) return;
      const p = g.current.pointOfView();
      g.current.pointOfView({ lat: p.lat, lng: p.lng, altitude: clamp(p.altitude * factor, 0.12, 4) }, 350);
    },
  }), []);

  // Material próprio: a textura é aplicada direto nele (sem globeImageUrl).
  // Assim a troca Terra/Lua/Marte é síncrona e não passa pelo estado "sem imagem" da biblioteca.
  const material = useMemo(() => new THREE.MeshPhongMaterial({ color: 0xffffff, shininess: 6 }), []);
  const texCache = useRef(new WeakMap<HTMLCanvasElement, THREE.CanvasTexture>());
  useEffect(() => {
    const canvas = props.texture;
    if (!canvas) return;
    let tex = texCache.current.get(canvas);
    if (!tex) {
      tex = new THREE.CanvasTexture(canvas);
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.anisotropy = 4;
      texCache.current.set(canvas, tex);
    }
    material.map = tex;
    material.color.set(0xffffff);
    material.needsUpdate = true;
  }, [props.texture, material]);

  // Seleção como contorno (linha), não como polígono preenchido:
  // um polígono com a ordem de vértices "errada" cobre o globo inteiro.
  const paths = useMemo(() => {
    const s = props.selection;
    if (!s) return [];
    const h = s.res / 2;
    return [{
      pts: [
        [s.lat - h, s.lon - h], [s.lat - h, s.lon + h],
        [s.lat + h, s.lon + h], [s.lat + h, s.lon - h],
        [s.lat - h, s.lon - h],
      ],
    }];
  }, [props.selection]);

  const rings = useMemo(
    () => (props.selection ? [{ lat: props.selection.lat, lng: props.selection.lon }] : []),
    [props.selection],
  );

  const atm = ATMOSPHERE[props.body];

  return (
    <Globe
      ref={g}
      width={size.w}
      height={size.h}
      backgroundColor="rgba(0,0,0,0)"
      globeMaterial={material}
      showAtmosphere={atm.show}
      atmosphereColor={atm.color}
      atmosphereAltitude={atm.alt}
      onGlobeReady={() => {
        if (!g.current) return;
        g.current.pointOfView({ lat: -12, lng: -52, altitude: 2.3 }, 0);
        const c = g.current.controls();
        if (c) { c.minDistance = 112; c.maxDistance = 520; }
      }}
      onGlobeClick={(c: any) => cb.current.onClick(c.lat, c.lng)}
      onZoom={(pov: any) => {
        cancelAnimationFrame(raf.current);
        raf.current = requestAnimationFrame(() => cb.current.onPov(pov));
      }}
      pathsData={paths}
      pathPoints="pts"
      pathPointLat={(p: any) => p[0]}
      pathPointLng={(p: any) => p[1]}
      pathPointAlt={0.004}
      pathResolution={0.25}
      pathColor={() => SEL}
      pathStroke={2.5}
      pathTransitionDuration={0}
      ringsData={rings}
      ringColor={() => (t: number) => `rgba(109,255,143,${1 - t})`}
      ringMaxRadius={3}
      ringPropagationSpeed={2}
      ringRepeatPeriod={1100}
      htmlElementsData={props.markers}
      htmlLat={(d: any) => d.lat}
      htmlLng={(d: any) => d.lon}
      htmlAltitude={0.01}
      htmlElement={(d: any) => {
        const el = document.createElement('div');
        el.className = `gm gm-${d.kind}${d.active ? ' gm-active' : ''}`;
        const dot = document.createElement('span');
        dot.className = 'gm-dot';
        const label = document.createElement('span');
        label.className = 'gm-label';
        label.textContent = d.label;
        el.appendChild(dot);
        el.appendChild(label);
        el.style.pointerEvents = 'auto';
        el.style.cursor = 'pointer';
        el.onclick = (ev) => { ev.stopPropagation(); cb.current.onMarker(d.id); };
        return el;
      }}
    />
  );
});

export default GlobeView;
