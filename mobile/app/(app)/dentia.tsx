import { useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Image, Pressable, Text, View } from 'react-native';

import { errorMessage } from '@/api/client';
import { dayRange, hhmm } from '@/api/dates';
import { listAppointments, searchPatients, setAppointmentStatus } from '@/api/endpoints';
import type { PatientListItem } from '@/api/types';
import { Body, Button, Card, ErrorBox, Screen, Title } from '@/components/ui';
import { hasPermission } from '@/store/session';
import { BRAND_ASSETS, useTheme } from '@/theme/theme';
import { say, stopSpeaking } from '@/voice/dentiaVoice';
import { describeIntent, needsImplicitConfirm, normalize, parseIntent, type Intent } from '@/voice/intents';
import { useImplicitConfirm } from '@/voice/useImplicitConfirm';
import { useVoiceCapture } from '@/voice/useVoiceCapture';

/**
 * Asistente "Dentia" en el teléfono.
 *
 * v1 móvil: se activa tocando el botón (o el ícono de la pestaña). La escucha continua
 * con palabra de activación ("Dentia") queda para la fase 2 (docs/05 §9): en un teléfono
 * mantener el micrófono abierto todo el día gasta batería, Android muestra un aviso
 * permanente y Google Play exige justificar ese uso en primer plano.
 *
 * Flujo: escucha → transcribe en el servidor de la clínica → interpreta la orden aquí
 * (sin LLM) → Dentia responde con voz → si la orden cambia algo, confirmación implícita
 * de 3 s con opción de cancelar (decisión del proyecto).
 */

const MAX_SECONDS = 8;

interface Turn {
  who: 'tu' | 'dentia';
  text: string;
}

