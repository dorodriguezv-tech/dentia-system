import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as ImagePicker from 'expo-image-picker';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useMemo, useState } from 'react';
import { Alert, Modal, Pressable, ScrollView, Text, View } from 'react-native';

import { errorMessage } from '@/api/client';
import {
  createEncounter,
  createToothFinding,
  getCurrentEncounter,
  getOdontogram,
  getPatientEncounters,
  getPatientSummary,
  uploadPatientImages,
} from '@/api/endpoints';
import type { Surface } from '@/api/types';
import { FINDING_CATALOG, Odontogram } from '@/components/Odontogram';
import { AlertBar, Body, Button, Card, ErrorBox, Loading, Row, Screen, Title } from '@/components/ui';
import { guardSingleOpenEncounter } from '@/encounters/openEncounterGuard';
import { hasPermission } from '@/store/session';
import { FINDING_COLORS, useTheme } from '@/theme/theme';

export default function PacienteScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const t = useTheme();
  const qc = useQueryClient();
  const [sel, setSel] = useState<{ tooth: number; surface: Surface | null } | null>(null);

  const summary = useQuery({ queryKey: ['patient', id], queryFn: () => getPatientSummary(id) });
  const odo = useQuery({ queryKey: ['odontogram', id], queryFn: () => getOdontogram(id), enabled: hasPermission('odontogram.read') });
  const encounters = useQuery({ queryKey: ['encounters', id], queryFn: () => getPatientEncounters(id) });

  // Un hallazgo siempre va ligado a una atención (regla 6): usamos la más reciente de hoy
  const todayEncounter = useMemo(() => {
    const today = new Date().toDateString();
    return (encounters.data ?? [])
      .filter((e) => new Date(e.started_at).toDateString() === today)
      .sort((a, b) => b.started_at.localeCompare(a.started_at))[0];
  }, [encounters.data]);

  const canWriteOdo = hasPermission('odontogram.write') && !!todayEncounter;
  const canUploadPhoto = hasPermission('imaging.write') && !!todayEncounter;

  // M4 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3, R2 forma 2): iniciar atención sin
  // cita (urgencia / paciente que llegó sin agendar).
  const currentEncounter = useQuery({
    queryKey: ['encounters', 'current'],
    queryFn: getCurrentEncounter,
    enabled: hasPermission('records.write'),
  });
  const startEncounterNow = useMutation({
    mutationFn: () => createEncounter({ patient_id: id }),
    onSuccess: (enc) => {
      void qc.invalidateQueries({ queryKey: ['encounters', 'current'] });
      router.push({ pathname: '/atencion/[id]', params: { id: enc.id, patientId: id, patientName: p.full_name } });
    },
  });

  const addFinding = useMutation({
    mutationFn: (finding_code: string) =>
      createToothFinding({
        patient_id: id,
        encounter_id: todayEncounter!.id,
        tooth_fdi: sel!.tooth,
        surface: FINDING_CATALOG.find((f) => f.code === finding_code)?.wholeTooth ? null : sel!.surface,
        finding_code,
      }),
    onSuccess: () => {
      setSel(null);
      void qc.invalidateQueries({ queryKey: ['odontogram', id] });
    },
  });

  const photo = useMutation({
    mutationFn: async () => {
      if (!todayEncounter) throw new Error('Inicia la atención de hoy desde la Agenda para poder guardar la foto.');
      const perm = await ImagePicker.requestCameraPermissionsAsync();
      if (!perm.granted) throw new Error('Sin permiso de cámara. Actívalo en Ajustes del teléfono.');
      const shot = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.85, exif: false });
      if (shot.canceled || !shot.assets[0]) return null;
      const a = shot.assets[0];
      return uploadPatientImages(
        id,
        [{ uri: a.uri, name: a.fileName ?? `foto_${Date.now()}.jpg`, mimeType: a.mimeType ?? 'image/jpeg' }],
        { study_type: 'intraoral', encounter_id: todayEncounter.id, tooth_fdi: sel?.tooth },
      );
    },
    onSuccess: (r) => {
      if (r) Alert.alert('Fotografía guardada', 'Se agregó a la pestaña Imágenes del expediente.');
    },
  });

  if (summary.isLoading) return <Screen><Loading /></Screen>;
  if (summary.error || !summary.data) return <Screen><ErrorBox message={errorMessage(summary.error)} onRetry={() => void summary.refetch()} /></Screen>;
  const p = summary.data;

  return (
    <Screen>
      <Stack.Screen options={{ title: p.full_name }} />
      {/* Encabezado persistente con alertas (igual que la web) */}
      <Card>
        <Title>{p.full_name}</Title>
        <Body muted>
          Exp. {p.expediente_number} · {p.age} años
        </Body>
      </Card>
      <AlertBar alerts={p.alerts} />

      <Row>
        {hasPermission('records.write') ? (
          todayEncounter ? (
            <Button
              title="Dictar con IA"
              onPress={() => router.push({ pathname: '/atencion/[id]', params: { id: todayEncounter.id, patientId: id, patientName: p.full_name } })}
            />
          ) : (
            <Button
              title="Iniciar atención"
              onPress={() => guardSingleOpenEncounter(currentEncounter.data, () => startEncounterNow.mutate())}
              loading={startEncounterNow.isPending}
            />
          )
        ) : null}
        {canUploadPhoto ? <Button title="Tomar foto" variant="secondary" onPress={() => photo.mutate()} loading={photo.isPending} /> : null}
      </Row>
      {startEncounterNow.error ? <ErrorBox message={errorMessage(startEncounterNow.error)} /> : null}
      {photo.error ? <ErrorBox message={errorMessage(photo.error)} /> : null}

      <Title>Odontograma</Title>
      {!todayEncounter ? (
        <Body muted>Solo lectura: para registrar hallazgos, inicia la atención de hoy desde la Agenda.</Body>
      ) : null}
      {odo.isLoading ? <Loading /> : null}
      {odo.error ? <ErrorBox message={errorMessage(odo.error)} /> : null}
      {odo.data ? <Odontogram findings={odo.data} selected={sel} onSelect={(tooth, surface) => setSel({ tooth, surface })} /> : null}

      <FindingSheet
        visible={!!sel}
        title={sel ? `Pieza ${sel.tooth}${sel.surface ? ` · superficie ${sel.surface}` : ' · pieza completa'}` : ''}
        canWrite={canWriteOdo}
        history={(odo.data ?? []).filter((f) => f.tooth_fdi === sel?.tooth)}
        onPick={(code) => addFinding.mutate(code)}
        loading={addFinding.isPending}
        error={addFinding.error ? errorMessage(addFinding.error) : null}
        onClose={() => setSel(null)}
      />
      <View style={{ height: t.space(8) }} />
    </Screen>
  );
}

