import { useQueryClient } from '@tanstack/react-query';
import * as LocalAuthentication from 'expo-local-authentication';
import { usePreventScreenCapture } from 'expo-screen-capture';
import { useEffect, useRef } from 'react';
import { AppState, Image, View } from 'react-native';

import { Body, Button, Title } from '@/components/ui';
import { useSession } from '@/store/session';
import { BRAND_ASSETS, useTheme } from '@/theme/theme';

/**
 * Protección de datos clínicos en el teléfono:
 *  1. Impide capturas y grabación de pantalla (FLAG_SECURE en Android) mientras hay sesión.
 *     También oculta el contenido en la vista de "apps recientes".
 *  2. Si la app pasa más de LOCK_AFTER_MS en segundo plano, se bloquea, borra la caché
 *     de datos en memoria y pide huella/rostro/PIN del teléfono para continuar.
 */
const LOCK_AFTER_MS = 2 * 60 * 1000;

export function SecureScreen() {
  usePreventScreenCapture();
  return null;
}

export function useAutoLock() {
  const qc = useQueryClient();
  const backgroundedAt = useRef<number | null>(null);

  useEffect(() => {
    const sub = AppState.addEventListener('change', (next) => {
      const { accessToken, setLocked } = useSession.getState();
      if (!accessToken) return;
      if (next === 'background') backgroundedAt.current = Date.now();
      if (next === 'active' && backgroundedAt.current) {
        if (Date.now() - backgroundedAt.current > LOCK_AFTER_MS) {
          qc.clear();
          setLocked(true);
        }
        backgroundedAt.current = null;
      }
    });
    return () => sub.remove();
  }, [qc]);
}

export function LockScreen() {
  const t = useTheme();
  const { setLocked, clear } = useSession();

  const unlock = async () => {
    const hasHw = await LocalAuthentication.hasHardwareAsync();
    const enrolled = await LocalAuthentication.isEnrolledAsync();
    if (!hasHw || !enrolled) {
      // Sin biometría ni PIN configurado: por seguridad, volver a iniciar sesión
      await clear();
      return;
    }
    const res = await LocalAuthentication.authenticateAsync({
      promptMessage: 'Desbloquear DENT-IA',
      cancelLabel: 'Cancelar',
      disableDeviceFallback: false,
    });
    if (res.success) setLocked(false);
  };

  return (
    <View style={{ flex: 1, backgroundColor: t.colors.background, alignItems: 'center', justifyContent: 'center', padding: 24, gap: 16 }}>
      <Image source={BRAND_ASSETS.isotipo} style={{ width: 96, height: 96 }} accessible={false} />
      <Title>Sesión bloqueada</Title>
      <Body muted style={{ textAlign: 'center' }}>
        Por seguridad de los datos de tus pacientes, DENT-IA se bloquea cuando la dejas en segundo plano.
      </Body>
      <Button title="Desbloquear" big onPress={unlock} />
      <Button title="Cerrar sesión" variant="ghost" onPress={() => void clear()} />
    </View>
  );
}