export default function DentiaScreen() {
  const t = useTheme();
  const qc = useQueryClient();
  const voice = useVoiceCapture();
  const confirm = useImplicitConfirm(3);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [choices, setChoices] = useState<PatientListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const stopping = useRef(false);

  const reply = useCallback((text: string) => {
    setTurns((prev) => [...prev.slice(-12), { who: 'dentia', text }]);
    void say(text);
  }, []);

  const openPatient = useCallback((p: PatientListItem) => {
    setChoices([]);
    router.push({ pathname: '/paciente/[id]', params: { id: p.id } });
  }, []);

  const execute = useCallback(
    async (intent: Intent) => {
      try {
        switch (intent.type) {
          case 'OPEN_PATIENT': {
            const found = await searchPatients(intent.name);
            if (found.length === 0) return reply(`No encontré a ningún paciente llamado ${intent.name}.`);
            if (found.length === 1 && found[0]) return openPatient(found[0]);
            setChoices(found.slice(0, 6));
            return reply(`Encontré ${found.length} pacientes con ese nombre. Elige uno en la pantalla.`);
          }
          case 'SHOW_AGENDA':
            return router.navigate({ pathname: '/(app)', params: { dia: String(intent.dayOffset) } });
          case 'NEXT_APPOINTMENT': {
            const r = dayRange(0);
            const list = await listAppointments(r.from, r.to);
            const now = Date.now();
            const next = list
              .filter((a) => ['RESERVADA', 'CONFIRMADA', 'EN_SALA'].includes(a.status) && new Date(a.ends_at).getTime() > now)
              .sort((a, b) => a.starts_at.localeCompare(b.starts_at))[0];
            if (!next) return reply('No quedan citas pendientes hoy.');
            reply(`Sigue ${next.patient_full_name}, a las ${hhmm(next.starts_at)}.`);
            return;
          }
          case 'CHECK_IN': {
            if (!hasPermission('agenda.write')) return reply('Tu usuario no tiene permiso para mover citas.');
            const r = dayRange(0);
            const list = await listAppointments(r.from, r.to);
            const target = normalize(intent.name);
            const matches = list.filter(
              (a) => ['RESERVADA', 'CONFIRMADA'].includes(a.status) && target.split(' ').every((w) => normalize(a.patient_full_name).includes(w)),
            );
            if (matches.length !== 1 || !matches[0]) {
              return reply(
                matches.length === 0
                  ? `No encontré una cita pendiente hoy para ${intent.name}.`
                  : `Hay ${matches.length} citas que coinciden con ${intent.name}. Márcala desde la agenda.`,
              );
            }
            await setAppointmentStatus(matches[0].id, 'EN_SALA');
            void qc.invalidateQueries({ queryKey: ['appointments'] });
            return reply(`Listo, ${matches[0].patient_full_name} está en sala.`);
          }
          case 'START_DICTATION':
            return reply('Para dictar, abre la atención del paciente desde la agenda y toca Dictar. Así el dictado queda en la atención correcta.');
          default:
            return reply(describeIntent(intent));
        }
      } catch (e) {
        reply(`No pude hacerlo: ${errorMessage(e)}`);
      }
    },
    [openPatient, qc, reply],
  );

  const handleHeard = useCallback(
    (heard: string) => {
      if (!heard) return reply('No te escuché. Toca el botón e inténtalo de nuevo.');
      setTurns((prev) => [...prev.slice(-12), { who: 'tu', text: heard }]);
      const intent = parseIntent(heard);

      if (intent.type === 'CANCEL') {
        if (confirm.pending) confirm.cancel();
        return reply('Cancelado.');
      }
      if (intent.type === 'CONFIRM') {
        if (confirm.pending) return confirm.confirmNow();
        return reply('No hay nada pendiente por confirmar.');
      }
      if (needsImplicitConfirm(intent)) {
        const label = describeIntent(intent);
        reply(`${label} Di cancela si no es correcto.`);
        confirm.schedule(label, () => execute(intent));
        return;
      }
      if (intent.type === 'SHOW_AGENDA') reply(describeIntent(intent));
      void execute(intent);
    },
    [confirm, execute, reply],
  );

  const talk = useCallback(async () => {
    setError(null);
    await stopSpeaking();
    if (voice.isRecording) {
      if (stopping.current) return;
      stopping.current = true;
      const heard = await voice.stopAndTranscribe();
      stopping.current = false;
      handleHeard(heard);
    } else {
      await voice.start();
    }
  }, [handleHeard, voice]);

  // Corte automático: las órdenes son cortas
  useEffect(() => {
    if (voice.isRecording && voice.seconds >= MAX_SECONDS) void talk();
  }, [voice.isRecording, voice.seconds, talk]);

  useEffect(() => {
    if (voice.error) setError(voice.error);
  }, [voice.error]);

  const listening = voice.isRecording;
  const busy = voice.state === 'transcribing';

  return (
    <Screen>
      <View style={{ alignItems: 'center', gap: 16, paddingVertical: 16 }}>
        <Pressable
          onPress={() => void talk()}
          disabled={busy}
          accessibilityRole="button"
          accessibilityLabel={listening ? 'Dejar de escuchar' : 'Hablar con Dentia'}
          style={({ pressed }) => ({
            width: 168,
            height: 168,
            borderRadius: 84,
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: listening ? t.colors.danger : t.colors.primary,
            opacity: busy ? 0.6 : pressed ? 0.85 : 1,
            borderWidth: listening ? 8 : 0,
            borderColor: t.colors.dangerSoft,
          })}
        >
          {listening ? (
            <Text style={{ fontSize: 56, color: t.colors.onPrimary }}>◼</Text>
          ) : (
            <Image source={BRAND_ASSETS.isotipoWhite} style={{ width: 96, height: 96, tintColor: t.colors.onPrimary }} accessible={false} />
          )}
        </Pressable>
        <Title>{listening ? `Te escucho… (${voice.seconds}s)` : busy ? 'Entendiendo…' : 'Toca y habla con Dentia'}</Title>
        <Body muted style={{ textAlign: 'center' }}>
          “Abre el expediente de Ana López” · “Agenda de mañana” · “¿Quién sigue?” · “Laura Sánchez ya llegó”
        </Body>
      </View>

      {confirm.pending ? (
        <Card style={{ borderColor: t.colors.primary, borderWidth: 2 }}>
          <Body style={{ fontWeight: '700' }}>{confirm.pending.label}</Body>
          <Body muted>Se ejecuta en {confirm.pending.remaining} s…</Body>
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <Button title="Cancelar" variant="danger" onPress={() => { confirm.cancel(); reply('Cancelado.'); }} />
            <Button title="Hacerlo ya" variant="secondary" onPress={confirm.confirmNow} />
          </View>
        </Card>
      ) : null}

      {choices.length ? (
        <Card>
          <Body style={{ fontWeight: '700' }}>¿Cuál paciente?</Body>
          {choices.map((p) => (
            <Button key={p.id} title={`${p.full_name} · Exp. ${p.expediente_number}`} variant="ghost" onPress={() => openPatient(p)} />
          ))}
        </Card>
      ) : null}

      {error ? <ErrorBox message={error} /> : null}

      {turns.map((turn, i) => (
        <View
          key={i}
          style={{
            alignSelf: turn.who === 'tu' ? 'flex-end' : 'flex-start',
            maxWidth: '85%',
            backgroundColor: turn.who === 'tu' ? t.colors.primarySoft : t.colors.surface,
            borderRadius: 14,
            padding: 12,
            borderWidth: turn.who === 'dentia' ? 1 : 0,
            borderColor: t.colors.border,
          }}
        >
          <Text style={{ color: t.colors.text, fontSize: 15 }}>{turn.text}</Text>
        </View>
      ))}
    </Screen>
  );
}
