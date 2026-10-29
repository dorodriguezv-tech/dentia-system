import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import * as catalogsApi from '../catalogs/api'
import { STATUS_LABELS } from './catalog'
import { formatTime } from './dateUtils'
import styles from './NewAppointmentForm.module.css'
import type { AppointmentListItemOut, AppointmentStatus } from './types'

function ReasonAction({
  label,
  onConfirm,
  pending,
}: {
  label: string
  onConfirm: (reason: string) => void
  pending: boolean
}) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')

  if (!open) {
    return (
      <button type="button" className={styles.submitButton} onClick={() => setOpen(true)}>
        {label}
      </button>
    )
  }
  return (
    <span className={styles.actionsRow}>
      <input
        type="text"
        placeholder="Motivo"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <button
        type="button"
        className={styles.submitButton}
        disabled={!reason.trim() || pending}
        onClick={() => onConfirm(reason)}
      >
        Confirmar
      </button>
    </span>
  )
}

interface AppointmentDetailPanelProps {
  appointment: AppointmentListItemOut
  canWrite: boolean
  canStartEncounter: boolean
  pending: boolean
  onClose: () => void
  onChangeStatus: (status: AppointmentStatus, reason?: string) => void
  onStartEncounter: () => void
  onReschedule: (date: Date, hour: number, minute: number) => void
}

export function AppointmentDetailPanel({
  appointment,
  canWrite,
  canStartEncounter,
  pending,
  onClose,
  onChangeStatus,
  onStartEncounter,
  onReschedule,
}: AppointmentDetailPanelProps) {
  const [rescheduling, setRescheduling] = useState(false)
  const start = new Date(appointment.starts_at)
  const end = new Date(appointment.ends_at)
  const [newDate, setNewDate] = useState(start.toISOString().slice(0, 10))
  const [newTime, setNewTime] = useState(formatTime(start))

  const status = appointment.status

  // B1 (Parte B, Fase 12.2): el nombre del tipo de cita vive en el catalogo
  // administrable -- si se desactivo despues de agendar esta cita, igual se
  // sigue mostrando (comparte el cache con NewAppointmentForm.tsx, mismo query key).
  const appointmentTypesQuery = useQuery({
    queryKey: ['catalog-items', 'appointment_type'],
    queryFn: () => catalogsApi.listCatalogItems('appointment_type', false),
  })
  const appointmentTypeName =
    appointmentTypesQuery.data?.find((item) => item.code === appointment.appointment_type)
      ?.name ?? appointment.appointment_type

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h3>{appointment.patient_full_name}</h3>
        <button className={styles.closeButton} type="button" onClick={onClose}>
          Cerrar
        </button>
      </div>
      <p className={styles.when}>
        {start.toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long' })},{' '}
        {formatTime(start)}–{formatTime(end)}
      </p>
      <p>
        {appointmentTypeName} con {appointment.provider_full_name}
        {appointment.resource_name && ` · ${appointment.resource_name}`}
      </p>
      <p>
        Estado: <strong>{STATUS_LABELS[status]}</strong>
      </p>

      {canWrite && (status === 'RESERVADA' || status === 'CONFIRMADA' || status === 'EN_SALA') && (
        <div className={styles.actionsRow}>
          {status === 'RESERVADA' && (
            <button
              type="button"
              className={styles.submitButton}
              disabled={pending}
              onClick={() => onChangeStatus('CONFIRMADA')}
            >
              Confirmar
            </button>
          )}
          {status !== 'EN_SALA' && (
            <button
              type="button"
              className={styles.submitButton}
              disabled={pending}
              onClick={() => onChangeStatus('EN_SALA')}
            >
              Pasar a sala
            </button>
          )}
          {canStartEncounter && (
            <button
              type="button"
              className={styles.submitButton}
              disabled={pending}
              onClick={onStartEncounter}
            >
              Iniciar atencion
            </button>
          )}
          <ReasonAction
            label="No se presento"
            pending={pending}
            onConfirm={(reason) => onChangeStatus('NO_SHOW', reason)}
          />
          <ReasonAction
            label="Cancelar"
            pending={pending}
            onConfirm={(reason) => onChangeStatus('CANCELADA', reason)}
          />
        </div>
      )}

      {canWrite && status === 'EN_ATENCION' && (
        <button
          type="button"
          className={styles.submitButton}
          disabled={pending}
          onClick={() => onChangeStatus('TERMINADA')}
        >
          Terminar
        </button>
      )}

      {canWrite && (status === 'RESERVADA' || status === 'CONFIRMADA') && (
        <div>
          {!rescheduling ? (
            <button type="button" className={styles.submitButton} onClick={() => setRescheduling(true)}>
              Reprogramar
            </button>
          ) : (
            <div className={styles.actionsRow}>
              {/* El backend rechaza un horario pasado (PAST_TIME_SLOT); `min` aqui solo
                  evita que la fecha parezca una opcion valida en el selector nativo,
                  igual criterio que el sombreado de CalendarGrid.tsx. */}
              <input
                type="date"
                min={new Date().toISOString().slice(0, 10)}
                value={newDate}
                onChange={(e) => setNewDate(e.target.value)}
              />
              <input type="time" value={newTime} onChange={(e) => setNewTime(e.target.value)} />
              <button
                type="button"
                className={styles.submitButton}
                disabled={pending}
                onClick={() => {
                  const [hour, minute] = newTime.split(':').map(Number)
                  onReschedule(new Date(`${newDate}T00:00:00`), hour, minute)
                }}
              >
                Confirmar nuevo horario
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
