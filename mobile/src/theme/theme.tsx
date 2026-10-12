import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { useColorScheme } from 'react-native';

import type { Branding } from '@/api/types';

/**
 * Tema de la app a partir de GET /branding (la misma marca que configura el admin
 * en Configuración → Apariencia, docs/04_TEMAS_Y_MARCA.md).
 *
 * Igual que en el frontend web: los componentes NUNCA usan un #hex fijo, siempre
 * `theme.colors.*`. Los colores de hallazgos del odontograma y de estados de cita son
 * semánticos y fijos (no cambian con la marca), como `--color-finding-*` en la web.
 */

export interface Theme {
  dark: boolean;
  clinicName: string;
  /** La clínica todavía usa la identidad del producto (sin nombre ni logo propios). */
  isProductBrand: boolean;
  colors: {
    primary: string;
    primarySoft: string;
    onPrimary: string;
    secondary: string;
    accent: string;
    background: string;
    surface: string;
    border: string;
    text: string;
    textMuted: string;
    success: string;
    warning: string;
    danger: string;
    dangerSoft: string;
  };
  /** Degradado de marca (cian → azul del logo) para acentos decorativos. */
  gradient: [string, string];
  fonts: { heading: string | undefined; headingSemi: string | undefined };
  radius: number;
  space: (n: number) => number;
}

/**
 * Identidad del producto DENT-IA, tomada del logo oficial (assets/brand/).
 * Es el preset "dentia" del backend: si cambias un color aquí, cámbialo también en
 * backend/app/modules/branding/presets.py y frontend/src/theme/presets.ts.
 *
 *  Azul DENT-IA   #004A73  (letras del logo)        → texto de marca, encabezados
 *  Primario       #0A5A8C  (blanco encima 7.4:1)    → botones y enlaces
 *  Azul circuito  #1690B6  (centro del degradado)   → secundario
 *  Cian circuito  #22AAC2  (diente y anillo)        → acento decorativo, nunca texto pequeño (2.8:1)
 */
export const DENTIA_BRAND = {
  name: 'DENT-IA',
  tagline: 'Sistema Inteligente de Gestión Odontológica',
  navy: '#004A73',
  primary: '#0A5A8C',
  secondary: '#1690B6',
  cyan: '#22AAC2',
  primaryDark: '#4FC3D9', // primario en modo oscuro (7.7:1 sobre la superficie oscura)
} as const;

export const BRAND_ASSETS = {
  logo: require('../../assets/brand/dentia-logo.png'),
  logoWhite: require('../../assets/brand/dentia-logo-blanco.png'),
  isotipo: require('../../assets/brand/dentia-isotipo.png'),
  isotipoWhite: require('../../assets/brand/dentia-isotipo-blanco.png'),
};

const DEFAULT_BRAND: Branding = {
  display_name: DENTIA_BRAND.name,
  colors: {
    primary: DENTIA_BRAND.primary,
    secondary: DENTIA_BRAND.secondary,
    accent: DENTIA_BRAND.cyan,
    bg: '#F5F9FC',
    surface: '#FFFFFF',
    border: '#D3E2EC',
    text: '#0E2A3B',
    text_muted: '#4F6676',
    success: '#3BA55C',
    warning: '#E0A100',
    danger: '#D64545',
  },
};

// Base neutra oscura fija (mismo criterio que DARK_OVERRIDES del frontend), con tinte azul DENT-IA
const DARK = { background: '#0B1A24', surface: '#13242F', border: '#24394A', text: '#E6F0F6', textMuted: '#9DB3C2' };

