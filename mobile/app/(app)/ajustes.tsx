import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Constants from 'expo-constants';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert } from 'react-native';

import { getAiStatus, logout, updatePreferences } from '@/api/endpoints';
import type { PreferenceTheme, UserPreferencesUpdate } from '@/api/types';
import { DentiaLogo, PoweredByDentia } from '@/components/Brand';
import { Badge, Body, Button, Card, ErrorBox, Row, Screen, Title } from '@/components/ui';
import { performLogout } from '@/session/logout';
import { hasPermission, useSession } from '@/store/session';
import { useTheme } from '@/theme/theme';
import { stopActiveRecording } from '@/voice/activeRecording';
import { listSpanishVoices, say, setPreferredVoice, setSpeechRate, setSpeechVolume, stopSpeaking } from '@/voice/dentiaVoice';

/**
 * M2 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3): "Mis preferencias" (todos los usuarios,
 * sincronizadas con GET/PUT /me/preferences — B7) separado de "Clínica" (servidor,
 * marca, IA — solo `branding.manage` o `ai.configure`, R4 del documento de paridad).
 *
 * Idioma: el backend ya acepta cualquier valor y lo guarda, pero ni la web ni esta
 * app tienen todavía textos en otro idioma que no sea español — por eso se muestra
 * como informativo en vez de un selector que no cambiaría nada (M8: "nunca un botón
 * muerto"). Queda anotado en docs/PENDIENTES_CLINICOS.md.
 */
const THEME_OPTIONS: { value: PreferenceTheme; label: string }[] = [
  { value: 'system', label: 'Según el teléfono' },
  { value: 'light', label: 'Claro' },
  { value: 'dark', label: 'Oscuro' },
];

const RATE_OPTIONS: { value: number; label: string }[] = [
  { value: 0.85, label: 'Lenta' },
  { value: 1.0, label: 'Normal' },
  { value: 1.15, label: 'Rápida' },
];

const VOLUME_OPTIONS: { value: number; label: string }[] = [
  { value: 0.5, label: 'Baja' },
  { value: 0.8, label: 'Media' },
  { value: 1.0, label: 'Alta' },
];

const LOCK_OPTIONS = [1, 2, 5];

