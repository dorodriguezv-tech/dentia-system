import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { canReadTreatment, canWriteTreatment } from '../auth/roles'
import { useActiveRole } from '../auth/store'
import * as encountersApi from '../encounters/api'
import * as api from './api'
import { PLAN_STATUS_LABELS } from './catalog'
import { PlanDetail } from './PlanDetail'
import styles from '../patients/PatientDetailPage.module.css'

export function TreatmentTab({ patientId }: { patientId: string }) {
  const activeRole = useActiveRole()
  const queryClient = useQueryClient()
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [encounterId, setEncounterId] = useState('')
  const [title, setTitle] = useState('')

  const plansQuery = useQuery({
    queryKey: ['treatment-plans', patientId],
    queryFn: () => api.listPlans(patientId),
  })
  const encountersQuery = useQuery({
    queryKey: ['patient-encounters', patientId],
    queryFn: () => encountersApi.listPatientEncounters(patientId),
    enabled: creating,
  })

  const createMutation = useMutation({
    mutationFn: () => api.createPlan({ patient_id: patientId, encounter_id: encounterId, title }),
    onSuccess: (plan) => {
      setCreating(false)
      setTitle('')
      setEncounterId('')
      queryClient.invalidateQueries({ queryKey: ['treatment-plans', patientId] })
      setSelectedPlanId(plan.id)
    },
  })

  if (!canReadTreatment(activeRole)) {
    return <p>No tienes permiso para ver los planes de tratamiento.</p>
  }
  const canWrite = canWriteTreatment(activeRole)

  if (selectedPlanId) {
    return (
      <PlanDetail
        planId={selectedPlanId}
        patientId={patientId}
        onBack={() => setSelectedPlanId(null)}
      />
    )
  }

  return (
    <div className={styles.card}>
      <h2>Planes de tratamiento</h2>
      {plansQuery.data?.length === 0 && <p>Sin planes de tratamiento registrados.</p>}
      {plansQuery.data?.map((plan) => (
        <div key={plan.id} className={styles.contactItem}>
          <span>
            {plan.title} — {PLAN_STATUS_LABELS[plan.status]} · ${plan.total}
          </span>
          <button className={styles.linkButton} type="button" onClick={() => setSelectedPlanId(plan.id)}>
            Ver
          </button>
        </div>
      ))}

      {canWrite && (
        <>
          {!creating ? (
            <button className={styles.primaryButton} type="button" onClick={() => setCreating(true)}>
              Nuevo plan
            </button>
          ) : (
            <form
              className={styles.form}
              onSubmit={(e) => {
                e.preventDefault()
                createMutation.mutate()
              }}
            >
              <select value={encounterId} onChange={(e) => setEncounterId(e.target.value)}>
                <option value="">Selecciona una atencion...</option>
                {encountersQuery.data?.map((encounter) => (
                  <option key={encounter.id} value={encounter.id}>
                    {new Date(encounter.started_at).toLocaleDateString('es-MX')} —{' '}
                    {encounter.chief_complaint ?? 'Sin motivo'}
                  </option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Titulo del plan"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
              <button
                className={styles.primaryButton}
                type="submit"
                disabled={!encounterId || !title.trim() || createMutation.isPending}
              >
                Crear plan
              </button>
            </form>
          )}
        </>
      )}
    </div>
  )
}
