import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, RefreshControl, ScrollView, View } from 'react-native';

import { errorMessage } from '@/api/client';
import { addDays, dateKey, dayRange, hhmm } from '@/api/dates';
import { getCurrentEncounter, listAppointments, setAppointmentStatus, startEncounter } from '@/api/endpoints';
import type { Appointment } from '@/api/types';
import { AppointmentActionsSheet } from '@/agenda/AppointmentActionsSheet';
import { Badge, Body, Button, Card, Empty, ErrorBox, Loading, Row, Title } from '@/components/ui';
import { guardSingleOpenEncounter } from '@/encounters/openEncounterGuard';
import { hasPermission } from '@/store/session';
import { STATUS_COLORS, useTheme } from '@/theme/theme';

const STATUS_LABEL: Record<string, string> = {
  RESERVADA: 'Reservada',
  CONFIRMADA: 'Confirmada',
  EN_SALA: 'En sala',
  EN_ATENCION: 'En atención',
  TERMINADA: 'Terminada',
  CANCELADA: 'Cancelada',
  NO_SHOW: 'No asistió',
  REPROGRAMADA: 'Reprogramada',
};

export default function AgendaScreen() {
  const t = useTheme();
  const qc = useQueryClient();
  const params = useLocalSearchParams<{ dia?: string }>();
  const [offset, setOffset] = useState(0);
  const [actionsFor, setActionsFor] = useState<Appointment | null>(null);

  // Dentia puede abrir la agenda de mañana con /?dia=1
  useEffect(() => {
    if (params.dia !== undefined) setOffset(Number(params.dia) || 0);
  }, [params.dia]);

  const range = dayRange(offset);
  const q = useQuery({
    queryKey: ['appointments', range.from],
    queryFn: () => listAppointments(range.from, range.to),
    refetchInterval: 60_000, // la recepción mueve citas todo el día
  });

  const checkIn = useMutation({
    mutationFn: (a: Appointment) => setAppointmentStatus(a.id, 'EN_SALA'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['appointments'] }),
  });

  const start = useMutation({
    mutationFn: (a: Appointment) => startEncounter(a.id),
    onSuccess: (enc, a) => {
      void qc.invalidateQueries({ queryKey: ['appointments'] });
      void qc.invalidateQueries({ queryKey: ['encounters', 'current'] });
      router.push({ pathname: '/atencion/[id]', params: { id: enc.id, patientId: a.patient_id, patientName: a.patient_full_name } });
    },
  });

  // M4 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3, R2 forma 1): si la cita sigue
  // "Agendada"/"Confirmada" (no pasó por "Llegó"), confirma antes de iniciar en un
  // solo paso; y solo una consulta abierta por profesional (B10).
  const currentEncounter = useQuery({
    queryKey: ['encounters', 'current'],
    queryFn: getCurrentEncounter,
    enabled: hasPermission('records.write'),
  });

  const confirmStart = (a: Appointment) => {
    const proceed = () => guardSingleOpenEncounter(currentEncounter.data, () => start.mutate(a));
    if (a.status === 'EN_SALA') {
      proceed();
      return;
    }
    Alert.alert('Iniciar atención', '¿El paciente ya está en el sillón?', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Sí, iniciar', onPress: proceed },
    ]);
  };

  const canAgenda = hasPermission('agenda.write');
  const canStart = hasPermission('records.write');
  const items = (q.data ?? []).filter((a) => a.status !== 'REPROGRAMADA').sort((a, b) => a.starts_at.localeCompare(b.starts_at));

  // M3: vista semana simple (7 chips tocables) — no hay una cuadrícula de horas como
  // en la web todavía, pero permite ver y saltar a cualquier día de la semana sin
  // tocar ◀/▶ repetidas veces.
  const today = addDays(new Date(), 0); // medianoche local de hoy
  const weekStart = addDays(today, -((today.getDay() + 6) % 7)); // lunes de esta semana

  return (
    <>
    <ScrollView
      style={{ backgroundColor: t.colors.background }}
      contentContainerStyle={{ padding: 16, gap: 12 }}
      refreshControl={<RefreshControl refreshing={q.isRefetching} onRefresh={() => void q.refetch()} />}
    >
      {hasPermission('agenda.write') ? (
        <Button title="+ Nueva cita" onPress={() => router.push('/cita/nueva')} />
      ) : null}

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
        {Array.from({ length: 7 }, (_, i) => {
          const day = addDays(weekStart, i);
          const dayOffset = Math.round((day.getTime() - today.getTime()) / 86_400_000);
          return (
            <Button
              key={dateKey(day)}
              title={day.toLocaleDateString('es-MX', { weekday: 'short', day: 'numeric' })}
              variant={dayOffset === offset ? 'secondary' : 'ghost'}
              onPress={() => setOffset(dayOffset)}
            />
          );
        })}
      </ScrollView>

      <Row style={{ justifyContent: 'space-between' }}>
        <Button title="◀" variant="ghost" onPress={() => setOffset((o) => o - 1)} />
        <Title>{range.label}</Title>
        <Button title="▶" variant="ghost" onPress={() => setOffset((o) => o + 1)} />
      </Row>
      {offset !== 0 ? <Button title="Volver a hoy" variant="secondary" onPress={() => setOffset(0)} /> : null}

      {q.isLoading ? <Loading /> : null}
      {q.error ? <ErrorBox message={errorMessage(q.error)} onRetry={() => void q.refetch()} /> : null}
      {checkIn.error ? <ErrorBox message={errorMessage(checkIn.error)} /> : null}
      {start.error ? <ErrorBox message={errorMessage(start.error)} /> : null}
      {q.data && items.length === 0 ? <Empty>No hay citas para este día.</Empty> : null}

      {items.map((a) => {
        const active = a.status === 'RESERVADA' || a.status === 'CONFIRMADA' || a.status === 'EN_SALA';
        return (
          <Card key={a.id} onPress={() => router.push({ pathname: '/paciente/[id]', params: { id: a.patient_id } })}>
            <Row style={{ justifyContent: 'space-between' }}>
              <Body style={{ fontWeight: '800', fontSize: 18 }}>
                {hhmm(a.starts_at)}–{hhmm(a.ends_at)}
              </Body>
              <Row>
                <Badge label={STATUS_LABEL[a.status] ?? a.status} color={STATUS_COLORS[a.status] ?? t.colors.textMuted} />
                <Button title="Más" variant="ghost" accessibilityHint="Más acciones de esta cita" onPress={() => setActionsFor(a)} />
              </Row>
            </Row>
            <Body style={{ fontWeight: '600' }}>{a.patient_full_name}</Body>
            {a.appointment_type || a.provider_full_name ? (
              <Body muted>{[a.appointment_type, a.provider_full_name].filter(Boolean).join(' · ')}</Body>
            ) : null}
            {active && offset === 0 ? (
              <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
                {canAgenda && a.status !== 'EN_SALA' ? (
                  <Button title="Llegó" variant="secondary" onPress={() => checkIn.mutate(a)} loading={checkIn.isPending && checkIn.variables?.id === a.id} />
                ) : null}
                {canStart ? (
                  <Button title="Iniciar atención" onPress={() => confirmStart(a)} loading={start.isPending && start.variables?.id === a.id} />
                ) : (
                  <Body muted>Lo inicia el odontólogo.</Body>
                )}
              </View>
            ) : null}
          </Card>
        );
      })}
    </ScrollView>
    <AppointmentActionsSheet appointment={actionsFor} onClose={() => setActionsFor(null)} />
    </>
  );
}