function FindingSheet(props: {
  visible: boolean;
  title: string;
  canWrite: boolean;
  history: { id: string; finding_code: string; surface: string | null; kind: string; origin: string; created_at: string }[];
  onPick: (code: string) => void;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}) {
  const t = useTheme();
  return (
    <Modal visible={props.visible} transparent animationType="slide" onRequestClose={props.onClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.35)' }} onPress={props.onClose} accessibilityLabel="Cerrar" />
      <View style={{ backgroundColor: t.colors.surface, padding: 16, gap: 12, borderTopLeftRadius: 16, borderTopRightRadius: 16, maxHeight: '75%' }}>
        <Title>{props.title}</Title>
        <ScrollView contentContainerStyle={{ gap: 12 }}>
          {props.canWrite ? (
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
              {FINDING_CATALOG.map((f) => (
                <Pressable
                  key={f.code}
                  disabled={props.loading}
                  onPress={() => props.onPick(f.code)}
                  accessibilityRole="button"
                  style={{ minHeight: 48, paddingHorizontal: 12, borderRadius: 10, justifyContent: 'center', borderWidth: 2, borderColor: FINDING_COLORS[f.code] ?? t.colors.border }}
                >
                  <Text style={{ color: t.colors.text, fontWeight: '600' }}>{f.label}</Text>
                </Pressable>
              ))}
            </View>
          ) : (
            <Body muted>Sin atención abierta hoy o sin permiso: solo puedes consultar.</Body>
          )}
          {props.error ? <ErrorBox message={props.error} /> : null}
          <Body style={{ fontWeight: '700' }}>Historial de la pieza</Body>
          {props.history.length === 0 ? <Body muted>Sin registros.</Body> : null}
          {props.history.map((h) => (
            <Body key={h.id} muted>
              {new Date(h.created_at).toLocaleDateString('es-MX')} · {h.finding_code.toLowerCase()} {h.surface ?? '(pieza)'} · {h.kind}
              {h.origin === 'AI_ASSISTED' ? ' · IA' : ''}
            </Body>
          ))}
        </ScrollView>
        <Button title="Cerrar" variant="ghost" onPress={props.onClose} />
      </View>
    </Modal>
  );
}
