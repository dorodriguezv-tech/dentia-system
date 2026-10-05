import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../api/health'

export function HomePage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['health'], queryFn: getHealth })

  return (
    <section>
      <h1>Bienvenido a DentalCare</h1>
      <p>
        Estado de la API:{' '}
        {isLoading ? 'consultando...' : isError ? 'sin conexion' : (data?.status ?? 'desconocido')}
      </p>
    </section>
  )
}
