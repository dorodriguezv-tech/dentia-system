import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { RefreshControl, ScrollView, View } from 'react-native';

import { errorMessage } from '@/api/client';
import { dayRange, hhmm } from '@/api/dates';
import { listAppointments, setAppointmentStatus, startEncounter } from '@/api/endpoints';
import type { Appointment } from '@/api/types';
import { Badge, Body, Button, Card, Empty, ErrorBox, Loading, Row, Title } from '@/components/ui';
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
      router.push({ pathname: '/atencion/[id]', params: { id: enc.id, patientId: a.patient_id, patientName: a.patient_full_name } });
    },
  });

  const canAgenda = hasPermission('agenda.write');
  const canStart = hasPermission('records.write');
  const items = (q.data ?? []).filter((a) => a.status !== 'REPROGRAMADA').sort((a, b) => a.starts_at.localeCompare(b.starts_at));

  return (
    <ScrollView
      style={{ backgroundColor: t.colors.background }}
      contentContainerStyle={{ padding: 16, gap: 12 }}
      refreshControl={<RefreshControl refreshing={q.isRefetching} onRefresh={() => void q.refetch()} />}
    >
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
              <Badge label={STATUS_LABEL[a.status] ?? a.status} color={STATUS_COLORS[a.status] ?? t.colors.textMuted} />
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
                  <Button title="Iniciar atención" onPress={() => start.mutate(a)} loading={start.isPending && start.variables?.id === a.id} />
                ) : null}
              </View>
            ) : null}
          </Card>
        );
      })}
    </ScrollView>
  );
}
