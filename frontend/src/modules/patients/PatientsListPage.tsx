import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { canWritePatients } from '../auth/roles'
import { useActiveRole } from '../auth/store'
import * as api from './api'
import styles from './PatientsListPage.module.css'
import { STATUS_LABELS, type StatusCode } from './types'

export function PatientsListPage() {
  const navigate = useNavigate()
  const activeRole = useActiveRole()
  const [status, setStatus] = useState<StatusCode | ''>('')

  const patientsQuery = useQuery({
    queryKey: ['patients', status],
    queryFn: () => api.listPatients(status || undefined),
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
