import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { ScrollView, TextInput, View } from 'react-native';

import { errorMessage } from '@/api/client';
import { addDays, combineDayAndTime, dateKey, dayLabel, hhmm } from '@/api/dates';
import { getDaySchedule } from '@/api/endpoints';
import type { Uuid } from '@/api/types';
import { Body, Button, ErrorBox, Loading, Row } from '@/components/ui';
import { useTheme } from '@/theme/theme';

/** Dos semanas hacia adelante, como franja de días (misma idea que la Agenda) para
 * explorar varios días a la vez en vez de ir de uno en uno con ◀ / ▶. Se reporta
 * como mejora al probar en un teléfono: pedía algo "como el calendario web" para
 * elegir un horario libre tecleando menos. */
const DAY_STRIP_LENGTH = 14;

/**
 * M3 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3): elige día y hora para una cita nueva o
 * una reprogramación, con la agenda real del profesional que calcula el backend
 * (GET /appointments/day-schedule) — nunca inventada en el teléfono. No hay un
 * selector de fecha nativo instalado (evita agregar un paquete con código nativo a
 * mitad de esta tarea); el día se elige de una franja de 14 días o con ◀ / ▶ para ir
 * más lejos, y la hora de una cuadrícula de horas completas (disponibles y
 * ocupadas, igual que la agenda del dentista) o escribiéndola a mano para algo
 * que no caiga en una hora en punto. Reporte al probar en un teléfono real: antes
 * solo se mostraban 3 huecos sueltos en pasos de 15 minutos, sin ver lo ocupado.
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

  const schedule = useQuery({
    queryKey: ['day-schedule', providerId, dateKey(day), durationMinutes],
    queryFn: () => getDaySchedule(providerId as Uuid, dateKey(day), durationMinutes),
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
        <Button title="◀" variant="ghost" accessibilityHint="Día anterior" onPress={() => setDayOffset((o) => o - 1)} />
        <Body style={{ fontWeight: '700' }}>{dayLabel(dayOffset, day)}</Body>
        <Button title="▶" variant="ghost" accessibilityHint="Día siguiente" onPress={() => setDayOffset((o) => o + 1)} />
      </Row>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
        {Array.from({ length: DAY_STRIP_LENGTH }, (_, i) => {
          const chipDay = addDays(new Date(), i);
          const label = i === 0 ? 'Hoy' : i === 1 ? 'Mañana' : chipDay.toLocaleDateString('es-MX', { weekday: 'short', day: 'numeric' });
          return <Button key={i} title={label} variant={dayOffset === i ? 'secondary' : 'ghost'} onPress={() => setDayOffset(i)} />;
        })}
      </ScrollView>

      {schedule.isLoading ? <Loading label="Buscando horarios…" /> : null}
      {schedule.error ? <ErrorBox message={errorMessage(schedule.error)} onRetry={() => void schedule.refetch()} /> : null}
      {schedule.data && schedule.data.slots.length === 0 ? (
        <Body muted>Sin horario laboral ese día para este profesional.</Body>
      ) : null}
      <Row>
        {(schedule.data?.slots ?? []).map((slot) => (
          <Button
            key={slot.starts_at}
            title={slot.available ? hhmm(slot.starts_at) : `${hhmm(slot.starts_at)} · Ocupado`}
            variant={value === slot.starts_at ? 'secondary' : 'ghost'}
            disabled={!slot.available}
            accessibilityHint={slot.available ? undefined : 'Este horario ya está ocupado'}
            onPress={() => onChange(slot.starts_at)}
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