export function buildTheme(branding: Branding | undefined, dark: boolean, fontsLoaded = false): Theme {
  const b = branding ?? DEFAULT_BRAND;
  const c = { ...DEFAULT_BRAND.colors, ...b.colors };
  const surface = dark ? DARK.surface : '#FFFFFF';
  // En modo oscuro el primario de marca (azul) no se lee sobre fondo oscuro: se aclara
  // hasta 4.5:1. Con el preset DENT-IA se usa el cian claro del logo.
  const primary = dark
    ? c.primary.toUpperCase() === DENTIA_BRAND.primary
      ? DENTIA_BRAND.primaryDark
      : ensureContrast(c.primary, surface, 4.5)
    : c.primary;
  const clinicName = b.display_name?.trim() || DENTIA_BRAND.name;
  return {
    dark,
    clinicName,
    isProductBrand: !branding || clinicName.toUpperCase().replace('-', '') === 'DENTIA',
    colors: {
      primary,
      primarySoft: withAlpha(primary, dark ? 0.22 : 0.1),
      onPrimary: readableOn(primary),
      secondary: c.secondary ?? primary,
      accent: c.accent ?? DENTIA_BRAND.cyan,
      background: dark ? DARK.background : (c.bg ?? '#F5F9FC'),
      surface,
      border: dark ? DARK.border : '#D3E2EC',
      text: dark ? DARK.text : (c.text ?? '#0E2A3B'),
      textMuted: dark ? DARK.textMuted : '#4F6676',
      success: c.success ?? '#3BA55C',
      warning: c.warning ?? '#E0A100',
      danger: c.danger ?? '#D64545',
      dangerSoft: withAlpha(c.danger ?? '#D64545', dark ? 0.25 : 0.1),
    },
    gradient: [DENTIA_BRAND.cyan, dark ? DENTIA_BRAND.primaryDark : DENTIA_BRAND.primary],
    fonts: fontsLoaded
      ? { heading: 'Montserrat_700Bold', headingSemi: 'Montserrat_600SemiBold' }
      : { heading: undefined, headingSemi: undefined },
    radius: 12,
    space: (n) => n * 4,
  };
}

/** Colores semánticos del odontograma: fijos, no dependen de la marca. */
export const FINDING_COLORS: Record<string, string> = {
  SANO: '#E5E7EB',
  CARIES: '#DC2626',
  RESTAURACION: '#2563EB',
  CORONA: '#7C3AED',
  ENDODONCIA: '#EA580C',
  AUSENTE: '#111827',
  EXTRACCION_INDICADA: '#B91C1C',
  IMPLANTE: '#0891B2',
  PROTESIS_FIJA: '#4F46E5',
  SELLADOR: '#16A34A',
  FRACTURA: '#CA8A04',
  MOVILIDAD: '#9333EA',
};

export const STATUS_COLORS: Record<string, string> = {
  RESERVADA: '#64748B',
  CONFIRMADA: '#2563EB',
  EN_SALA: '#D97706',
  EN_ATENCION: '#0E7C86',
  TERMINADA: '#16A34A',
  CANCELADA: '#DC2626',
  NO_SHOW: '#9F1239',
  REPROGRAMADA: '#7C3AED',
};

const ThemeContext = createContext<Theme>(buildTheme(undefined, false));

export function ThemeProvider({ branding, fontsLoaded, children }: { branding?: Branding; fontsLoaded?: boolean; children: ReactNode }) {
  const scheme = useColorScheme();
  const theme = useMemo(() => buildTheme(branding, scheme === 'dark', fontsLoaded), [branding, scheme, fontsLoaded]);
  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export const useTheme = () => useContext(ThemeContext);

// ---------- utilidades de color ----------
function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  const full = h.length === 3 ? h.split('').map((x) => x + x).join('') : h;
  const n = parseInt(full.slice(0, 6), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export function withAlpha(hex: string, alpha: number): string {
  const [r, g, b] = hexToRgb(hex);
  return `rgba(${r},${g},${b},${alpha})`;
}

function luminance(hex: string): number {
  const [r, g, b] = hexToRgb(hex).map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Blanco o casi-negro, el que tenga mejor contraste WCAG sobre `bg`. */
export function contrastRatio(a: string, b: string): number {
  const [x, y] = [luminance(a), luminance(b)].sort((m, n) => n - m) as [number, number];
  return (x + 0.05) / (y + 0.05);
}

/** Mezcla el color hacia blanco hasta alcanzar el contraste pedido sobre `bg`. */
export function ensureContrast(color: string, bg: string, ratio: number): string {
  const [r, g, b] = hexToRgb(color);
  for (let t = 0; t <= 1.0001; t += 0.05) {
    const mix = [r, g, b].map((v) => Math.round(v + (255 - v) * t));
    const hex = `#${mix.map((v) => v.toString(16).padStart(2, '0')).join('')}`;
    if (contrastRatio(hex, bg) >= ratio) return hex.toUpperCase();
  }
  return '#FFFFFF';
}

export function readableOn(bg: string): string {
  const L = luminance(bg);
  const whiteContrast = 1.05 / (L + 0.05);
  const darkContrast = (L + 0.05) / (luminance('#0B1A24') + 0.05);
  return whiteContrast >= darkContrast ? '#FFFFFF' : '#0B1A24';
}
