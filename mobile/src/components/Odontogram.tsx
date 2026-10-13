import { useMemo, useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import Svg, { G, Polygon, Rect, Text as SvgText } from 'react-native-svg';

import type { Surface, ToothFinding } from '@/api/types';
import { FINDING_COLORS, useTheme } from '@/theme/theme';

/**
 * Odontograma FDI dibujado con react-native-svg, mismo modelo que Tooth.tsx de la web:
 * 5 zonas en cruz (arriba V, abajo P/L, centro O/I, lados M/D con mesial hacia la
 * línea media). Un hallazgo de "toda la pieza" (surface = null) se dibuja como un
 * recuadro completo. PLANNED se dibuja con contorno discontinuo.
 *
 * Cada pieza es un objetivo táctil de ≥ 44 px; las zonas internas son para precisión
 * con stylus. Tocar una pieza o zona llama a onSelect(pieza, superficie | null).
 */

const UPPER_PERM = [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28];
const LOWER_PERM = [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38];
const UPPER_TEMP = [55, 54, 53, 52, 51, 61, 62, 63, 64, 65];
const LOWER_TEMP = [85, 84, 83, 82, 81, 71, 72, 73, 74, 75];

type Zone = 'top' | 'bottom' | 'left' | 'right' | 'center';

const ZONES: Record<Zone, string> = {
  top: '2,2 42,2 30,14 14,14',
  bottom: '2,42 42,42 30,30 14,30',
  left: '2,2 14,14 14,30 2,42',
  right: '42,2 30,14 30,30 42,42',
  center: '14,14 30,14 30,30 14,30',
};

export function surfaceForZone(tooth: number, zone: Zone): Surface {
  const quadrant = Math.floor(tooth / 10);
  const position = tooth % 10;
  const upper = [1, 2, 5, 6].includes(quadrant);
  const patientRight = [1, 4, 5, 8].includes(quadrant); // se dibujan a la izquierda de la pantalla
  // Premolares/molares (4–8) y molares temporales (4–5) son posteriores
  const posterior = position >= 4;
  switch (zone) {
    case 'top':
      return 'V';
    case 'bottom':
      return upper ? 'P' : 'L';
    case 'center':
      return posterior ? 'O' : 'I';
    case 'left':
      return patientRight ? 'D' : 'M';
    case 'right':
      return patientRight ? 'M' : 'D';
  }
}

/** Las 5 superficies reales de una pieza (M5: selección múltiple en la hoja de
 * captura), en el mismo orden que las zonas de la cruz. */
export function applicableSurfaces(tooth: number): Surface[] {
  return (Object.keys(ZONES) as Zone[]).map((z) => surfaceForZone(tooth, z));
}

interface Props {
  findings: ToothFinding[];
  onSelect?: (tooth: number, surface: Surface | null) => void;
  selected?: { tooth: number; surface: Surface | null } | null;
}

export function Odontogram({ findings, onSelect, selected }: Props) {
  const t = useTheme();
  const [dentition, setDentition] = useState<'permanente' | 'temporal'>('permanente');

  const index = useMemo(() => {
    const existing = new Map<string, ToothFinding>();
    const planned = new Map<string, ToothFinding>();
    for (const f of findings) {
      const key = `${f.tooth_fdi}-${f.surface ?? 'ALL'}`;
      if (f.kind === 'EXISTING') existing.set(key, f);
      if (f.kind === 'PLANNED') planned.set(key, f);
    }
    return { existing, planned };
  }, [findings]);

  const upper = dentition === 'permanente' ? UPPER_PERM : UPPER_TEMP;
  const lower = dentition === 'permanente' ? LOWER_PERM : LOWER_TEMP;
  const size = 46;

  const renderTooth = (tooth: number) => {
    const whole = index.existing.get(`${tooth}-ALL`);
    const wholePlanned = index.planned.get(`${tooth}-ALL`);
    const isSel = selected?.tooth === tooth;
    const label = `Pieza ${tooth}${whole ? `, ${whole.finding_code.toLowerCase()}` : ''}`;
    return (
      <Pressable
        key={tooth}
        accessibilityRole="button"
        accessibilityLabel={label}
        onPress={() => onSelect?.(tooth, null)}
        style={{ alignItems: 'center', width: size, paddingVertical: 2 }}
      >
        <Text style={{ fontSize: 11, color: t.colors.textMuted }}>{tooth}</Text>
        <Svg width={size - 4} height={size - 4} viewBox="0 0 44 44">
          {whole ? (
            <G>
              <Rect x={2} y={2} width={40} height={40} fill={FINDING_COLORS[whole.finding_code] ?? t.colors.textMuted} stroke={t.colors.text} strokeWidth={1} />
              <SvgText x={22} y={27} fontSize={11} fontWeight="bold" fill="#FFFFFF" textAnchor="middle">
                {abbrev(whole.finding_code)}
              </SvgText>
            </G>
          ) : (
            (Object.keys(ZONES) as Zone[]).map((zone) => {
              const s = surfaceForZone(tooth, zone);
              const ex = index.existing.get(`${tooth}-${s}`);
              const pl = index.planned.get(`${tooth}-${s}`);
              const zoneSelected = isSel && selected?.surface === s;
              return (
                <Polygon
                  key={zone}
                  points={ZONES[zone]}
                  fill={ex ? (FINDING_COLORS[ex.finding_code] ?? t.colors.textMuted) : t.colors.surface}
                  stroke={zoneSelected ? t.colors.primary : pl ? (FINDING_COLORS[pl.finding_code] ?? t.colors.primary) : t.colors.border}
                  strokeWidth={zoneSelected || pl ? 2.5 : 1}
                  strokeDasharray={pl ? '3,2' : undefined}
                  onPress={() => onSelect?.(tooth, s)}
                />
              );
            })
          )}
          {wholePlanned ? (
            <Rect x={1} y={1} width={42} height={42} fill="none" stroke={FINDING_COLORS[wholePlanned.finding_code] ?? t.colors.primary} strokeWidth={2.5} strokeDasharray="4,3" />
          ) : null}
          {isSel && selected?.surface === null ? <Rect x={0.5} y={0.5} width={43} height={43} fill="none" stroke={t.colors.primary} strokeWidth={3} /> : null}
        </Svg>
      </Pressable>
    );
  };

  return (
    <View style={{ gap: 8 }}>
      <View style={{ flexDirection: 'row', gap: 8 }}>
        {(['permanente', 'temporal'] as const).map((d) => (
          <Pressable
            key={d}
            onPress={() => setDentition(d)}
            accessibilityRole="tab"
            accessibilityState={{ selected: dentition === d }}
            style={{
              paddingHorizontal: 14,
              minHeight: 40,
              justifyContent: 'center',
              borderRadius: 999,
              backgroundColor: dentition === d ? t.colors.primary : t.colors.primarySoft,
            }}
          >
            <Text style={{ color: dentition === d ? t.colors.onPrimary : t.colors.primary, fontWeight: '600' }}>
              {d === 'permanente' ? 'Permanente' : 'Temporal'}
            </Text>
          </Pressable>
        ))}
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator>
        <View style={{ gap: 10 }}>
          <View style={{ flexDirection: 'row' }}>{upper.map(renderTooth)}</View>
          <View style={{ height: 1, backgroundColor: t.colors.border }} />
          <View style={{ flexDirection: 'row' }}>{lower.map(renderTooth)}</View>
        </View>
      </ScrollView>
      <Legend />
    </View>
  );
}

function abbrev(code: string): string {
  const map: Record<string, string> = { ausente: 'X', implante: 'IMP', corona: 'CR', endodoncia: 'EN', extraccion_indicada: 'EI', protesis_fija: 'PF', fractura: 'FX', movilidad: 'MV' };
  return map[code] ?? code.slice(0, 2).toUpperCase();
}

function Legend() {
  const t = useTheme();
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
      {Object.entries(FINDING_COLORS)
        .filter(([k]) => k !== 'sano')
        .map(([code, color]) => (
          <View key={code} style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
            <View style={{ width: 12, height: 12, backgroundColor: color, borderRadius: 2 }} />
            <Text style={{ fontSize: 12, color: t.colors.textMuted }}>{code.replace('_', ' ').toLowerCase()}</Text>
          </View>
        ))}
    </View>
  );
}
