import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useKeepAwake } from 'expo-keep-awake';
import { useEffect, useState } from 'react';
import { Alert, BackHandler, TextInput, View } from 'react-native';

import { ApiError, errorMessage } from '@/api/client';
import {
  acceptSuggestion,
  closeEncounter,
  createNote,
  createWaitlistEntry,
  finalizeNote,
  getEncounter,
  getOdontogram,
  getPatientEncounters,
  getPatientSummary,
  interpret,
  listEncounterNotes,
  listProceduresPerformed,
  listSuggestions,
  listTreatmentPlans,
  rejectSuggestion,
  updateNote,
} from '@/api/endpoints';
import type { AiSuggestion, UnrecognizedOut } from '@/api/types';
import { AlertBar, Badge, Body, Button, Card, ErrorBox, Loading, Row, Screen, Title } from '@/components/ui';
import { buildNotePrefill } from '@/encounters/notePrefill';
import { useVoiceCapture } from '@/voice/useVoiceCapture';
import { useTheme } from '@/theme/theme';

/**
 * Pantalla "Consulta" (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3): Resumen, Dictado y
 * Nota (M6, con "Cerrar consulta"). Odontograma editable dentro de esta pantalla y
 * Fotos/Procedimientos como pestañas propias quedan fuera de alcance — ya existen
 * por separado (odontograma y fotos desde la ficha del paciente; procedimientos se
 * resumen aquí, en el prellenado de la nota).
 *
 * Dictado: micrófono → /ai/transcribe (faster-whisper local) → texto editable
 * → /ai/interpret (Ollama local) → propuestas PENDING
 * → el odontólogo Acepta / Rechaza cada una (regla 9: la IA nunca guarda sola).
 */

const DESTINO: Record<string, string> = {
  set_chief_complaint: 'Atención',
  add_vital_signs: 'Atención',
  append_note: 'Nota',
  add_allergy: 'Expediente',
  add_medication: 'Expediente',
  add_medical_history: 'Expediente',
  add_tooth_finding: 'Odontograma',
  add_diagnosis: 'Diagnóstico',
  add_planned_procedure: 'Plan',
  add_performed_procedure: 'Plan',
  schedule_followup: 'Agenda',
};

const NEEDS_ALERT_CHECK = new Set(['add_planned_procedure', 'add_performed_procedure']);

const PLAN_STATUS_LABEL: Record<string, string> = {
  BORRADOR: 'Borrador',
  PRESENTADO: 'Presentado',
  ACEPTADO: 'Aceptado',
  RECHAZADO: 'Rechazado',
  EN_PROGRESO: 'En progreso',
  TERMINADO: 'Terminado',
};

type Section = 'resumen' | 'dictado' | 'nota';

