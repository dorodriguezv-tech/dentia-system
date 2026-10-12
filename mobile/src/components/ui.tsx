import type { ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type StyleProp,
  type TextInputProps,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { ClinicalAlert } from '@/api/types';
import { useTheme } from '@/theme/theme';

/** Objetivo táctil mínimo: 48 dp (Android) — guantes de látex incluidos. */
export const TOUCH = 48;

export function Screen({ children, scroll = true, padded = true }: { children: ReactNode; scroll?: boolean; padded?: boolean }) {
  const t = useTheme();
  const inner = <View style={{ padding: padded ? t.space(4) : 0, gap: t.space(3), flexGrow: 1 }}>{children}</View>;
  return (
    <SafeAreaView edges={['bottom', 'left', 'right']} style={{ flex: 1, backgroundColor: t.colors.background }}>
      {scroll ? <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ flexGrow: 1 }}>{inner}</ScrollView> : inner}
    </SafeAreaView>
  );
}

export function Title({ children }: { children: ReactNode }) {
  const t = useTheme();
  return (
    <Text accessibilityRole="header" style={{ fontSize: 22, fontWeight: '700', fontFamily: t.fonts.heading, color: t.colors.text }}>
      {children}
    </Text>
  );
}

export function Body({ children, muted, style }: { children: ReactNode; muted?: boolean; style?: StyleProp<any> }) {
  const t = useTheme();
  return <Text style={[{ fontSize: 16, color: muted ? t.colors.textMuted : t.colors.text, lineHeight: 22 }, style]}>{children}</Text>;
}

export function Card({ children, style, onPress }: { children: ReactNode; style?: StyleProp<ViewStyle>; onPress?: () => void }) {
  const t = useTheme();
  const base: ViewStyle = {
    backgroundColor: t.colors.surface,
    borderRadius: t.radius,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: t.colors.border,
    padding: t.space(4),
    gap: t.space(2),
  };
  if (!onPress) return <View style={[base, style]}>{children}</View>;
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={({ pressed }) => [base, style, pressed && { opacity: 0.7 }]}>
      {children}
    </Pressable>
  );
}

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';

export function Button({
  title,
  onPress,
  variant = 'primary',
  loading,
  disabled,
  icon,
  big,
  accessibilityHint,
}: {
  title: string;
  onPress: () => void;
  variant?: Variant;
  loading?: boolean;
  disabled?: boolean;
  icon?: ReactNode;
  big?: boolean;
  accessibilityHint?: string;
}) {
  const t = useTheme();
  const bg =
    variant === 'primary' ? t.colors.primary : variant === 'danger' ? t.colors.danger : variant === 'secondary' ? t.colors.primarySoft : 'transparent';
  const fg = variant === 'primary' || variant === 'danger' ? t.colors.onPrimary : t.colors.primary;
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      accessibilityRole="button"
      accessibilityLabel={title}
      accessibilityHint={accessibilityHint}
      accessibilityState={{ disabled: disabled || loading, busy: loading }}
      style={({ pressed }) => ({
        minHeight: big ? 64 : TOUCH,
        borderRadius: t.radius,
        backgroundColor: bg,
        paddingHorizontal: t.space(4),
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'row',
        gap: t.space(2),
        opacity: disabled ? 0.45 : pressed ? 0.8 : 1,
        borderWidth: variant === 'ghost' ? 1 : 0,
        borderColor: t.colors.border,
      })}
    >
      {loading ? <ActivityIndicator color={fg} /> : icon}
      <Text style={{ color: fg, fontSize: big ? 18 : 16, fontWeight: '600' }}>{title}</Text>
    </Pressable>
  );
}

export function Field({ label, error, ...props }: TextInputProps & { label: string; error?: string }) {
  const t = useTheme();
  return (
    <View style={{ gap: t.space(1) }}>
      <Text style={{ color: t.colors.text, fontWeight: '600' }}>{label}</Text>
      <TextInput
        placeholderTextColor={t.colors.textMuted}
        accessibilityLabel={label}
        style={{
          minHeight: TOUCH,
          borderWidth: 1,
          borderColor: error ? t.colors.danger : t.colors.border,
          borderRadius: t.radius,
          paddingHorizontal: t.space(3),
          color: t.colors.text,
          backgroundColor: t.colors.surface,
          fontSize: 16,
        }}
        {...props}
      />
      {error ? <Text style={{ color: t.colors.danger }}>{error}</Text> : null}
    </View>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const t = useTheme();
  return (
    <View accessibilityRole="alert" style={{ backgroundColor: t.colors.dangerSoft, borderRadius: t.radius, padding: t.space(3), gap: t.space(2) }}>
      <Text style={{ color: t.colors.danger, fontWeight: '600' }}>{message}</Text>
      {onRetry ? <Button title="Reintentar" variant="ghost" onPress={onRetry} /> : null}
    </View>
  );
}

export function Loading({ label = 'Cargando…' }: { label?: string }) {
  const t = useTheme();
  return (
    <View style={{ padding: t.space(6), alignItems: 'center', gap: t.space(2) }}>
      <ActivityIndicator color={t.colors.primary} />
      <Body muted>{label}</Body>
    </View>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  const t = useTheme();
  return (
    <View style={{ padding: t.space(6), alignItems: 'center' }}>
      <Body muted>{children}</Body>
    </View>
  );
}

export function Badge({ label, color }: { label: string; color: string }) {
  return (
    <View style={{ alignSelf: 'flex-start', backgroundColor: color, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 3 }}>
      <Text style={{ color: '#FFFFFF', fontSize: 12, fontWeight: '700' }}>{label}</Text>
    </View>
  );
}

/** Barra de alertas clínicas: siempre visible arriba de la ficha (regla 8).
 * El backend manda texto plano (sin tipo ni severidad estructurados todavía). */
export function AlertBar({ alerts }: { alerts: ClinicalAlert[] }) {
  const t = useTheme();
  if (!alerts.length) return null;
  return (
    <View
      accessibilityRole="alert"
      accessibilityLabel={`Alertas clínicas: ${alerts.join(', ')}`}
      style={{ backgroundColor: t.colors.dangerSoft, borderLeftWidth: 4, borderLeftColor: t.colors.danger, borderRadius: t.radius, padding: t.space(3), gap: 4 }}
    >
      <Text style={{ color: t.colors.danger, fontWeight: '800' }}>⚠ Alertas clínicas</Text>
      {alerts.map((a, i) => (
        <Text key={`${a}-${i}`} style={{ color: t.colors.text }}>
          • {a}
        </Text>
      ))}
    </View>
  );
}

export function Row({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[{ flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' }, style]}>{children}</View>;
}
