import Constants from 'expo-constants';
import { router } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { errorMessage } from '@/api/client';
import { getHealth } from '@/api/endpoints';
import { DentiaLogo } from '@/components/Brand';
import { Body, Button, Card, ErrorBox, Field, Screen, Title } from '@/components/ui';
import { normalizeServerUrl, useSession } from '@/store/session';

/**
 * Configuración del servidor de la clínica. La app no trae una URL fija porque cada
 * clínica tiene su propio servidor (todo corre en la red de la clínica, docs/02 §1).
 */
export default function ServidorScreen() {
  const current = useSession((s) => s.serverUrl);
  const [url, setUrl] = useState(current ?? '');
  const [error, setError] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const isDevBuild = Constants.expoConfig?.extra?.variant === 'development';

  const save = async () => {
    setError(null);
    const clean = normalizeServerUrl(url);
    if (!isDevBuild && clean.startsWith('http://')) {
      setError('Por seguridad, esta versión solo acepta direcciones https://.');
      return;
    }
    setTesting(true);
    const previous = useSession.getState().serverUrl;
    try {
      await useSession.getState().setServerUrl(clean);
      await getHealth();
      router.replace('/login');
    } catch (e) {
      if (previous) await useSession.getState().setServerUrl(previous);
      setError(`${errorMessage(e)}\nRevisa la dirección y que el teléfono esté en la red de la clínica.`);
    } finally {
      setTesting(false);
    }
  };

  return (
    <Screen>
      <View style={{ alignItems: 'center', paddingVertical: 8 }}>
        <DentiaLogo width={200} />
      </View>
      <Title>¿Dónde está tu servidor DENT-IA?</Title>
      <Body muted>Pide la dirección al administrador de la clínica. Ejemplos:</Body>
      <Card>
        <Body>• https://dentia.miclinica.mx</Body>
        <Body>• https://servidor-clinica.tu-red.ts.net (Tailscale)</Body>
        {isDevBuild ? <Body>• http://192.168.1.50:8001 (solo en pruebas)</Body> : null}
      </Card>
      <Field
        label="Dirección del servidor"
        value={url}
        onChangeText={setUrl}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        placeholder="https://"
        onSubmitEditing={save}
      />
      {error ? <ErrorBox message={error} /> : null}
      <Button title="Probar y guardar" onPress={save} loading={testing} disabled={!url.trim()} big />
    </Screen>
  );
}
