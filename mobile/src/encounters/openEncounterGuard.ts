import { router } from 'expo-router';
import { Alert } from 'react-native';

import type { CurrentEncounter } from '@/api/types';

/**
 * M4 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3, R2): "Solo una consulta abierta por
 * profesional; si hay otra, preguntar '¿Volver a ella o dejarla en borrador?'".
 * Es una ayuda de la interfaz, no una regla del backend (que hoy no impide tener
 * más de una atención sin cerrar — no existe todavía un cierre real, B11/M6).
 */
export function guardSingleOpenEncounter(
  current: CurrentEncounter | null | undefined,
  startNew: () => void,
): void {
  if (!current) {
    startNew();
    return;
  }
  Alert.alert(
    'Consulta abierta',
    `Tienes abierta la consulta de ${current.patient_full_name}. ¿Volver a ella o dejarla en borrador?`,
    [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Volver a ella',
        onPress: () =>
          router.push({
            pathname: '/atencion/[id]',
            params: { id: current.id, patientId: current.patient_id, patientName: current.patient_full_name },
          }),
      },
      { text: 'Dejarla en borrador', onPress: startNew },
    ],
  );
}