export default function AtencionScreen() {
  useKeepAwake(); // que la pantalla no se apague mientras el odontólogo dicta
  const { id: encounterId, patientId, patientName } = useLocalSearchParams<{ id: string; patientId: string; patientName?: string }>();
  const t = useTheme();
  const qc = useQueryClient();
  const voice = useVoiceCapture();
  const [text, setText] = useState('');
  const [unrecognized, setUnrecognized] = useState<UnrecognizedOut[]>([]);
  const [section, setSection] = useState<Section>('resumen');
  // Regla 8 de CLAUDE.md: la primera vez que se abre esta atención, hay que
  // "enterarse" de las alertas antes de poder hacer nada más. No hay un endpoint
  // propio para auditar este acuse (solo existe para finalizar la nota, M6) — por
  // ahora es una compuerta de la interfaz, documentado en docs/PENDIENTES_CLINICOS.md.
  const [ackAlerts, setAckAlerts] = useState(false);
  useEffect(() => setAckAlerts(false), [encounterId]);

  // M8: el botón Atrás de Android no debe cerrar la consulta "por accidente" —
  // solo confirma salir (la consulta sigue abierta; la barra "En consulta" permite
  // volver, docs/06_APP_MOVIL_V1_1_PARIDAD.md §2).
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      Alert.alert('¿Salir de la consulta?', 'Quedará abierta; puedes volver desde "En consulta" arriba.', [
        { text: 'Seguir aquí', style: 'cancel' },
        { text: 'Salir', onPress: () => router.back() },
      ]);
      return true; // evita que Android salga directo
    });
    return () => sub.remove();
  }, []);

  const summary = useQuery({ queryKey: ['patient', patientId], queryFn: () => getPatientSummary(patientId), enabled: !!patientId });
  const encounter = useQuery({ queryKey: ['encounter', encounterId], queryFn: () => getEncounter(encounterId) });
  const encounters = useQuery({ queryKey: ['encounters', patientId], queryFn: () => getPatientEncounters(patientId), enabled: !!patientId });
  const plans = useQuery({ queryKey: ['treatment-plans', patientId], queryFn: () => listTreatmentPlans(patientId), enabled: !!patientId });
  const suggestions = useQuery({ queryKey: ['suggestions', encounterId], queryFn: () => listSuggestions(encounterId) });
  const odo = useQuery({ queryKey: ['odontogram', patientId], queryFn: () => getOdontogram(patientId), enabled: !!patientId });
  const procedures = useQuery({ queryKey: ['procedures-performed', patientId], queryFn: () => listProceduresPerformed(patientId), enabled: !!patientId });
  const notesQ = useQuery({ queryKey: ['notes', encounterId], queryFn: () => listEncounterNotes(encounterId) });

  // M6: nota SOAP de esta consulta -- se precarga con lo capturado hoy la primera
  // vez que no hay ningún borrador todavía (nunca vuelve a sobreescribir lo que el
  // odontólogo ya haya escrito en un refetch posterior).
  const [noteId, setNoteId] = useState<string | null>(null);
  const [soapS, setSoapS] = useState('');
  const [soapO, setSoapO] = useState('');
  const [soapA, setSoapA] = useState('');
  const [soapP, setSoapP] = useState('');
  const [prefilled, setPrefilled] = useState(false);

  useEffect(() => {
    if (prefilled || !notesQ.data) return;
    const draft = notesQ.data.find((n) => n.status === 'DRAFT');
    const final = notesQ.data.find((n) => n.status === 'FINAL');
    const existing = final ?? draft;
    if (existing) {
      setNoteId(existing.id);
      setSoapS(existing.soap_s ?? '');
      setSoapO(existing.soap_o ?? '');
      setSoapA(existing.soap_a ?? '');
      setSoapP(existing.soap_p ?? '');
    } else {
      const { soapS: s, soapO: o } = buildNotePrefill({
        encounterId,
        chiefComplaint: encounter.data?.chief_complaint,
        findings: odo.data ?? [],
        proceduresPerformed: procedures.data ?? [],
        suggestions: suggestions.data ?? [],
        describeSuggestion,
      });
      setSoapS(s);
      setSoapO(o);
    }
    setPrefilled(true);
  }, [prefilled, notesQ.data, odo.data, procedures.data, suggestions.data, encounter.data, encounterId]);

  const noteFields = { soap_s: soapS || null, soap_o: soapO || null, soap_a: soapA || null, soap_p: soapP || null };
  const finalNote = notesQ.data?.find((n) => n.status === 'FINAL');
  const isClosed = !!encounter.data?.ended_at;

  const saveDraft = useMutation({
    mutationFn: async () => (noteId ? updateNote(noteId, noteFields) : createNote(encounterId, noteFields)),
    onSuccess: (note) => {
      setNoteId(note.id);
      void qc.invalidateQueries({ queryKey: ['notes', encounterId] });
    },
  });

  const finalizeAndClose = useMutation({
    mutationFn: async () => {
      const id = noteId ? (await updateNote(noteId, noteFields)).id : (await createNote(encounterId, noteFields)).id;
      setNoteId(id);
      await finalizeNote(id, true); // la pantalla ya exigió "Enterado" de las alertas al entrar
      return closeEncounter(encounterId, true);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['notes', encounterId] });
      void qc.invalidateQueries({ queryKey: ['encounter', encounterId] });
      void qc.invalidateQueries({ queryKey: ['encounters', 'current'] });
      void qc.invalidateQueries({ queryKey: ['appointments'] });
      promptNextAppointment();
    },
  });

  const remindLater = useMutation({
    mutationFn: () => createWaitlistEntry({ patient_id: patientId, notes: 'Seguimiento pendiente de agendar (cierre de consulta)' }),
    onSuccess: () => router.back(),
  });

  const confirmFinalize = () => {
    Alert.alert('Finalizar nota', 'Una nota final no se puede modificar; las correcciones crean una versión nueva.', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Finalizar y cerrar', onPress: () => finalizeAndClose.mutate() },
    ]);
  };

  const promptNextAppointment = () => {
    const planHint = plansToShow[0]?.title;
    Alert.alert('¿Agendar la próxima cita?', undefined, [
      { text: 'No requiere', style: 'cancel', onPress: () => router.back() },
      { text: 'Recordar después', onPress: () => remindLater.mutate() },
      {
        text: 'Agendar',
        onPress: () =>
          router.replace({
            pathname: '/cita/nueva',
            params: {
              patientId,
              patientName: patientName ?? '',
              suggestedOffsetDays: '7',
              ...(planHint ? { planHint: `Plan pendiente: ${planHint}` } : {}),
            },
          }),
      },
    ]);
  };

  const runInterpret = useMutation({
    mutationFn: () => interpret({ transcript: text, encounter_id: encounterId }),
    onSuccess: (r) => {
      setUnrecognized(r.unrecognized ?? []);
      void qc.invalidateQueries({ queryKey: ['suggestions', encounterId] });
    },
  });

  const decide = useMutation({
    mutationFn: ({ s, accept }: { s: AiSuggestion; accept: boolean }) => (accept ? acceptSuggestion(s.id) : rejectSuggestion(s.id, 'Rechazada desde la app')),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['suggestions', encounterId] });
      void qc.invalidateQueries({ queryKey: ['odontogram', patientId] });
      void qc.invalidateQueries({ queryKey: ['patient', patientId] });
    },
  });

  const alerts = summary.data?.alerts ?? [];
  const pending = (suggestions.data ?? []).filter((s) => s.status === 'PENDING');
  const previousEncounters = (encounters.data ?? []).filter((e) => e.id !== encounterId).slice(0, 3);
  const plansToShow = (plans.data ?? []).filter((p) => p.status !== 'RECHAZADO');

  const accept = (s: AiSuggestion) => {
    if (NEEDS_ALERT_CHECK.has(s.action_type) && alerts.length) {
      Alert.alert('Revisa las alertas clínicas', alerts.map((a) => `• ${a}`).join('\n'), [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Aceptar de todos modos', onPress: () => decide.mutate({ s, accept: true }) },
      ]);
      return;
    }
    decide.mutate({ s, accept: true });
  };

  const acceptAll = async () => {
    for (const s of pending) {
      if (NEEDS_ALERT_CHECK.has(s.action_type) && alerts.length) continue; // esas se revisan una por una
      try {
        await decide.mutateAsync({ s, accept: true });
      } catch {
        /* el error queda visible en decide.error */
      }
    }
  };

  const toggleMic = async () => {
    if (voice.isRecording) {
      const heard = await voice.stopAndTranscribe();
      if (heard) setText((prev) => (prev ? `${prev} ${heard}` : heard));
    } else {
      await voice.start();
    }
  };

  const ollamaDown = runInterpret.error instanceof ApiError && runInterpret.error.status === 503;

  if (!summary.isLoading && alerts.length > 0 && !ackAlerts) {
    return (
      <Screen>
        <Stack.Screen options={{ title: patientName ? `Atención · ${patientName}` : 'Atención' }} />
        <Card style={{ borderColor: t.colors.danger, borderWidth: 2 }}>
          <Title>⚠ Alertas clínicas</Title>
          {alerts.map((a, i) => (
            <Body key={`${a}-${i}`}>• {a}</Body>
          ))}
          <Button title="Enterado" variant="danger" onPress={() => setAckAlerts(true)} />
        </Card>
      </Screen>
    );
  }

  return (
    <Screen>
      <Stack.Screen options={{ title: patientName ? `Atención · ${patientName}` : 'Atención' }} />
      <AlertBar alerts={alerts} />

      {isClosed ? (
        <Card style={{ borderColor: t.colors.success, borderWidth: 2 }}>
          <Body style={{ fontWeight: '700' }}>Consulta cerrada</Body>
        </Card>
      ) : null}

      <Row>
        <Button title="Resumen" variant={section === 'resumen' ? 'secondary' : 'ghost'} onPress={() => setSection('resumen')} />
        <Button title="Dictado" variant={section === 'dictado' ? 'secondary' : 'ghost'} onPress={() => setSection('dictado')} />
        <Button title="Nota" variant={section === 'nota' ? 'secondary' : 'ghost'} onPress={() => setSection('nota')} />
      </Row>

      {section === 'resumen' ? (
        <>
          <Card>
            <Title>Motivo de esta atención</Title>
            {encounter.isLoading ? <Loading /> : null}
            <Body muted>{encounter.data?.chief_complaint || 'Sin motivo capturado.'}</Body>
          </Card>

          <Card>
            <Title>Últimas atenciones</Title>
            {previousEncounters.length === 0 ? <Body muted>Esta es la primera atención registrada.</Body> : null}
            {previousEncounters.map((e) => (
              <Body key={e.id}>{new Date(e.started_at).toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long' })}</Body>
            ))}
          </Card>

          <Card>
            <Title>Plan de tratamiento</Title>
            {plansToShow.length === 0 ? <Body muted>Sin plan de tratamiento vigente.</Body> : null}
            {plansToShow.map((p) => (
              <Row key={p.id} style={{ justifyContent: 'space-between' }}>
                <Body style={{ fontWeight: '600' }}>{p.title}</Body>
                <Badge label={PLAN_STATUS_LABEL[p.status] ?? p.status} color={t.colors.secondary} />
              </Row>
            ))}
          </Card>
        </>
      ) : section === 'dictado' ? (
        <>
          <Card>
            <Title>Dictado</Title>
            <Button
              big
              title={voice.isRecording ? `Detener (${voice.seconds}s)` : voice.state === 'transcribing' ? 'Transcribiendo…' : 'Dictar'}
              variant={voice.isRecording ? 'danger' : 'primary'}
              loading={voice.state === 'transcribing'}
              onPress={() => void toggleMic()}
              accessibilityHint="Graba el dictado; vuelve a tocar para detener y transcribir"
            />
            {voice.error ? <ErrorBox message={voice.error} /> : null}
            <TextInput
              multiline
              value={text}
              onChangeText={setText}
              placeholder="Aquí aparece lo que dictes. Puedes corregirlo antes de interpretar."
              placeholderTextColor={t.colors.textMuted}
              accessibilityLabel="Transcripción del dictado"
              style={{
                minHeight: 120,
                textAlignVertical: 'top',
                borderWidth: 1,
                borderColor: t.colors.border,
                borderRadius: t.radius,
                padding: 12,
                color: t.colors.text,
                fontSize: 16,
              }}
            />
            <Row>
              <Button title="Interpretar dictado" onPress={() => runInterpret.mutate()} disabled={!text.trim()} loading={runInterpret.isPending} />
              {text ? <Button title="Limpiar" variant="ghost" onPress={() => setText('')} /> : null}
            </Row>
            {runInterpret.isPending ? <Body muted>El modelo local puede tardar hasta 2 minutos…</Body> : null}
            {runInterpret.error ? (
              <ErrorBox
                message={
                  ollamaDown
                    ? 'El asistente (Ollama) no está disponible en el servidor. Tu texto se conserva aquí; interprétalo cuando vuelva o captúralo en la computadora.'
                    : errorMessage(runInterpret.error)
                }
              />
            ) : null}
            {unrecognized.length ? (
              <View style={{ gap: 4 }}>
                <Body style={{ fontWeight: '700' }}>No reconocido (captúralo a mano):</Body>
                {unrecognized.map((u, i) => (
                  <Body key={i} muted>
                    • {u.text}
                  </Body>
                ))}
              </View>
            ) : null}
          </Card>

          <Row style={{ justifyContent: 'space-between' }}>
            <Title>Propuestas del asistente</Title>
            {pending.length > 1 ? <Button title="Aceptar todo" variant="secondary" onPress={() => void acceptAll()} /> : null}
          </Row>
          {suggestions.isLoading ? <Loading /> : null}
          {decide.error ? <ErrorBox message={errorMessage(decide.error)} /> : null}
          {suggestions.data && pending.length === 0 ? <Body muted>Sin propuestas pendientes.</Body> : null}

          {pending.map((s) => (
            <Card key={s.id}>
              <Row style={{ justifyContent: 'space-between' }}>
                <Badge label={DESTINO[s.action_type] ?? s.action_type} color={t.colors.primary} />
                <Badge label="IA" color={t.colors.secondary} />
              </Row>
              <Body>{describeSuggestion(s)}</Body>
              {s.transcript_excerpt ? <Body muted>“{s.transcript_excerpt}”</Body> : null}
              <Row>
                <Button title="Aceptar" onPress={() => accept(s)} disabled={decide.isPending} />
                <Button title="Rechazar" variant="ghost" onPress={() => decide.mutate({ s, accept: false })} disabled={decide.isPending} />
              </Row>
            </Card>
          ))}
          <Body muted>Para editar el contenido de una propuesta, ábrela en la versión web (pantalla Atención).</Body>
        </>
      ) : (
        <>
          {finalNote ? (
            <Card>
              <Title>Nota finalizada</Title>
              <Body muted>Esta nota ya es definitiva. Las correcciones se hacen desde la computadora.</Body>
            </Card>
          ) : (
            <Card>
              <Title>Nota de la consulta</Title>
              <Body muted>Prellenada con lo capturado hoy; puedes corregirla antes de guardar.</Body>
              <Body style={{ fontWeight: '700' }}>S · Subjetivo (motivo, síntomas)</Body>
              <TextInput multiline value={soapS} onChangeText={setSoapS} placeholderTextColor={t.colors.textMuted} accessibilityLabel="Subjetivo" style={noteInputStyle(t)} />
              <Body style={{ fontWeight: '700' }}>O · Objetivo (hallazgos, procedimientos)</Body>
              <TextInput multiline value={soapO} onChangeText={setSoapO} placeholderTextColor={t.colors.textMuted} accessibilityLabel="Objetivo" style={noteInputStyle(t)} />
              <Body style={{ fontWeight: '700' }}>A · Análisis (diagnóstico)</Body>
              <TextInput multiline value={soapA} onChangeText={setSoapA} placeholderTextColor={t.colors.textMuted} accessibilityLabel="Análisis" style={noteInputStyle(t)} />
              <Body style={{ fontWeight: '700' }}>P · Plan</Body>
              <TextInput multiline value={soapP} onChangeText={setSoapP} placeholderTextColor={t.colors.textMuted} accessibilityLabel="Plan" style={noteInputStyle(t)} />

              {saveDraft.error ? <ErrorBox message={errorMessage(saveDraft.error)} /> : null}
              {finalizeAndClose.error ? <ErrorBox message={errorMessage(finalizeAndClose.error)} /> : null}

              <Row>
                <Button title="Guardar borrador" variant="secondary" onPress={() => saveDraft.mutate()} loading={saveDraft.isPending} />
                <Button title="Finalizar y cerrar consulta" variant="danger" onPress={confirmFinalize} loading={finalizeAndClose.isPending} disabled={isClosed} />
              </Row>
            </Card>
          )}
        </>
      )}
    </Screen>
  );
}

