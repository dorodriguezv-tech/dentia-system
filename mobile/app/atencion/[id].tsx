import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Stack, useLocalSearchParams } from 'expo-router';
import { useKeepAwake } from 'expo-keep-awake';
import { useState } from 'react';
import { Alert, TextInput, View } from 'react-native';

import { ApiError, errorMessage } from '@/api/client';
import { acceptSuggestion, getPatientSummary, interpret, listSuggestions, rejectSuggestion } from '@/api/endpoints';
import type { AiSuggestion, UnrecognizedOut } from '@/api/types';
import { AlertBar, Badge, Body, Button, Card, ErrorBox, Loading, Row, Screen, Title } from '@/components/ui';
import { useVoiceCapture } from '@/voice/useVoiceCapture';
import { useTheme } from '@/theme/theme';

/**
 * Dictado clínico de una atención (docs/03_AGENTE_IA_VOZ.md), versión móvil:
 *   micrófono → /ai/transcribe (faster-whisper local) → texto editable
 *   → /ai/interpret (Ollama local) → propuestas PENDING
 *   → el odontólogo Acepta / Rechaza cada una (regla 9: la IA nunca guarda sola).
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

export default function AtencionScreen() {
  useKeepAwake(); // que la pantalla no se apague mientras el odontólogo dicta
  const { id: encounterId, patientId, patientName } = useLocalSearchParams<{ id: string; patientId: string; patientName?: string }>();
  const t = useTheme();
  const qc = useQueryClient();
  const voice = useVoiceCapture();
  const [text, setText] = useState('');
  const [unrecognized, setUnrecognized] = useState<UnrecognizedOut[]>([]);

  const summary = useQuery({ queryKey: ['patient', patientId], queryFn: () => getPatientSummary(patientId), enabled: !!patientId });
  const suggestions = useQuery({ queryKey: ['suggestions', encounterId], queryFn: () => listSuggestions(encounterId) });

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

  return (
    <Screen>
      <Stack.Screen options={{ title: patientName ? `Atención · ${patientName}` : 'Atención' }} />
      <AlertBar alerts={alerts} />

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
    </Screen>
  );
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
