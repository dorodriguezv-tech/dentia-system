import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { canReadTreatment, canWriteTreatment } from '../auth/roles'
import { useActiveRole } from '../auth/store'
import { EncounterPickerField } from '../encounters/EncounterPicker'
import { useEncounterPicker } from '../encounters/useEncounterPicker'
import * as api from './api'
import { PLAN_STATUS_LABELS } from './catalog'
import { PlanDetail } from './PlanDetail'
import styles from '../patients/PatientDetailPage.module.css'

export function TreatmentTab({ patientId }: { patientId: string }) {
  const activeRole = useActiveRole()
  const queryClient = useQueryClient()
  const canRead = canReadTreatment(activeRole)
  const canWrite = canWriteTreatment(activeRole)
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [title, setTitle] = useState('')

  const plansQuery = useQuery({
    queryKey: ['treatment-plans', patientId],
    queryFn: () => api.listPlans(patientId),
    enabled: canRead,
  })
  // A3/A4: mismo selector compartido que el expediente -- preselecciona la atencion
  // de hoy y ofrece "+ Iniciar atencion nueva" si el paciente no tiene ninguna, en vez
  // de dejar el formulario de "Crear plan" deshabilitado para siempre.
  const encounterPicker = useEncounterPicker(patientId, canWrite, creating)

  const createMutation = useMutation({
    mutationFn: () =>
      api.createPlan({ patient_id: patientId, encounter_id: encounterPicker.encounterId, title }),
    onSuccess: (plan) => {
      setCreating(false)
      setTitle('')
      queryClient.invalidateQueries({ queryKey: ['treatment-plans', patientId] })
      setSelectedPlanId(plan.id)
    },
  })

  if (!canRead) {
    return <p>No tienes permiso para ver los planes de tratamiento.</p>
  }

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
            {plan.title} — {PLAN_STATUS_LABELS[plan.status]} · {plan.professional_name} · $
            {plan.total}
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
              <EncounterPickerField encounterPicker={encounterPicker} />
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
                disabled={!encounterPicker.encounterId || !title.trim() || createMutation.isPending}
                title={!encounterPicker.encounterId ? 'Selecciona o inicia una atencion' : undefined}
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
