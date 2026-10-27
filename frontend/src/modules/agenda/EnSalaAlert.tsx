import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { canWriteRecords } from '../auth/roles'
import { useActiveRole, useAuthStore } from '../auth/store'
import * as api from './api'
import { addDays, formatTime, startOfDay, toDateKey } from './dateUtils'
import styles from './EnSalaAlert.module.css'

const POLL_INTERVAL_MS = 30000

/** Banner persistente, visible en toda la app (montado en app/Layout.tsx), que avisa
 * al odontologo/especialista cuando recepcion marca una cita propia como EN_SALA
 * (el paciente ya llego). No hay websockets en este proyecto -- se resuelve con
 * polling corto (ver CLAUDE.md seccion 7, catalogo configurable/decision pragmatica
 * similar): cada POLL_INTERVAL_MS se vuelve a preguntar por las citas de hoy de este
 * profesional en estado EN_SALA. El banner desaparece solo cuando la cita ya no esta
 * en ese estado (se inicio la atencion, se cancelo, etc.) porque el siguiente poll ya
 * no la trae. */
export function EnSalaAlert() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const activeRole = useActiveRole()
  const user = useAuthStore((s) => s.user)
  const canSeeAlert = canWriteRecords(activeRole) && !!user

  // No existe un endpoint "mi perfil de profesional" -- providers.user_id es el
  // vinculo entre el usuario logueado y su provider_id (ver backend/app/modules/
  // agenda/schemas.py::ProviderOut). ['providers'] es la misma clave que usa
  // AgendaPage, asi que si ya se visito la agenda esto no dispara una llamada extra.
  const providersQuery = useQuery({
    queryKey: ['providers'],
    queryFn: api.listProviders,
    enabled: canSeeAlert,
  })
  const providerId = providersQuery.data?.find((p) => p.user_id === user?.id)?.id ?? null

  const todayStart = startOfDay(new Date())
  const todayEnd = addDays(todayStart, 1)

  const appointmentsQuery = useQuery({
    queryKey: ['agenda-en-sala-alert', toDateKey(todayStart), providerId],
    queryFn: () =>
      api.listAppointments({
        startsFrom: todayStart.toISOString(),
        startsTo: todayEnd.toISOString(),
        providerId,
      }),
    enabled: canSeeAlert && !!providerId,
    refetchInterval: POLL_INTERVAL_MS,
  })

  // Igual que ResumenTab::startEncounterMutation (A4): sin useMutation, un error
  // (403, 500, red) deja el boton habilitado de nuevo sin explicar por que no paso
  // nada. Al no tener onError propio, cae en la red de seguridad global
  // (app/globalMutationErrorHandling.ts) que muestra el error igual que cualquier
  // otro boton de la aplicacion.
  const startEncounterMutation = useMutation({
    mutationFn: api.startEncounter,
    onSuccess: (encounter) => {
      queryClient.invalidateQueries({ queryKey: ['agenda-en-sala-alert'] })
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
      navigate(`/pacientes/${encounter.patient_id}/atencion/${encounter.id}`)
    },
  })

  if (!canSeeAlert || !providerId) return null

  const waitingPatients = (appointmentsQuery.data ?? []).filter((a) => a.status === 'EN_SALA')
  if (waitingPatients.length === 0) return null

  return (
    <div className={styles.banner} role="alert">
      <strong className={styles.title}>
        {waitingPatients.length === 1
          ? 'Paciente en sala de espera'
          : `${waitingPatients.length} pacientes en sala de espera`}
      </strong>
      <ul className={styles.list}>
        {waitingPatients.map((appointment) => (
          <li key={appointment.id} className={styles.item}>
            <span className={styles.patient}>
              {appointment.patient_full_name} · {formatTime(new Date(appointment.starts_at))}
            </span>
            <button
              className={styles.startButton}
              type="button"
              disabled={startEncounterMutation.isPending}
              onClick={() => startEncounterMutation.mutate(appointment.id)}
            >
              Iniciar atencion
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
