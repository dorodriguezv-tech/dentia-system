import { useMutation, useQueryClient } from '@tanstack/react-query';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';

import { ApiError, errorMessage } from '@/api/client';
import { hhmm } from '@/api/dates';
import { rescheduleAppointment } from '@/api/endpoints';
import { SlotPicker } from '@/agenda/SlotPicker';
import { Body, Button, Card, ErrorBox, Field, Screen, Title } from '@/components/ui';

export default function ReprogramarScreen() {
  const params = useLocalSearchParams<{
    id: string;
    patientName: string;
    providerId: string;
    startsAt: string;
    endsAt: string;
  }>();
  const qc = useQueryClient();
  const [startsAt, setStartsAt] = useState<string | null>(null);
  const [reason, setReason] = useState('');

  const durationMinutes = Math.max(
    5,
    Math.round((new Date(params.endsAt).getTime() - new Date(params.startsAt).getTime()) / 60_000),
  );

  const reschedule = useMutation({
    mutationFn: () => rescheduleAppointment(params.id, { starts_at: startsAt!, reason: reason.trim() || null }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['appointments'] });
      router.back();
    },
  });

  const conflict = reschedule.error instanceof ApiError && reschedule.error.status === 409;

  return (
    <Screen>
      <Stack.Screen options={{ title: 'Reprogramar cita' }} />
      <Card>
        <Title>{params.patientName}</Title>
        <Body muted>
          Hora actual: {hhmm(params.startsAt)}–{hhmm(params.endsAt)}
        </Body>
      </Card>

      <Card>
        <Title>Nueva fecha y hora</Title>
        <SlotPicker providerId={params.providerId} durationMinutes={durationMinutes} value={startsAt} onChange={setStartsAt} />
      </Card>

      <Card>
        <Title>Motivo (opcional)</Title>
        <Field label="Motivo del cambio" value={reason} onChangeText={setReason} />
      </Card>

      {reschedule.error ? (
        <ErrorBox message={conflict ? 'Ese horario ya está ocupado. Elige otro de la lista.' : errorMessage(reschedule.error)} />
      ) : null}

      <Button title="Confirmar reprogramación" big onPress={() => reschedule.mutate()} disabled={!startsAt || reschedule.isPending} loading={reschedule.isPending} />
    </Screen>
  );
}
