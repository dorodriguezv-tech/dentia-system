import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as ImagePicker from 'expo-image-picker';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, KeyboardAvoidingView, Linking, Modal, Platform, Pressable, ScrollView, Text, TextInput, View } from 'react-native';

import { errorMessage } from '@/api/client';
import {
  annulToothFinding,
  createEncounter,
  createToothFinding,
  getCurrentEncounter,
  getOdontogram,
  getPatient,
  getPatientEncounters,
  getPatientSummary,
  getToothHistory,
  listOdontogramFindings,
  uploadPatientImages,
} from '@/api/endpoints';
import type { FindingKind, OdontogramFindingCatalogItem, Surface, ToothFindingHistoryEntry } from '@/api/types';
import { applicableSurfaces, Odontogram } from '@/components/Odontogram';
import { AlertBar, Body, Button, Card, ErrorBox, Loading, Row, Screen, Title } from '@/components/ui';
import { telUrl } from '@/contact/links';
import { guardSingleOpenEncounter } from '@/encounters/openEncounterGuard';
import { hasPermission } from '@/store/session';
import { FINDING_COLORS, useTheme } from '@/theme/theme';

const KIND_LABEL: Record<FindingKind, string> = { EXISTING: 'Diagnóstico', PLANNED: 'Planificado', PERFORMED: 'Realizado' };
const SURFACE_LABEL: Record<Surface, string> = { O: 'Oclusal', I: 'Incisal', M: 'Mesial', D: 'Distal', V: 'Vestibular', L: 'Lingual', P: 'Palatina' };

