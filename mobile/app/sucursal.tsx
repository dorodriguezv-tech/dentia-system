import { router } from 'expo-router';

import { Body, Card, Empty, Screen, Title } from '@/components/ui';
import { useSession } from '@/store/session';

export default function SucursalScreen() {
  const clinics = useSession((s) => s.clinics);

  const choose = async (id: string) => {
    await useSession.getState().setClinic(id);
    router.replace('/(app)');
  };

  return (
    <Screen>
      <Title>¿En qué sucursal trabajas hoy?</Title>
      {clinics.length === 0 ? <Empty>Tu usuario no tiene sucursales asignadas. Pide acceso al administrador.</Empty> : null}
      {clinics.map((c) => (
        <Card key={c.clinic_id} onPress={() => void choose(c.clinic_id)}>
          <Body style={{ fontWeight: '700' }}>{c.clinic_name}</Body>
          <Body muted>{c.role}</Body>
        </Card>
      ))}
    </Screen>
  );
}
