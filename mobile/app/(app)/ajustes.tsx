import { useQuery, useQueryClient } from '@tanstack/react-query';
import Constants from 'expo-constants';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';

import { getAiStatus, logout } from '@/api/endpoints';
import { DentiaLogo, PoweredByDentia } from '@/components/Brand';
import { Badge, Body, Button, Card, Row, Screen, Title } from '@/components/ui';
import { hasPermission, useSession } from '@/store/session';
import { useTheme } from '@/theme/theme';
import { listSpanishVoices, say, setPreferredVoice } from '@/voice/dentiaVoice';

export default function AjustesScreen() {
  const t = useTheme();
  const qc = useQueryClient();
  const { me, clinics, clinicId, serverUrl, refreshToken } = useSession();
  const clinic = clinics.find((c) => c.clinic_id === clinicId);
  const [voices, setVoices] = useState<{ id: string; label: string }[]>([]);
  const [voiceId, setVoiceId] = useState<string | null>(null);

  const ai = useQuery({ queryKey: ['ai-status'], queryFn: getAiStatus, enabled: hasPermission('ai.configure') });

  useEffect(() => {
    listSpanishVoices()
      .then((vs) => setVoices(vs.map((v) => ({ id: v.identifier, label: `${v.name} (${v.language})${/network/i.test(v.identifier) ? ' · en línea' : ''}` }))))
      .catch(() => setVoices([]));
  }, []);

  const doLogout = async () => {
    if (refreshToken) await logout(refreshToken);
    qc.clear();
    await useSession.getState().clear();
    router.replace('/login');
  };

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
        <Title>Asistente de IA</Title>
        {ai.data ? (
          <Row>
            <Badge label={`IA ${ai.data.ai_enabled ? 'activada' : 'desactivada'}`} color={ai.data.ai_enabled ? t.colors.success : t.colors.danger} />
            <Badge label={`Ollama ${ai.data.ollama_reachable ? 'OK' : 'apagado'}`} color={ai.data.ollama_reachable ? t.colors.success : t.colors.danger} />
            <Body muted>{ai.data.ollama_model} · {ai.data.whisper_model}</Body>
          </Row>
        ) : (
          <Body muted>{ai.isLoading ? 'Consultando…' : 'Sin acceso al estado del asistente.'}</Body>
        )}
      </Card>

      <Card>
        <Title>Voz de Dentia</Title>
        <Body muted>Se prefieren voces instaladas en el teléfono (sin internet). Si no hay voz en español, instala “Datos de voz” en Ajustes de Android → Texto a voz.</Body>
        {voices.slice(0, 8).map((v) => (
          <Button
            key={v.id}
            title={`${voiceId === v.id ? '✓ ' : ''}${v.label}`}
            variant={voiceId === v.id ? 'secondary' : 'ghost'}
            onPress={() => {
              setVoiceId(v.id);
              setPreferredVoice(v.id);
              void say('Hola, soy Dentia. ¿En qué te ayudo?');
            }}
          />
        ))}
      </Card>

      <Card style={{ alignItems: 'center' }}>
        {t.isProductBrand ? <DentiaLogo width={180} /> : <PoweredByDentia />}
        <Body muted>Servidor: {serverUrl}</Body>
        <Body muted>
          Versión {Constants.expoConfig?.version} ({String(Constants.expoConfig?.extra?.variant)})
        </Body>
      </Card>

      <Button title="Cerrar sesión" variant="danger" onPress={() => void doLogout()} />
    </Screen>
  );
}
