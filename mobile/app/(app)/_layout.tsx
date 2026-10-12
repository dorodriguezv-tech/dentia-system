import { Ionicons } from '@expo/vector-icons';
import { Redirect, Tabs } from 'expo-router';

import { useSession } from '@/store/session';
import { useTheme } from '@/theme/theme';

export default function AppTabs() {
  const t = useTheme();
  const loggedIn = useSession((s) => !!s.accessToken);
  if (!loggedIn) return <Redirect href="/" />;

  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: t.colors.surface },
        headerTintColor: t.colors.text,
        tabBarActiveTintColor: t.colors.primary,
        tabBarInactiveTintColor: t.colors.textMuted,
        tabBarStyle: { backgroundColor: t.colors.surface, borderTopColor: t.colors.border, minHeight: 60 },
        tabBarLabelStyle: { fontSize: 12, fontWeight: '600' },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ title: 'Agenda', tabBarIcon: ({ color, size }) => <Ionicons name="calendar-outline" color={color} size={size} /> }}
      />
      <Tabs.Screen
        name="pacientes"
        options={{ title: 'Pacientes', tabBarIcon: ({ color, size }) => <Ionicons name="people-outline" color={color} size={size} /> }}
      />
      <Tabs.Screen
        name="dentia"
        options={{ title: 'Dentia', tabBarIcon: ({ color, size }) => <Ionicons name="mic-circle-outline" color={color} size={size + 4} /> }}
      />
      <Tabs.Screen
        name="ajustes"
        options={{ title: 'Ajustes', tabBarIcon: ({ color, size }) => <Ionicons name="settings-outline" color={color} size={size} /> }}
      />
    </Tabs>
  );
}