function noteInputStyle(t: ReturnType<typeof useTheme>) {
  return {
    minHeight: 70,
    textAlignVertical: 'top' as const,
    borderWidth: 1,
    borderColor: t.colors.border,
    borderRadius: t.radius,
    padding: 12,
    color: t.colors.text,
    fontSize: 16,
  };
}

/** Texto legible de una propuesta (payload según docs/03 §4). */
function describeSuggestion(s: AiSuggestion): string {
  const p = s.payload as Record<string, any>;
  const surf = Array.isArray(p.surfaces) && p.surfaces.length ? ` ${p.surfaces.join('')}` : '';
  switch (s.action_type) {
    case 'set_chief_complaint':
      return `Motivo de consulta: ${p.text}`;
    case 'add_allergy':
      return `Alergia: ${p.substance}${p.reaction ? ` (${p.reaction})` : ''}${p.severity ? ` · ${p.severity}` : ''}`;
    case 'add_medication':
      return `Medicamento: ${p.name}${p.dose ? ` ${p.dose}` : ''}${p.frequency ? ` · ${p.frequency}` : ''}`;
    case 'add_medical_history':
      return `Antecedente (${p.category}): ${p.text}`;
    case 'add_vital_signs':
      return `Signos vitales: ${[p.bp_sys && p.bp_dia ? `TA ${p.bp_sys}/${p.bp_dia}` : null, p.hr ? `FC ${p.hr}` : null, p.temp ? `T ${p.temp}°` : null].filter(Boolean).join(' · ')}`;
    case 'add_tooth_finding':
      return `Pieza ${p.tooth_fdi}${surf}: ${String(p.finding_code).toLowerCase()}${p.material ? ` (${p.material})` : ''}`;
    case 'add_diagnosis':
      return `Diagnóstico: ${p.text}${p.tooth_fdi ? ` en ${p.tooth_fdi}` : ''}`;
    case 'add_planned_procedure':
      return `Plan: ${p.procedure_code}${p.tooth_fdi ? ` en ${p.tooth_fdi}${surf}` : ''}`;
    case 'add_performed_procedure':
      return `Realizado: ${p.procedure_code}${p.tooth_fdi ? ` en ${p.tooth_fdi}${surf}` : ''}`;
    case 'append_note':
      return `Nota (${p.section}): ${p.text}`;
    case 'schedule_followup':
      return `Seguimiento en ${p.in_days} días: ${p.reason}`;
    default:
      return JSON.stringify(p);
  }
}
