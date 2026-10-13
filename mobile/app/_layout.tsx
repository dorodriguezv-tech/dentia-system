import { Montserrat_600SemiBold, Montserrat_700Bold, useFonts } from '@expo-google-fonts/montserrat';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState, type ReactNode } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { getBranding } from '@/api/endpoints';
import { OpenEncounterBanner } from '@/encounters/OpenEncounterBanner';
import { LockScreen, SecureScreen, useAutoLock } from '@/security/appLock';
import { useSession } from '@/store/session';
import { ThemeProvider, useTheme } from '@/theme/theme';
import { setPreferredVoice, setSpeechRate, setSpeechVolume } from '@/voice/dentiaVoice';

void SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  // La caché vive SOLO en memoria (sin persistQueryClient): ningún dato clínico a disco.
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 1, staleTime: 30_000, gcTime: 5 * 60_000, refetchOnWindowFocus: true },
          mutations: { retry: 0 },
        },
      }),
  );

  const hydrated = useSession((s) => s.hydrated);
  // Montserrat: tipografía de encabezados, la más cercana a la del logo DENT-IA.
  // Va empaquetada en la app; si fallara al cargar, se usa la tipografía del sistema.
  const [fontsLoaded, fontError] = useFonts({ Montserrat_600SemiBold, Montserrat_700Bold });
  const ready = hydrated && (fontsLoaded || !!fontError);
  useEffect(() => {
    void useSession.getState().hydrate();
  }, []);
  useEffect(() => {
    if (ready) void SplashScreen.hideAsync();
  }, [ready]);

  if (!ready) return null;

  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <BrandedTheme fontsLoaded={fontsLoaded}>
          <Shell />
        </BrandedTheme>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}

function BrandedTheme({ children, fontsLoaded }: { children: ReactNode; fontsLoaded: boolean }) {
  const serverUrl = useSession((s) => s.serverUrl);
  const themePreference = useSession((s) => s.preferences?.theme ?? 'system');
  const branding = useQuery({
    queryKey: ['branding', serverUrl],
    queryFn: getBranding,
    enabled: !!serverUrl,
    staleTime: 60 * 60_000,
  });
  return (
    <ThemeProvider branding={branding.data} fontsLoaded={fontsLoaded} themePreference={themePreference}>
      {children}
    </ThemeProvider>
  );
}

function Shell() {
  const t = useTheme();
  const locked = useSession((s) => s.locked);
  const loggedIn = useSession((s) => !!s.accessToken);
  const preferences = useSession((s) => s.preferences);
  useAutoLock();

  // M2: aplica la voz/velocidad/volumen guardados en cuanto llegan (login, reinicio
  // de la app o un cambio desde Ajustes), para que Dentia los respete sin reabrir nada.
  useEffect(() => {
    if (!preferences) return;
    setPreferredVoice(preferences.voice_id);
    setSpeechRate(preferences.speech_rate);
    setSpeechVolume(preferences.speech_volume);
  }, [preferences]);

  if (locked) return <LockScreen />;

  return (
    <>
      <StatusBar style={t.dark ? 'light' : 'dark'} />
      {loggedIn ? <SecureScreen /> : null}
      {loggedIn ? <OpenEncounterBanner /> : null}
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: t.colors.surface },
          headerTintColor: t.colors.text,
          headerTitleStyle: { fontWeight: '700', fontFamily: t.fonts.heading },
          contentStyle: { backgroundColor: t.colors.background },
        }}
      >
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="servidor" options={{ title: 'Servidor de la clínica' }} />
        <Stack.Screen name="login" options={{ headerShown: false }} />
        <Stack.Screen name="sucursal" options={{ title: 'Elige sucursal', headerBackVisible: false }} />
        <Stack.Screen name="(app)" options={{ headerShown: false }} />
        <Stack.Screen name="paciente/[id]" options={{ title: 'Paciente' }} />
        <Stack.Screen name="atencion/[id]" options={{ title: 'Atención y dictado' }} />
      </Stack>
    </>
  );
}