export default function PacienteScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const t = useTheme();
  const qc = useQueryClient();
  const [sel, setSel] = useState<{ tooth: number; surface: Surface | null } | null>(null);
  const [undo, setUndo] = useState<{ ids: string[]; label: string } | null>(null);
  const undoTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const summary = useQuery({ queryKey: ['patient', id], queryFn: () => getPatientSummary(id) });
  const odo = useQuery({ queryKey: ['odontogram', id], queryFn: () => getOdontogram(id), enabled: hasPermission('odontogram.read') });
  const encounters = useQuery({ queryKey: ['encounters', id], queryFn: () => getPatientEncounters(id) });
  // M8: acción rápida "Llamar" en la ficha.
  const patientDetail = useQuery({ queryKey: ['patient-detail', id], queryFn: () => getPatient(id) });

  // Un hallazgo siempre va ligado a una atención (regla 6): usamos la más reciente de hoy
  const todayEncounter = useMemo(() => {
    const today = new Date().toDateString();
    return (encounters.data ?? [])
      .filter((e) => new Date(e.started_at).toDateString() === today)
      .sort((a, b) => b.started_at.localeCompare(a.started_at))[0];
  }, [encounters.data]);

  const canWriteOdo = hasPermission('odontogram.write') && !!todayEncounter;
  const canUploadPhoto = hasPermission('imaging.write') && !!todayEncounter;

  // M4: iniciar atención sin cita (urgencia / paciente que llegó sin agendar).
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
  const startToEdit = () => guardSingleOpenEncounter(currentEncounter.data, () => startEncounterNow.mutate());

  // M5 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3): catálogo real de la sucursal, no una
  // lista fija en el teléfono (ver nota en theme.tsx sobre FINDING_COLORS).
  const catalog = useQuery({ queryKey: ['catalog', 'odontogram_finding'], queryFn: listOdontogramFindings, enabled: canWriteOdo });

  const history = useQuery({
    queryKey: ['tooth-history', id, sel?.tooth],
    queryFn: () => getToothHistory(id, sel!.tooth),
    enabled: !!sel,
  });

  const clearUndoTimer = () => {
    if (undoTimer.current) clearTimeout(undoTimer.current);
    undoTimer.current = null;
  };

  const addFinding = useMutation({
    mutationFn: async (args: { surfaces: Surface[]; wholeTooth: boolean; finding_code: string; kind: FindingKind; material: string | null }) => {
      const targets: (Surface | null)[] = args.wholeTooth ? [null] : args.surfaces;
      const created = await Promise.all(
        targets.map((surface) =>
          createToothFinding({
            patient_id: id,
            encounter_id: todayEncounter!.id,
            tooth_fdi: sel!.tooth,
            surface,
            finding_code: args.finding_code,
            kind: args.kind,
            material: args.material,
          }),
        ),
      );
      return created;
    },
    onSuccess: (created) => {
      setSel(null);
      void qc.invalidateQueries({ queryKey: ['odontogram', id] });
      void qc.invalidateQueries({ queryKey: ['tooth-history', id, sel?.tooth] });
      clearUndoTimer();
      setUndo({ ids: created.map((f) => f.id), label: created.length > 1 ? `${created.length} hallazgos guardados` : 'Hallazgo guardado' });
      undoTimer.current = setTimeout(() => setUndo(null), 5000);
    },
  });

  const annul = useMutation({
    mutationFn: ({ findingId, reason }: { findingId: string; reason: string }) => annulToothFinding(findingId, reason),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['odontogram', id] });
      void qc.invalidateQueries({ queryKey: ['tooth-history', id, sel?.tooth] });
    },
  });

  const undoNow = () => {
    if (!undo) return;
    clearUndoTimer();
    const ids = undo.ids;
    setUndo(null);
    void Promise.all(ids.map((findingId) => annulToothFinding(findingId, 'Deshecho (menos de 5 s después de capturarlo)'))).then(() => {
      void qc.invalidateQueries({ queryKey: ['odontogram', id] });
      void qc.invalidateQueries({ queryKey: ['tooth-history', id, sel?.tooth] });
    });
  };

  useEffect(() => clearUndoTimer, []);

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
            <Button title="Iniciar atención" onPress={startToEdit} loading={startEncounterNow.isPending} />
          )
        ) : null}
        {hasPermission('agenda.write') ? (
          <Button
            title="Nueva cita"
            variant="secondary"
            onPress={() => router.push({ pathname: '/cita/nueva', params: { patientId: id, patientName: p.full_name } })}
          />
        ) : null}
        {patientDetail.data?.phone ? (
          <Button
            title="Llamar"
            variant="secondary"
            onPress={() =>
              void Linking.openURL(telUrl(patientDetail.data!.phone!)).catch(() =>
                Alert.alert('No se pudo abrir el teléfono', 'Verifica que el número del paciente sea correcto.'),
              )
            }
          />
        ) : null}
        {canUploadPhoto ? <Button title="Tomar foto" variant="secondary" onPress={() => photo.mutate()} loading={photo.isPending} /> : null}
      </Row>
      {startEncounterNow.error ? <ErrorBox message={errorMessage(startEncounterNow.error)} /> : null}
      {photo.error ? <ErrorBox message={errorMessage(photo.error)} onRetry={() => photo.mutate()} /> : null}

      <Title>Odontograma</Title>
      {!todayEncounter ? (
        <View style={{ gap: 8 }}>
          <Body muted>Solo lectura: inicia la atención de hoy para registrar hallazgos.</Body>
          {hasPermission('records.write') ? (
            <Button title="Iniciar atención para editar" variant="secondary" onPress={startToEdit} loading={startEncounterNow.isPending} />
          ) : null}
        </View>
      ) : null}
      {odo.isLoading ? <Loading /> : null}
      {odo.error ? <ErrorBox message={errorMessage(odo.error)} onRetry={() => void odo.refetch()} /> : null}
      {odo.data ? <Odontogram findings={odo.data} selected={sel} onSelect={(tooth, surface) => setSel({ tooth, surface })} /> : null}

      <FindingSheet
        visible={!!sel}
        tooth={sel?.tooth ?? null}
        initialSurface={sel?.surface ?? null}
        canWrite={canWriteOdo}
        catalog={catalog.data ?? []}
        catalogLoading={catalog.isLoading}
        history={history.data ?? []}
        historyLoading={history.isLoading}
        onCreate={(args) => addFinding.mutate(args)}
        creating={addFinding.isPending}
        createError={addFinding.error ? errorMessage(addFinding.error) : null}
        onAnnul={(findingId, reason) => annul.mutate({ findingId, reason })}
        annulling={annul.isPending}
        annulError={annul.error ? errorMessage(annul.error) : null}
        onClose={() => setSel(null)}
      />

      {undo ? (
        <Row style={{ justifyContent: 'space-between', backgroundColor: t.colors.surface, borderWidth: 1, borderColor: t.colors.border, borderRadius: t.radius, padding: 12 }}>
          <Body>{undo.label}</Body>
          <Button title="Deshacer" variant="ghost" onPress={undoNow} />
        </Row>
      ) : null}

      <View style={{ height: t.space(8) }} />
    </Screen>
  );
}

