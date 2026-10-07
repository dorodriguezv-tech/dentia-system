import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { canWritePatients } from '../auth/roles'
import { useActiveRole } from '../auth/store'
import * as api from './api'
import styles from './PatientsListPage.module.css'
import { STATUS_LABELS, type StatusCode } from './types'

// B3 (Parte B, Fase 12.2): copia minima de agenda/rules.py::PROVIDER_ROLES --
// solo estos roles pueden tener pacientes propios (via primary_provider_id).
const PROVIDER_ROLE_CODES = new Set(['odontologo', 'especialista'])

export function PatientsListPage() {
  const navigate = useNavigate()
  const activeRole = useActiveRole()
  const [status, setStatus] = useState<StatusCode | ''>('')
  const [mineOnly, setMineOnly] = useState(false)
  const canFilterMine = activeRole !== null && PROVIDER_ROLE_CODES.has(activeRole)

  const patientsQuery = useQuery({
    queryKey: ['patients', status, canFilterMine && mineOnly],
    queryFn: () => api.listPatients(status || undefined, canFilterMine && mineOnly),
  })

  return (
    <section>
      <div className={styles.toolbar}>
        <h1>Pacientes</h1>
        <div className={styles.filters}>
          <select
            aria-label="Filtrar por estado"
            value={status}
            onChange={(e) => setStatus(e.target.value as StatusCode | '')}
          >
            <option value="">Todos los estados</option>
            {Object.entries(STATUS_LABELS).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
          {canFilterMine && (
            <label className={styles.mineOnlyToggle}>
              <input
                type="checkbox"
                checked={mineOnly}
                onChange={(e) => setMineOnly(e.target.checked)}
              />
              Mis pacientes
            </label>
          )}
          {canWritePatients(activeRole) && (
            <button
              className={styles.addButton}
              type="button"
              onClick={() => navigate('/pacientes/nuevo')}
            >
              Nuevo paciente
            </button>
          )}
        </div>
      </div>

      {patientsQuery.isLoading && <p>Cargando pacientes...</p>}
      {patientsQuery.isError && <p>No se pudieron cargar los pacientes.</p>}

      {patientsQuery.data && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Expediente</th>
              <th>Nombre</th>
              <th>Fecha de nacimiento</th>
              <th>Telefono</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {patientsQuery.data.map((patient) => (
              <tr
                key={patient.id}
                role="button"
                tabIndex={0}
                aria-label={`Abrir expediente de ${patient.full_name}, exp. ${patient.expediente_number}`}
                className={styles.row}
                onClick={() => navigate(`/pacientes/${patient.id}`)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    navigate(`/pacientes/${patient.id}`)
                  }
                }}
              >
                <td>{patient.expediente_number}</td>
                <td>{patient.full_name}</td>
                <td>{patient.date_of_birth}</td>
                <td>{patient.phone ?? '-'}</td>
                <td>{STATUS_LABELS[patient.status]}</td>
              </tr>
            ))}
            {patientsQuery.data.length === 0 && (
              <tr>
                <td colSpan={5}>No hay pacientes con ese filtro.</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </section>
  )
}
