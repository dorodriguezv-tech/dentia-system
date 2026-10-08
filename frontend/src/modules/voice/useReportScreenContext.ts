import { useEffect } from 'react'
import { useScreenContextStore } from './screenContext'

/** Fase 13 ("Dentia"), 13.2: cada pantalla que tiene un paciente/atencion
 * activos lo declara aqui (p.ej. PatientDetailPage con la pestaña actual) --
 * useVoiceSession.ts lo manda al backend junto con la ruta cuando cambia. Al
 * desmontar, limpia el contexto (si uno sale del expediente, Dentia ya no
 * debe asumir que "el paciente" sigue siendo el mismo). */
export function useReportScreenContext(context: {
  patientId?: string | null
  encounterId?: string | null
  tab?: string | null
}): void {
  const setScreenContext = useScreenContextStore((s) => s.setScreenContext)
  const clearScreenContext = useScreenContextStore((s) => s.clearScreenContext)

  useEffect(() => {
    setScreenContext(context)
    return () => clearScreenContext()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [context.patientId, context.encounterId, context.tab])
}
