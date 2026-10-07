import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { canReadAgenda, canWriteAgenda, canWriteRecords } from '../auth/roles'
import { useActiveRole } from '../auth/store'
import * as api from './api'
import styles from './AgendaPage.module.css'
import { AppointmentDetailPanel } from './AppointmentDetailPanel'
import { CalendarGrid } from './CalendarGrid'
import {
  addDays,
  combineDateAndTime,
  monthGridDays,
  startOfDay,
  startOfMonth,
  startOfWeek,
  toDateKey,
} from './dateUtils'
import { MonthGrid } from './MonthGrid'
import { NewAppointmentForm } from './NewAppointmentForm'
import type { AppointmentListItemOut, AppointmentStatus } from './types'

type ViewMode = 'dia' | 'semana' | 'mes'
type GroupBy = 'profesional' | 'gabinete'
type ActivePanel =
  | { type: 'new'; date: Date; hour: number; minute: number }
  | { type: 'detail'; appointment: AppointmentListItemOut }
  | null

export function AgendaPage() {
  const activeRole = useActiveRole()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [viewMode, setViewMode] = useState<ViewMode>('semana')
  const [groupBy, setGroupBy] = useState<GroupBy>('profesional')
  const [anchorDate, setAnchorDate] = useState(() => startOfDay(new Date()))
  const [selectedProviderId, setSelectedProviderId] = useState('')
  const [selectedResourceId, setSelectedResourceId] = useState('')
  const [panel, setPanel] = useState<ActivePanel>(null)

  const providersQuery = useQuery({ queryKey: ['providers'], queryFn: api.listProviders })
  const resourcesQuery = useQuery({ queryKey: ['resources'], queryFn: () => api.listResources() })

  const effectiveProviderId = selectedProviderId || providersQuery.data?.[0]?.id || ''

  const dates = useMemo(() => {
    if (viewMode === 'dia') return [anchorDate]
    if (viewMode === 'semana') {
      const start = startOfWeek(anchorDate)
      return Array.from({ length: 7 }, (_, i) => addDays(start, i))
    }
    return monthGridDays(anchorDate)
  }, [viewMode, anchorDate])

  const startsFrom = dates[0]
  const startsTo = addDays(dates[dates.length - 1], 1)

  const appointmentsQuery = useQuery({
    queryKey: [
      'appointments',
      toDateKey(startsFrom),
      toDateKey(startsTo),
      groupBy === 'profesional' ? effectiveProviderId : null,
      groupBy === 'gabinete' ? selectedResourceId : null,
    ],
    queryFn: () =>
      api.listAppointments({
        startsFrom: startsFrom.toISOString(),
        startsTo: startsTo.toISOString(),
        providerId: groupBy === 'profesional' ? effectiveProviderId || null : null,
        resourceId: groupBy === 'gabinete' ? selectedResourceId || null : null,
      }),
    enabled: groupBy === 'profesional' ? !!effectiveProviderId : !!selectedResourceId,
  })

  function invalidateAppointments() {
    queryClient.invalidateQueries({ queryKey: ['appointments'] })
  }

  const createMutation = useMutation({
    mutationFn: api.createAppointment,
    onSuccess: () => {
      invalidateAppointments()
      setPanel(null)
    },
  })

  const statusMutation = useMutation({
    mutationFn: ({
      id,
      status,
      reason,
    }: {
      id: string
      status: AppointmentStatus
      reason?: string
    }) => api.changeAppointmentStatus(id, { status, reason }),
    onSuccess: () => {
      invalidateAppointments()
      setPanel(null)
    },
  })

  const rescheduleMutation = useMutation({
    mutationFn: ({ id, starts_at }: { id: string; starts_at: string }) =>
      api.rescheduleAppointment(id, { starts_at }),
    onSuccess: () => {
      invalidateAppointments()
      setPanel(null)
    },
  })

  const startEncounterMutation = useMutation({
    mutationFn: api.startEncounter,
    onSuccess: (encounter) => {
      invalidateAppointments()
      navigate(`/pacientes/${encounter.patient_id}/atencion/${encounter.id}`)
    },
  })

  if (!canReadAgenda(activeRole)) {
    return <p>No tienes permiso para ver la agenda.</p>
  }
  const canWrite = canWriteAgenda(activeRole)
  const canStartEncounter = canWriteRecords(activeRole)

  function navigateAnchor(direction: 1 | -1) {
    if (viewMode === 'dia') setAnchorDate((d) => addDays(d, direction))
    else if (viewMode === 'semana') setAnchorDate((d) => addDays(d, 7 * direction))
    else {
      const d = new Date(anchorDate)
      d.setMonth(d.getMonth() + direction)
      setAnchorDate(startOfDay(d))
    }
  }

  const appointments = appointmentsQuery.data ?? []

  return (
    <section className={styles.page}>
      <h1>Agenda</h1>

      <div className={styles.controls}>
        <div className={styles.viewToggle}>
          {(['dia', 'semana', 'mes'] as ViewMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              className={viewMode === mode ? styles.toggleActive : styles.toggle}
              onClick={() => setViewMode(mode)}
            >
              {mode === 'dia' ? 'Dia' : mode === 'semana' ? 'Semana' : 'Mes'}
            </button>
          ))}
        </div>

        <div className={styles.nav}>
          <button type="button" className={styles.toggle} onClick={() => navigateAnchor(-1)}>
            Anterior
          </button>
          <button
            type="button"
            className={styles.toggle}
            onClick={() => setAnchorDate(startOfDay(new Date()))}
          >
            Hoy
          </button>
          <button type="button" className={styles.toggle} onClick={() => navigateAnchor(1)}>
            Siguiente
          </button>
        </div>

        <div className={styles.groupBy}>
          {(['profesional', 'gabinete'] as GroupBy[]).map((mode) => (
            <button
              key={mode}
              type="button"
              className={groupBy === mode ? styles.toggleActive : styles.toggle}
              onClick={() => setGroupBy(mode)}
            >
              {mode === 'profesional' ? 'Por profesional' : 'Por gabinete'}
            </button>
          ))}
        </div>

        {groupBy === 'profesional' ? (
          <select
            aria-label="Profesional"
            value={effectiveProviderId}
            onChange={(e) => setSelectedProviderId(e.target.value)}
          >
            {providersQuery.data?.map((provider) => (
              <option key={provider.id} value={provider.id}>
                {provider.full_name}
              </option>
            ))}
          </select>
        ) : (
          <select
            aria-label="Gabinete"
            value={selectedResourceId}
            onChange={(e) => setSelectedResourceId(e.target.value)}
          >
            <option value="">Selecciona un gabinete...</option>
            {resourcesQuery.data?.map((resource) => (
              <option key={resource.id} value={resource.id}>
                {resource.name}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className={styles.body}>
        <div className={styles.calendar}>
          {viewMode === 'mes' ? (
            <MonthGrid
              days={dates}
              month={startOfMonth(anchorDate)}
              appointments={appointments}
              onDayClick={(day) => {
                setAnchorDate(day)
                setViewMode('dia')
              }}
            />
          ) : (
            <CalendarGrid
              dates={dates}
              appointments={appointments}
              onSlotClick={(date, hour, minute) => {
                if (canWrite) setPanel({ type: 'new', date, hour, minute })
              }}
              onDropAppointment={(appointmentId, date, hour, minute) => {
                if (!canWrite) return
                rescheduleMutation.mutate({
                  id: appointmentId,
                  starts_at: combineDateAndTime(date, hour, minute).toISOString(),
                })
              }}
              onAppointmentClick={(appointment) => setPanel({ type: 'detail', appointment })}
            />
          )}
        </div>

        {panel?.type === 'new' && providersQuery.data && (
          <NewAppointmentForm
            date={panel.date}
            hour={panel.hour}
            minute={panel.minute}
            providers={providersQuery.data}
            resources={resourcesQuery.data ?? []}
            defaultProviderId={effectiveProviderId}
            pending={createMutation.isPending}
            onClose={() => setPanel(null)}
            onSubmit={(data) => createMutation.mutate(data)}
          />
        )}

        {panel?.type === 'detail' && (
          <AppointmentDetailPanel
            appointment={panel.appointment}
            canWrite={canWrite}
            canStartEncounter={canStartEncounter}
            pending={
              statusMutation.isPending ||
              startEncounterMutation.isPending ||
              rescheduleMutation.isPending
            }
            onClose={() => setPanel(null)}
            onChangeStatus={(status, reason) =>
              statusMutation.mutate({ id: panel.appointment.id, status, reason })
            }
            onStartEncounter={() => startEncounterMutation.mutate(panel.appointment.id)}
            onReschedule={(date, hour, minute) =>
              rescheduleMutation.mutate({
                id: panel.appointment.id,
                starts_at: combineDateAndTime(date, hour, minute).toISOString(),
              })
            }
          />
        )}
      </div>
    </section>
  )
}
