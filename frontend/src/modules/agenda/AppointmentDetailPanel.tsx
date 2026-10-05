import { useState } from 'react'
import { APPOINTMENT_TYPES, STATUS_LABELS } from './catalog'
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
        {APPOINTMENT_TYPES[appointment.appointment_type].label} con {appointment.provider_full_name}
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
              <input type="date" value={newDate} onChange={(e) => setNewDate(e.target.value)} />
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
