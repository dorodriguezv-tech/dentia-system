import { router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, Text, View } from 'react-native';

import { errorMessage } from '@/api/client';
import { getMe, getMyClinics, login, loginMfa } from '@/api/endpoints';
import { BrandStripe, ClinicLogo, PoweredByDentia } from '@/components/Brand';
import { Body, Button, ErrorBox, Field, Screen, Title } from '@/components/ui';
import { useSession } from '@/store/session';
import { useTheme } from '@/theme/theme';

export default function LoginScreen() {
  const t = useTheme();
  const serverUrl = useSession((s) => s.serverUrl);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const finish = async (access: string, refresh: string) => {
    await useSession.getState().setTokens(access, refresh);
    const [me, clinics] = await Promise.all([getMe(), getMyClinics()]);
    useSession.getState().setProfile(me, clinics);
    if (clinics.length === 1 && clinics[0]) {
      await useSession.getState().setClinic(clinics[0].clinic_id);
      router.replace('/(app)');
    } else {
      router.replace('/sucursal');
    }
  };

  const submit = async () => {
    setError(null);
    setLoading(true);
    try {
      if (mfaToken) {
        const pair = await loginMfa(mfaToken, code.trim());
        await finish(pair.access_token, pair.refresh_token);
        return;
      }
      const res = await login(email.trim().toLowerCase(), password);
      if (res.mfa_required && res.mfa_token) {
        setMfaToken(res.mfa_token);
        return;
      }
      if (!res.access_token || !res.refresh_token) {
        throw new Error('El servidor no devolvió el token de sesión para la app (ver docs/05 §7, cambio B1).');
      }
      await finish(res.access_token, res.refresh_token);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Screen>
        <View style={{ alignItems: 'center', marginTop: 40, gap: 12 }}>
          <ClinicLogo serverUrl={serverUrl} width={240} />
          {/* El logo DENT-IA ya incluye nombre y lema; solo se escribe el nombre si la clínica usa su propia marca */}
          {!t.isProductBrand ? <Title>{t.clinicName}</Title> : null}
          <Body muted style={{ textAlign: 'center' }}>
            La IA captura, organiza y documenta. Tú te concentras en el paciente.
          </Body>
        </View>
        <BrandStripe />

        {!mfaToken ? (
          <>
            <Field
              label="Correo"
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              autoComplete="email"
              keyboardType="email-address"
              textContentType="username"
            />
            <Field
              label="Contraseña"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoComplete="password"
              textContentType="password"
              onSubmitEditing={submit}
            />
          </>
        ) : (
          <>
            <Body>Escribe el código de 6 dígitos de tu app autenticadora.</Body>
            <Field
              label="Código de verificación"
              value={code}
              onChangeText={(v) => setCode(v.replace(/\D/g, '').slice(0, 6))}
              keyboardType="number-pad"
              autoComplete="one-time-code"
              textContentType="oneTimeCode"
              maxLength={6}
              onSubmitEditing={submit}
            />
          </>
        )}

        {error ? <ErrorBox message={error} /> : null}
        <Button
          title={mfaToken ? 'Verificar' : 'Entrar'}
          onPress={submit}
          loading={loading}
          disabled={mfaToken ? code.length !== 6 : !email || !password}
          big
        />
        <Pressable onPress={() => router.push('/servidor')} accessibilityRole="link" style={{ padding: 12, alignItems: 'center' }}>
          <Text style={{ color: t.colors.primary }}>Servidor: {serverUrl ?? 'sin configurar'} · Cambiar</Text>
        </Pressable>
        {!t.isProductBrand ? <PoweredByDentia /> : null}
      </Screen>
    </KeyboardAvoidingView>
  );
}
