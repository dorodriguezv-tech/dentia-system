import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';

import { errorMessage } from '@/api/client';
import { searchPatients } from '@/api/endpoints';
import { Body, Card, Empty, ErrorBox, Field, Loading, Screen } from '@/components/ui';

export default function PacientesScreen() {
  const [text, setText] = useState('');
  const [q, setQ] = useState('');

  // Búsqueda tolerante (pg_trgm + unaccent en el backend) con espera de 300 ms
  useEffect(() => {
    const id = setTimeout(() => setQ(text.trim()), 300);
    return () => clearTimeout(id);
  }, [text]);

  const res = useQuery({
    queryKey: ['patients-search', q],
    queryFn: () => searchPatients(q),
    enabled: q.length >= 2,
  });

  return (
    <Screen>
      <Field
        label="Buscar paciente"
        placeholder="Nombre, apellido o número de expediente"
        value={text}
        onChangeText={setText}
        autoCorrect={false}
        returnKeyType="search"
      />
      {q.length < 2 ? <Empty>Escribe al menos 2 letras. También puedes decirle a Dentia: “abre el expediente de …”.</Empty> : null}
      {res.isFetching ? <Loading label="Buscando…" /> : null}
      {res.error ? <ErrorBox message={errorMessage(res.error)} /> : null}
      {res.data && res.data.length === 0 ? <Empty>Sin resultados para “{q}”.</Empty> : null}
      {res.data?.map((p) => (
        <Card key={p.id} onPress={() => router.push({ pathname: '/paciente/[id]', params: { id: p.id } })}>
          <Body style={{ fontWeight: '700' }}>{p.full_name}</Body>
          <Body muted>
            Exp. {p.expediente_number} · Nac. {p.date_of_birth}
            {p.status !== 'activo' ? ` · ${p.status}` : ''}
          </Body>
        </Card>
      ))}
    </Screen>
  );
}