export default function AjustesScreen() {
  const t = useTheme();
  const qc = useQueryClient();
  const { me, clinics, clinicId, serverUrl, refreshToken, preferences } = useSession();
  const clinic = clinics.find((c) => c.clinic_id === clinicId);
  const [voices, setVoices] = useState<{ id: string; label: string }[]>([]);

  const canSeeClinicSection = hasPermission('branding.manage') || hasPermission('ai.configure');
  const ai = useQuery({
    queryKey: ['ai-status'],
    queryFn: getAiStatus,
    enabled: hasPermission('ai.configure'),
  });

  useEffect(() => {
    listSpanishVoices()
      .then((vs) => setVoices(vs.map((v) => ({ id: v.identifier, label: `${v.name} (${v.language})${/network/i.test(v.identifier) ? ' · en línea' : ''}` }))))
      .catch(() => setVoices([]));
  }, []);

  const savePrefs = useMutation({
    mutationFn: (patch: UserPreferencesUpdate) => updatePreferences(patch),
    onSuccess: (updated) => {
      useSession.getState().setPreferences(updated);
      // Para que "Probar voz" y el resto de la app lo noten de inmediato, sin
      // esperar al efecto global de app/_layout.tsx.
      setPreferredVoice(updated.voice_id);
      setSpeechRate(updated.speech_rate);
      setSpeechVolume(updated.speech_volume);
    },
  });

  const doLogout = () =>
    performLogout({
      refreshToken,
      logoutApi: logout,
      stopVoice: () => {
        void stopSpeaking();
        stopActiveRecording();
      },
      clearQueryCache: () => qc.clear(),
      clearSession: () => useSession.getState().clear(),
      navigateToLogin: () => router.replace('/login'),
    });

  const confirmLogout = () => {
    Alert.alert('¿Cerrar sesión?', 'Si tienes una consulta abierta, quedará en borrador.', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Cerrar sesión', style: 'destructive', onPress: () => void doLogout() },
    ]);
  };

  const dentiaEnabled = preferences?.dentia_enabled ?? true;

  return (
    <Screen>
      <Card>
        <Title>{me?.full_name ?? 'Usuario'}</Title>
        <Body muted>{me?.email}</Body>
        <Body>
          {clinic?.clinic_name} · {clinic?.role}
        </Body>
        {clinics.length > 1 ? <Button title="Cambiar de sucursal" variant="secondary" onPress={() => router.push('/sucursal')} /> : null}
      </Card>

      <Card>
        <Title>Mis preferencias</Title>
        <Body muted>Se guardan en tu cuenta: viajan contigo entre el teléfono, la tablet y la computadora.</Body>

        <Body style={{ fontWeight: '700' }}>Idioma</Body>
        <Body muted>Español (México) · más idiomas próximamente</Body>

        <Body style={{ fontWeight: '700' }}>Asistente Dentia</Body>
        <Button
          title={dentiaEnabled ? 'Activada · tocar para desactivar' : 'Desactivada · tocar para activar'}
          variant={dentiaEnabled ? 'secondary' : 'ghost'}
          onPress={() => savePrefs.mutate({ dentia_enabled: !dentiaEnabled })}
          loading={savePrefs.isPending}
        />

        <Body style={{ fontWeight: '700' }}>Voz de Dentia</Body>
        <Body muted>Se prefieren voces instaladas en el teléfono (sin internet). Si no hay voz en español, instala “Datos de voz” en Ajustes de Android → Texto a voz.</Body>
        {voices.slice(0, 8).map((v) => (
          <Button
            key={v.id}
            title={`${preferences?.voice_id === v.id ? '✓ ' : ''}${v.label}`}
            variant={preferences?.voice_id === v.id ? 'secondary' : 'ghost'}
            onPress={() => {
              savePrefs.mutate(
                { voice_id: v.id },
                { onSuccess: () => void say('Hola, soy Dentia. ¿En qué te ayudo?') },
              );
            }}
          />
        ))}

        <Body style={{ fontWeight: '700' }}>Velocidad de voz</Body>
        <Row>
          {RATE_OPTIONS.map((o) => (
            <Button
              key={o.label}
              title={o.label}
              variant={(preferences?.speech_rate ?? 1.0) === o.value ? 'secondary' : 'ghost'}
              onPress={() => savePrefs.mutate({ speech_rate: o.value })}
            />
          ))}
        </Row>

        <Body style={{ fontWeight: '700' }}>Volumen de voz</Body>
        <Row>
          {VOLUME_OPTIONS.map((o) => (
            <Button
              key={o.label}
              title={o.label}
              variant={(preferences?.speech_volume ?? 1.0) === o.value ? 'secondary' : 'ghost'}
              onPress={() => savePrefs.mutate({ speech_volume: o.value })}
            />
          ))}
        </Row>

        <Body style={{ fontWeight: '700' }}>Tema</Body>
        <Row>
          {THEME_OPTIONS.map((o) => (
            <Button
              key={o.value}
              title={o.label}
              variant={(preferences?.theme ?? 'system') === o.value ? 'secondary' : 'ghost'}
              onPress={() => savePrefs.mutate({ theme: o.value })}
            />
          ))}
        </Row>

        <Body style={{ fontWeight: '700' }}>Bloquear la app tras</Body>
        <Row>
          {LOCK_OPTIONS.map((min) => (
            <Button
              key={min}
              title={`${min} min`}
              variant={(preferences?.lock_timeout_minutes ?? 2) === min ? 'secondary' : 'ghost'}
              onPress={() => savePrefs.mutate({ lock_timeout_minutes: min })}
            />
          ))}
        </Row>

        {savePrefs.error ? <ErrorBox message="No se pudo guardar. Se intentará de nuevo con la próxima acción." /> : null}
      </Card>

      {canSeeClinicSection ? (
        <Card>
          <Title>Clínica</Title>
          <Body muted>Servidor: {serverUrl}</Body>
          {ai.data ? (
            <Row>
              <Badge label={`IA ${ai.data.ai_enabled ? 'activada' : 'desactivada'}`} color={ai.data.ai_enabled ? t.colors.success : t.colors.danger} />
              <Badge label={`Ollama ${ai.data.ollama_reachable ? 'OK' : 'apagado'}`} color={ai.data.ollama_reachable ? t.colors.success : t.colors.danger} />
              <Body muted>{ai.data.ollama_model} · {ai.data.whisper_model}</Body>
            </Row>
          ) : hasPermission('ai.configure') ? (
            <Body muted>{ai.isLoading ? 'Consultando…' : 'Sin acceso al estado del asistente.'}</Body>
          ) : null}
        </Card>
      ) : null}

      <Card style={{ alignItems: 'center' }}>
        {t.isProductBrand ? <DentiaLogo width={180} /> : <PoweredByDentia />}
        <Body muted>
          Versión {Constants.expoConfig?.version} ({String(Constants.expoConfig?.extra?.variant)})
        </Body>
      </Card>

      <Button title="Cerrar sesión" variant="danger" onPress={confirmLogout} />
    </Screen>
  );
}
