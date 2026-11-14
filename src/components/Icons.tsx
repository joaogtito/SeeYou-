// Ícones de traço desenhados à mão para o MVP.
// O Figma usa o conjunto "keyline-icons"; quando exportarem os SVGs, basta trocar aqui.
import React from 'react';

type P = { size?: number };

const S = ({ size = 24, children }: P & { children: React.ReactNode }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {children}
  </svg>
);

export const IconSearch = (p: P) => (<S {...p}><circle cx="11" cy="11" r="6.5" /><path d="M16 16l4.5 4.5" /></S>);
export const IconTrophy = (p: P) => (<S {...p}><path d="M8 4h8v5a4 4 0 0 1-8 0V4z" /><path d="M8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4" /><path d="M12 13v4M8.5 20h7M10 17h4" /></S>);
export const IconTarget = (p: P) => (<S {...p}><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" /></S>);
export const IconArrowRight = (p: P) => (<S {...p}><path d="M5 12h14M13 6l6 6-6 6" /></S>);
export const IconLayers = (p: P) => (<S {...p}><path d="M12 3l9 5-9 5-9-5 9-5z" /><path d="M3 12.5l9 5 9-5M3 16.5l9 5 9-5" /></S>);
export const IconLeaf = (p: P) => (<S {...p}><path d="M5 19c0-8 5-13 14-14 0 9-5 14-13 14" /><path d="M5 19c3-5 6-7 10-9" /></S>);
export const IconThermo = (p: P) => (<S {...p}><path d="M10 14V5a2 2 0 0 1 4 0v9a4 4 0 1 1-4 0z" /><path d="M12 9v7" /></S>);
export const IconSpark = (p: P) => (<S {...p}><path d="M12 3l2.2 5.8L20 11l-5.8 2.2L12 19l-2.2-5.8L4 11l5.8-2.2L12 3z" /></S>);
export const IconClear = (p: P) => (<S {...p}><path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3" /><path d="M9.5 9.5l5 5M14.5 9.5l-5 5" /></S>);
export const IconPin = (p: P) => (<S {...p}><path d="M12 21s-6.5-6-6.5-11a6.5 6.5 0 0 1 13 0c0 5-6.5 11-6.5 11z" /><circle cx="12" cy="10" r="2.3" /></S>);
export const IconCompass = (p: P) => (<S {...p}><circle cx="12" cy="12" r="8.5" /><path d="M15.5 8.5l-2 5-5 2 2-5 5-2z" /></S>);
export const IconInfo = (p: P) => (<S {...p}><circle cx="12" cy="12" r="8.5" /><path d="M12 11v5M12 8h.01" /></S>);
export const IconGlobe = (p: P) => (<S {...p}><circle cx="12" cy="12" r="8.5" /><path d="M3.5 12h17M12 3.5c3 3 3 14 0 17M12 3.5c-3 3-3 14 0 17" /></S>);
export const IconMinus = (p: P) => (<S {...p}><circle cx="11" cy="11" r="6.5" /><path d="M16 16l4.5 4.5M8.5 11h5" /></S>);
export const IconPlus = (p: P) => (<S {...p}><circle cx="11" cy="11" r="6.5" /><path d="M16 16l4.5 4.5M8.5 11h5M11 8.5v5" /></S>);
export const IconCenter = (p: P) => (<S {...p}><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="1.6" /><path d="M12 2.5V6M12 18v3.5M2.5 12H6M18 12h3.5" /></S>);
export const IconCheck = (p: P) => (<S {...p}><circle cx="12" cy="12" r="8.5" /><path d="M8 12.5l2.8 2.8L16 9.8" /></S>);
export const IconAlert = (p: P) => (<S {...p}><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5v5.5M12 16h.01" /></S>);
export const IconClose = (p: P) => (<S {...p}><path d="M6 6l12 12M18 6L6 18" /></S>);

/** Logo do time: planeta com anel (redesenhado a partir da página "Logo" do Figma). */
export const Logo = ({ size = 50 }: P) => (
  <svg width={size} height={(size * 42) / 50} viewBox="0 0 50 42" aria-label="Analog Finder">
    <ellipse cx="25" cy="22" rx="23" ry="7" transform="rotate(-18 25 22)" fill="none" stroke="#dfe6ff" strokeWidth="3.2" />
    <circle cx="25" cy="21" r="12.5" fill="#dfe6ff" />
    <path d="M3.6 28.4c5.2 3 17.6 0.6 28.6-5.2 5.6-3 10-6.4 12.6-9.4" fill="none" stroke="#0e192f" strokeWidth="6" strokeLinecap="round" />
    <path d="M3.6 28.4c5.2 3 17.6 0.6 28.6-5.2 5.6-3 10-6.4 12.6-9.4" fill="none" stroke="#dfe6ff" strokeWidth="3.2" strokeLinecap="round" />
    <circle cx="42.5" cy="5" r="1.4" fill="#dfe6ff" />
    <circle cx="6" cy="8" r="1" fill="#dfe6ff" />
  </svg>
);
