import { useState } from 'react';
import { Image, Text, View } from 'react-native';

import { brandingLogoUrl } from '@/api/endpoints';
import { BRAND_ASSETS, DENTIA_BRAND, useTheme } from '@/theme/theme';

/**
 * Logos de marca.
 *
 * - DENT-IA es la marca del PRODUCTO (logo oficial empaquetado en assets/brand/).
 * - Cada clínica puede subir su propio logo en Configuración → Apariencia (web); se sirve
 *   en GET /branding/logo. Si la clínica no tiene logo (404), se muestra el de DENT-IA.
 * - En modo oscuro se usa la versión blanca del logo DENT-IA (las letras azul marino
 *   no se leen sobre fondo oscuro).
 */

export function DentiaLogo({ width = 220 }: { width?: number }) {
  const t = useTheme();
  // Proporción del logo completo recortado: 2001 × 1405
  return (
    <Image
      source={t.dark ? BRAND_ASSETS.logoWhite : BRAND_ASSETS.logo}
      style={{ width, height: width * (1405 / 2001) }}
      resizeMode="contain"
      accessibilityLabel={`${DENTIA_BRAND.name}, ${DENTIA_BRAND.tagline}`}
    />
  );
}

/** Logo de la clínica si existe; si no, el logo DENT-IA. */
export function ClinicLogo({ serverUrl, width = 220 }: { serverUrl: string | null; width?: number }) {
  const t = useTheme();
  const [failed, setFailed] = useState(false);
  if (!serverUrl || failed || t.isProductBrand) return <DentiaLogo width={width} />;
  return (
    <Image
      source={{ uri: brandingLogoUrl(serverUrl) }}
      style={{ width, height: width * 0.5 }}
      resizeMode="contain"
      onError={() => setFailed(true)}
      accessibilityLabel={`Logo de ${t.clinicName}`}
    />
  );
}

/** "con tecnología DENT-IA": visible cuando la clínica usa su propia marca. */
export function PoweredByDentia() {
  const t = useTheme();
  return (
    <View
      style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 8 }}
      accessibilityLabel="Con tecnología DENT-IA"
    >
      <Text style={{ color: t.colors.textMuted, fontSize: 12 }}>con tecnología</Text>
      <Image source={BRAND_ASSETS.isotipo} style={{ width: 18, height: 18 }} accessible={false} />
      <Text style={{ color: t.dark ? DENTIA_BRAND.primaryDark : DENTIA_BRAND.navy, fontSize: 13, fontWeight: '700', fontFamily: t.fonts.heading }}>
        DENT-IA
      </Text>
    </View>
  );
}

/** Franja delgada con el degradado del logo (cian → azul), sin dependencias nativas. */
export function BrandStripe({ height = 4 }: { height?: number }) {
  const t = useTheme();
  const steps = 12;
  const [a, b] = t.gradient;
  const mix = (i: number) => {
    const p = i / (steps - 1);
    const ha = a.match(/\w\w/g)!.map((x) => parseInt(x, 16));
    const hb = b.match(/\w\w/g)!.map((x) => parseInt(x, 16));
    return `rgb(${ha.map((v, k) => Math.round(v + ((hb[k] ?? v) - v) * p)).join(',')})`;
  };
  return (
    <View style={{ flexDirection: 'row', height, borderRadius: height, overflow: 'hidden' }} accessible={false}>
      {Array.from({ length: steps }, (_, i) => (
        <View key={i} style={{ flex: 1, backgroundColor: mix(i) }} />
      ))}
    </View>
  );
}
