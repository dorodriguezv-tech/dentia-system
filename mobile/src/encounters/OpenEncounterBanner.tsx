import { useQuery } from '@tanstack/react-query';
import { router, usePathname } from 'expo-router';
import { Pressable, Text, View } from 'react-native';

import { getCurrentEncounter } from '@/api/endpoints';
import { hasPermission } from '@/store/session';
import { useTheme } from '@/theme/theme';

/**
 * M4 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §2, B10): "Mientras haya una consulta
 * abierta, se muestra una barra fija arriba... así el odontólogo nunca 'pierde'
 * la consulta al navegar." Vive en app/_layout.tsx (fuera de las pestañas) para
 * verse también sobre la ficha del paciente, no solo dentro de (app).
 */
export function OpenEncounterBanner() {
  const t = useTheme();
  const pathname = usePathname();
  const current = useQuery({
    queryKey: ['encounters', 'current'],
    queryFn: getCurrentEncounter,
    enabled: hasPermission('records.write'),
    refetchInterval: 30_000,
  });

  const enc = current.data;
  if (!enc) return null;
  if (pathname === `/atencion/${enc.id}`) return null; // ya la estás viendo

  const minutes = Math.max(0, Math.round((Date.now() - new Date(enc.started_at).getTime()) / 60_000));

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`En consulta: ${enc.patient_full_name}, ${minutes} minutos. Abrir.`}
      onPress={() =>
        router.push({ pathname: '/atencion/[id]', params: { id: enc.id, patientId: enc.patient_id, patientName: enc.patient_full_name } })
      }
      style={{ backgroundColor: t.colors.primary, paddingHorizontal: 16, paddingVertical: 10, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}
    >
      <Text style={{ color: t.colors.onPrimary, fontWeight: '700', flexShrink: 1 }} numberOfLines={1}>
        En consulta: {enc.patient_full_name} · {minutes} min
      </Text>
      <Text style={{ color: t.colors.onPrimary, fontWeight: '700' }}>Abrir</Text>
    </Pressable>
  );
}
