import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { TextInput, View } from 'react-native';

import { errorMessage } from '@/api/client';
import { addDays, combineDayAndTime, dateKey, dayLabel, hhmm } from '@/api/dates';
import { getAvailability } from '@/api/endpoints';
import type { Uuid } from '@/api/types';
import { Body, Button, ErrorBox, Loading, Row } from '@/components/ui';
import { useTheme } from '@/theme/theme';

/**
 * M3 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3): elige día y hora para una cita nueva o
 * una reprogramación, con los mismos huecos libres reales que calcula el backend
 * (B8, GET /appointments/availability) — nunca inventados en el teléfono. No hay un
 * selector de fecha nativo instalado (evita agregar un paquete con código nativo a
 * mitad de esta tarea); el día se cambia con ◀ / ▶ / Hoy / Mañana, como en Agenda.
 */
export function SlotPicker({
  providerId,
  durationMinutes,
  value,
  onChange,
  initialDayOffset = 0,
}: {
  providerId: Uuid | null;
  durationMinutes: number;
  value: string | null;
  onChange: (iso: string) => void;
  /** M7: "próxima cita" sugiere +7 días en vez de hoy. */
  initialDayOffset?: number;
}) {
  const t = useTheme();
  const [dayOffset, setDayOffset] = useState(initialDayOffset);
  const [manualTime, setManualTime] = useState('');
  const [manualError, setManualError] = useState<string | null>(null);
  const day = addDays(new Date(), dayOffset);

  const availability = useQuery({
    queryKey: ['availability', providerId, dateKey(day), durationMinutes],
    queryFn: () => getAvailability(providerId as Uuid, dateKey(day), durationMinutes),
    enabled: !!providerId,
  });

  const useManualTime = () => {
    const combined = combineDayAndTime(day, manualTime);
    if (!combined) {
      setManualError('Escribe la hora como HH:MM, por ejemplo 14:30.');
      return;
    }
    setManualError(null);
    onChange(combined.toISOString());
  };

  if (!providerId) {
    return <Body muted>Elige primero un profesional para ver sus horarios.</Body>;
  }

  return (
    <View style={{ gap: 8 }}>
      <Row style={{ justifyContent: 'space-between' }}>
        <Button title="◀" variant="ghost" onPress={() => setDayOffset((o) => o - 1)} />
        <Body style={{ fontWeight: '700' }}>{dayLabel(dayOffset, day)}</Body>
        <Button title="▶" variant="ghost" onPress={() => setDayOffset((o) => o + 1)} />
      </Row>
      <Row>
        {dayOffset !== 0 ? <Button title="Hoy" variant="secondary" onPress={() => setDayOffset(0)} /> : null}
        {dayOffset !== 1 ? <Button title="Mañana" variant="secondary" onPress={() => setDayOffset(1)} /> : null}
      </Row>

      {availability.isLoading ? <Loading label="Buscando horarios…" /> : null}
      {availability.error ? <ErrorBox message={errorMessage(availability.error)} onRetry={() => void availability.refetch()} /> : null}
      {availability.data && availability.data.slots.length === 0 ? (
        <Body muted>Sin horarios libres ese día (fuera de horario laboral o todo ocupado).</Body>
      ) : null}
      <Row>
        {(availability.data?.slots ?? []).map((slot) => (
          <Button
            key={slot}
            title={hhmm(slot)}
            variant={value === slot ? 'secondary' : 'ghost'}
            onPress={() => onChange(slot)}
          />
        ))}
      </Row>

      <Body muted>¿Otra hora? Escríbela:</Body>
      <Row>
        <TextInput
          value={manualTime}
          onChangeText={setManualTime}
          placeholder="HH:MM"
          placeholderTextColor={t.colors.textMuted}
          keyboardType="numbers-and-punctuation"
          accessibilityLabel="Hora manual"
          style={{ minHeight: 48, minWidth: 90, borderWidth: 1, borderColor: t.colors.border, borderRadius: t.radius, paddingHorizontal: 12, color: t.colors.text, fontSize: 16 }}
        />
        <Button title="Usar esta hora" variant="secondary" onPress={useManualTime} disabled={!manualTime} />
      </Row>
      {manualError ? <ErrorBox message={manualError} /> : null}

      {value ? (
        <Body style={{ fontWeight: '700' }}>
          Elegido: {new Date(value).toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long' })} a las {hhmm(value)}
        </Body>
      ) : null}
    </View>
  );
}