function FindingSheet(props: {
  visible: boolean;
  tooth: number | null;
  initialSurface: Surface | null;
  canWrite: boolean;
  catalog: OdontogramFindingCatalogItem[];
  catalogLoading: boolean;
  history: ToothFindingHistoryEntry[];
  historyLoading: boolean;
  onCreate: (args: { surfaces: Surface[]; wholeTooth: boolean; finding_code: string; kind: FindingKind; material: string | null }) => void;
  creating: boolean;
  createError: string | null;
  onAnnul: (findingId: string, reason: string) => void;
  annulling: boolean;
  annulError: string | null;
  onClose: () => void;
}) {
  const t = useTheme();
  const [wholeTooth, setWholeTooth] = useState(false);
  const [surfaces, setSurfaces] = useState<Set<Surface>>(new Set());
  const [kind, setKind] = useState<FindingKind>('EXISTING');
  const [material, setMaterial] = useState('');
  const [search, setSearch] = useState('');
  const [annulTarget, setAnnulTarget] = useState<string | null>(null);
  const [annulReason, setAnnulReason] = useState('');

  useEffect(() => {
    if (!props.visible) return;
    setWholeTooth(props.initialSurface === null);
    setSurfaces(props.initialSurface ? new Set([props.initialSurface]) : new Set());
    setKind('EXISTING');
    setMaterial('');
    setSearch('');
    setAnnulTarget(null);
    setAnnulReason('');
  }, [props.visible, props.tooth, props.initialSurface]);

  if (props.tooth === null) return null;
  const tooth = props.tooth;
  const toothSurfaces = applicableSurfaces(tooth);

  const toggleSurface = (s: Surface) => {
    setWholeTooth(false);
    setSurfaces((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  };

  const selectWholeTooth = () => {
    setWholeTooth(true);
    setSurfaces(new Set());
  };

  const canSubmit = wholeTooth || surfaces.size > 0;
  const filteredCatalog = props.catalog.filter(
    (c) => !search.trim() || c.name.toLowerCase().includes(search.trim().toLowerCase()) || c.code.includes(search.trim().toLowerCase()),
  );

  return (
    <Modal visible={props.visible} transparent animationType="slide" onRequestClose={props.onClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.35)' }} onPress={props.onClose} accessibilityLabel="Cerrar" />
      {/* Un Modal de RN en Android no hereda windowSoftInputMode="adjustResize" de la
          actividad (limitación conocida): sin esto, el teclado tapaba el campo que se
          estaba llenando -- bug real encontrado al probar en un teléfono. */}
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ maxHeight: '85%' }}>
      <View style={{ backgroundColor: t.colors.surface, padding: 16, gap: 12, borderTopLeftRadius: 16, borderTopRightRadius: 16 }}>
        <Title>Pieza {tooth}</Title>
        <ScrollView contentContainerStyle={{ gap: 12 }}>
          {props.canWrite ? (
            <>
              <Body style={{ fontWeight: '700' }}>Superficies</Body>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                <Pressable
                  onPress={selectWholeTooth}
                  accessibilityRole="button"
                  accessibilityLabel="Pieza completa"
                  accessibilityState={{ selected: wholeTooth }}
                  style={{ minHeight: 44, paddingHorizontal: 12, borderRadius: 10, justifyContent: 'center', borderWidth: 2, borderColor: wholeTooth ? t.colors.primary : t.colors.border, backgroundColor: wholeTooth ? t.colors.primarySoft : 'transparent' }}
                >
                  <Text style={{ color: t.colors.text, fontWeight: '600' }}>Pieza completa</Text>
                </Pressable>
                {toothSurfaces.map((s) => (
                  <Pressable
                    key={s}
                    onPress={() => toggleSurface(s)}
                    accessibilityRole="button"
                    accessibilityLabel={`Superficie ${SURFACE_LABEL[s]}`}
                    accessibilityState={{ selected: surfaces.has(s) }}
                    style={{ minHeight: 44, paddingHorizontal: 12, borderRadius: 10, justifyContent: 'center', borderWidth: 2, borderColor: surfaces.has(s) ? t.colors.primary : t.colors.border, backgroundColor: surfaces.has(s) ? t.colors.primarySoft : 'transparent' }}
                  >
                    <Text style={{ color: t.colors.text, fontWeight: '600' }}>{SURFACE_LABEL[s]}</Text>
                  </Pressable>
                ))}
              </View>

              <Body style={{ fontWeight: '700' }}>Estado</Body>
              <View style={{ flexDirection: 'row', gap: 8 }}>
                {(Object.keys(KIND_LABEL) as FindingKind[]).map((k) => (
                  <Button key={k} title={KIND_LABEL[k]} variant={kind === k ? 'secondary' : 'ghost'} onPress={() => setKind(k)} />
                ))}
              </View>

              <TextInput
                value={material}
                onChangeText={setMaterial}
                placeholder="Material / nota (opcional)"
                placeholderTextColor={t.colors.textMuted}
                accessibilityLabel="Material o nota"
                style={{ minHeight: 44, borderWidth: 1, borderColor: t.colors.border, borderRadius: t.radius, paddingHorizontal: 12, color: t.colors.text, fontSize: 16 }}
              />

              <Body style={{ fontWeight: '700' }}>Hallazgo (elige para capturar o cambiar el vigente)</Body>
              <TextInput
                value={search}
                onChangeText={setSearch}
                placeholder="Buscar…"
                placeholderTextColor={t.colors.textMuted}
                accessibilityLabel="Buscar hallazgo"
                style={{ minHeight: 44, borderWidth: 1, borderColor: t.colors.border, borderRadius: t.radius, paddingHorizontal: 12, color: t.colors.text, fontSize: 16 }}
              />
              {props.catalogLoading ? <Loading /> : null}
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                {filteredCatalog.map((f) => {
                  const blocked = f.requiresSurface && !wholeTooth && surfaces.size === 0;
                  return (
                    <Pressable
                      key={f.code}
                      disabled={props.creating || !canSubmit || blocked}
                      onPress={() => props.onCreate({ surfaces: Array.from(surfaces), wholeTooth, finding_code: f.code, kind, material: material.trim() || null })}
                      accessibilityRole="button"
                      accessibilityLabel={f.name}
                      style={{ minHeight: 48, paddingHorizontal: 12, borderRadius: 10, justifyContent: 'center', borderWidth: 2, borderColor: FINDING_COLORS[f.code] ?? t.colors.border, opacity: props.creating || !canSubmit || blocked ? 0.4 : 1 }}
                    >
                      <Text style={{ color: t.colors.text, fontWeight: '600' }}>{f.name}</Text>
                    </Pressable>
                  );
                })}
              </View>
              {!canSubmit ? <Body muted>Elige al menos una superficie o "pieza completa".</Body> : null}
            </>
          ) : (
            <Body muted>Sin atención abierta hoy o sin permiso: solo puedes consultar.</Body>
          )}
          {props.createError ? <ErrorBox message={props.createError} /> : null}

          <Body style={{ fontWeight: '700' }}>Historial de la pieza</Body>
          {props.historyLoading ? <Loading /> : null}
          {props.history.length === 0 && !props.historyLoading ? <Body muted>Sin registros.</Body> : null}
          {props.annulError ? <ErrorBox message={props.annulError} /> : null}
          {props.history.map((h) => (
            <View key={h.id} style={{ gap: 4, opacity: h.is_current ? 1 : 0.6 }}>
              <Body>
                {new Date(h.created_at).toLocaleDateString('es-MX')} · {h.author_name || 'Dentia'} · {h.finding_code.toLowerCase()} {h.surface ? SURFACE_LABEL[h.surface] : '(pieza)'} · {KIND_LABEL[h.kind]}
                {h.origin === 'AI_ASSISTED' ? ' · IA' : ''}
                {!h.is_current ? ' · histórico' : ''}
              </Body>
              {props.canWrite && h.is_current ? (
                annulTarget === h.id ? (
                  <View style={{ gap: 8 }}>
                    <TextInput
                      value={annulReason}
                      onChangeText={setAnnulReason}
                      placeholder="Motivo de la anulación (obligatorio)"
                      placeholderTextColor={t.colors.textMuted}
                      accessibilityLabel="Motivo de la anulación"
                      style={{ minHeight: 44, borderWidth: 1, borderColor: t.colors.border, borderRadius: t.radius, paddingHorizontal: 12, color: t.colors.text, fontSize: 16 }}
                    />
                    <Row>
                      <Button
                        title="Confirmar anulación"
                        variant="danger"
                        disabled={!annulReason.trim() || props.annulling}
                        loading={props.annulling}
                        onPress={() => {
                          props.onAnnul(h.id, annulReason.trim());
                          setAnnulTarget(null);
                          setAnnulReason('');
                        }}
                      />
                      <Button title="Ya no" variant="ghost" onPress={() => setAnnulTarget(null)} />
                    </Row>
                  </View>
                ) : (
                  <Button title="Anular este hallazgo" variant="ghost" onPress={() => setAnnulTarget(h.id)} />
                )
              ) : null}
            </View>
          ))}
        </ScrollView>
        <Button title="Cerrar" variant="ghost" onPress={props.onClose} />
      </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
