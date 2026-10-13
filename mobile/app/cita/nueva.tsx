import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, Linking, TextInput, View } from 'react-native';

import { ApiError, errorMessage } from '@/api/client';
import { createAppointment, createPatientQuick, getPatient, listAppointmentTypes, listProviders, searchPatients } from '@/api/endpoints';
import type { PatientListItem } from '@/api/types';
import { SlotPicker } from '@/agenda/SlotPicker';
import { Body, Button, Card, ErrorBox, Field, Row, Screen, Title } from '@/components/ui';
import { hasPermission, useSession } from '@/store/session';
import { useTheme } from '@/theme/theme';

/**
 * M3 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3, R1): "+ Nueva cita". También sirve
 * como pantalla de "próxima cita" de M7 (R7) cuando llega con `suggestedOffsetDays`
 * y/o `planHint` (desde "Cerrar consulta") — mismos endpoints, un contexto arriba
 * y la fecha sugerida en vez de hoy; no es una pantalla separada.
 *
 * No incluye el gabinete (opcional en el backend, decisión administrativa que la
 * web sí ofrece pero que no está en el alcance de esta pantalla — se agenda sin
 * gabinete y se asigna después desde la web si la clínica lo usa) ni la
 * preselección por tocar un hueco libre en una cuadrícula (no existe esa
 * cuadrícula en el teléfono todavía).
 */
