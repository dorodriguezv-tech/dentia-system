import { canReadOdontogram, canWriteOdontogram } from '../auth/roles'
import { useActiveRole } from '../auth/store'
import { Odontograma } from './Odontograma'

export function OdontogramaTab({ patientId }: { patientId: string }) {
  const activeRole = useActiveRole()

  if (!canReadOdontogram(activeRole)) {
    return <p>No tienes permiso para ver el odontograma.</p>
  }

  return <Odontograma patientId={patientId} canWrite={canWriteOdontogram(activeRole)} />
}
