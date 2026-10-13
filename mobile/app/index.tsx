import { Redirect } from 'expo-router';
import { useEffect, useState } from 'react';

import { refreshAccessToken } from '@/api/client';
import { getMe, getMyClinics, getPreferences } from '@/api/endpoints';
import { Loading, Screen } from '@/components/ui';
import { useSession } from '@/store/session';

/**
 * Puerta de entrada: decide a qué pantalla ir.
 *   sin servidor → /servidor
 *   con refresh token guardado → intenta renovar la sesión en silencio
 *   sin sesión → /login
 *   sin sucursal elegida (o ya no válida) → /sucursal
 *   todo listo → agenda
 */
export default function Gate() {
  const { serverUrl, accessToken, refreshToken, clinicId, clinics } = useSession();
  const [checking, setChecking] = useState(!!refreshToken && !accessToken);

  useEffect(() => {
    if (!refreshToken || accessToken) return;
    let alive = true;
    (async () => {
      const ok = await refreshAccessToken();
      if (ok) {
        try {
          const [me, cl, prefs] = await Promise.all([getMe(), getMyClinics(), getPreferences()]);
          useSession.getState().setProfile(me, cl);
          useSession.getState().setPreferences(prefs);
        } catch {
          await useSession.getState().clear();
        }
      } else {
        await useSession.getState().clear();
      }
      if (alive) setChecking(false);
    })();
    return () => {
      alive = false;
    };
  }, [refreshToken, accessToken]);

  if (!serverUrl) return <Redirect href="/servidor" />;
  if (checking) {
    return (
      <Screen topSafe>
        <Loading label="Conectando con la clínica…" />
      </Screen>
    );
  }
  if (!accessToken) return <Redirect href="/login" />;
  const clinicValid = clinics.some((c) => c.clinic_id === clinicId);
  if (!clinicValid) return <Redirect href="/sucursal" />;
  return <Redirect href="/(app)" />;
}