export default function NuevaCitaScreen() {
  const params = useLocalSearchParams<{
    patientId?: string;
    patientName?: string;
    suggestedOffsetDays?: string;
    planHint?: string;
  }>();
  const t = useTheme();
  const qc = useQueryClient();
  const me = useSession((s) => s.me);

  const [patient, setPatient] = useState<{ id: string; full_name: string } | null>(
    params.patientId && params.patientName ? { id: params.patientId, full_name: params.patientName } : null,
  );
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<PatientListItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [showQuickCreate, setShowQuickCreate] = useState(false);
  const [quickFirst, setQuickFirst] = useState('');
  const [quickLastP, setQuickLastP] = useState('');
  const [quickLastM, setQuickLastM] = useState('');
  const [quickPhone, setQuickPhone] = useState('');
  const [quickDob, setQuickDob] = useState('');

  const [providerId, setProviderId] = useState<string | null>(null);
  const [appointmentType, setAppointmentType] = useState<string | null>(null);
  const [startsAt, setStartsAt] = useState<string | null>(null);
  const [notes, setNotes] = useState('');

  const providers = useQuery({ queryKey: ['providers'], queryFn: listProviders });
  const types = useQuery({ queryKey: ['appointment-types'], queryFn: listAppointmentTypes });

  useEffect(() => {
    if (providerId || !providers.data?.length) return;
    const mine = providers.data.find((p) => p.user_id === me?.id);
    setProviderId((mine ?? providers.data[0])?.id ?? null);
  }, [providers.data, providerId, me?.id]);

  useEffect(() => {
    if (appointmentType || !types.data?.length) return;
    setAppointmentType(types.data[0]?.code ?? null);
  }, [types.data, appointmentType]);

  const duration = types.data?.find((t) => t.code === appointmentType)?.default_minutes ?? 30;

  const runSearch = async (value: string) => {
    setQuery(value);
    setPatient(null);
    if (value.trim().length < 2) {
      setResults([]);
      return;
    }
    setSearching(true);
    try {
      setResults(await searchPatients(value));
    } finally {
      setSearching(false);
    }
  };

  const quickCreate = useMutation({
    mutationFn: () =>
      createPatientQuick({
        first_name: quickFirst.trim(),
        last_name_paternal: quickLastP.trim(),
        last_name_maternal: quickLastM.trim() || undefined,
        phone: quickPhone.trim() || undefined,
        date_of_birth: quickDob.trim(),
      }),
    onSuccess: (p) => {
      setPatient({ id: p.id, full_name: p.full_name });
      setShowQuickCreate(false);
    },
  });

  const create = useMutation({
    mutationFn: () =>
      createAppointment({
        patient_id: patient!.id,
        provider_id: providerId!,
        appointment_type: appointmentType!,
        starts_at: startsAt!,
        notes: notes.trim() || null,
      }),
    onSuccess: async (appt) => {
      void qc.invalidateQueries({ queryKey: ['appointments'] });
      const when = new Date(appt.starts_at).toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long' });
      const whenLabel = `${when}, ${new Date(appt.starts_at).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}`;
      let phone: string | null = null;
      try {
        phone = (await getPatient(appt.patient_id)).phone;
      } catch {
        /* si falla, se omite el botón de WhatsApp, no es bloqueante */
      }
      if (phone) {
        Alert.alert(`Cita creada: ${whenLabel}`, undefined, [
          {
            text: 'Enviar recordatorio por WhatsApp',
            onPress: () => {
              void Linking.openURL(`https://wa.me/${phone!.replace(/\D/g, '')}`);
              router.back();
            },
          },
          { text: 'Listo', style: 'cancel', onPress: () => router.back() },
        ]);
      } else {
        router.back();
      }
    },
  });

  const conflict = create.error instanceof ApiError && create.error.status === 409;
  const canSubmit = !!patient && !!providerId && !!appointmentType && !!startsAt && !create.isPending;

  return (
    <Screen>
      <Stack.Screen options={{ title: 'Nueva cita' }} />
      {params.planHint ? (
        <Card>
          <Body style={{ fontWeight: '700' }}>Siguiente cita sugerida</Body>
          <Body muted>{params.planHint}</Body>
        </Card>
      ) : null}
      <Card>
        <Title>Paciente</Title>
        {patient ? (
          <Row style={{ justifyContent: 'space-between' }}>
            <Body style={{ fontWeight: '700' }}>{patient.full_name}</Body>
            <Button title="Cambiar" variant="ghost" onPress={() => setPatient(null)} />
          </Row>
        ) : (
          <>
            <Field label="Buscar por nombre" value={query} onChangeText={(v) => void runSearch(v)} autoCapitalize="words" />
            {searching ? <Body muted>Buscando…</Body> : null}
            {results.map((p) => (
              <Button key={p.id} title={`${p.full_name} · exp. ${p.expediente_number}`} variant="ghost" onPress={() => setPatient(p)} />
            ))}
            {query.trim().length >= 2 && !searching && results.length === 0 ? (
              <Body muted>No se encontró ningún paciente con ese nombre.</Body>
            ) : null}
            {hasPermission('patients.write') ? (
              showQuickCreate ? (
                <View style={{ gap: 8 }}>
                  <Field label="Nombre(s)" value={quickFirst} onChangeText={setQuickFirst} autoCapitalize="words" />
                  <Field label="Apellido paterno" value={quickLastP} onChangeText={setQuickLastP} autoCapitalize="words" />
                  <Field label="Apellido materno (opcional)" value={quickLastM} onChangeText={setQuickLastM} autoCapitalize="words" />
                  <Field label="Teléfono (opcional)" value={quickPhone} onChangeText={setQuickPhone} keyboardType="phone-pad" />
                  <Field label="Fecha de nacimiento (AAAA-MM-DD)" value={quickDob} onChangeText={setQuickDob} keyboardType="numbers-and-punctuation" />
                  {quickCreate.error ? <ErrorBox message={errorMessage(quickCreate.error)} /> : null}
                  <Row>
                    <Button
                      title="Crear paciente"
                      onPress={() => quickCreate.mutate()}
                      loading={quickCreate.isPending}
                      disabled={!quickFirst.trim() || !quickLastP.trim() || !quickDob.trim()}
                    />
                    <Button title="Cancelar" variant="ghost" onPress={() => setShowQuickCreate(false)} />
                  </Row>
                </View>
              ) : (
                <Button title="+ Crear paciente rápido" variant="secondary" onPress={() => setShowQuickCreate(true)} />
              )
            ) : null}
          </>
        )}
      </Card>

      <Card>
        <Title>Profesional</Title>
        {(providers.data ?? []).map((p) => (
          <Button key={p.id} title={p.full_name} variant={providerId === p.id ? 'secondary' : 'ghost'} onPress={() => setProviderId(p.id)} />
        ))}
      </Card>

      <Card>
        <Title>Tipo de cita</Title>
        {(types.data ?? []).map((ty) => (
          <Button
            key={ty.code}
            title={`${ty.name} (${ty.default_minutes} min)`}
            variant={appointmentType === ty.code ? 'secondary' : 'ghost'}
            onPress={() => setAppointmentType(ty.code)}
          />
        ))}
      </Card>

      <Card>
        <Title>Fecha y hora</Title>
        <SlotPicker
          providerId={providerId}
          durationMinutes={duration}
          value={startsAt}
          onChange={setStartsAt}
          initialDayOffset={params.suggestedOffsetDays ? Number(params.suggestedOffsetDays) || 0 : 0}
        />
      </Card>

      <Card>
        <Title>Motivo / notas para recepción</Title>
        <TextInput
          multiline
          value={notes}
          onChangeText={setNotes}
          placeholder="Opcional"
          accessibilityLabel="Notas"
          placeholderTextColor={t.colors.textMuted}
          style={{ minHeight: 80, textAlignVertical: 'top', borderWidth: 1, borderColor: t.colors.border, borderRadius: t.radius, padding: 12, color: t.colors.text, fontSize: 16 }}
        />
      </Card>

      {create.error ? (
        <ErrorBox
          message={conflict ? 'Ese horario ya está ocupado. Elige otro de la lista.' : errorMessage(create.error)}
          onRetry={conflict ? undefined : () => create.mutate()}
        />
      ) : null}

      <Button title="Agendar cita" big onPress={() => create.mutate()} disabled={!canSubmit} loading={create.isPending} />
    </Screen>
  );
}
