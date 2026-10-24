import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { canAcceptBudget, canWriteTreatment } from '../auth/roles'
import { useActiveRole } from '../auth/store'
import { EncounterPickerField } from '../encounters/EncounterPicker'
import { useEncounterPicker } from '../encounters/useEncounterPicker'
import { FINDING_CATALOG, FINDING_CODES } from '../odontogram/findingCatalog'
import type { FindingCode, Surface } from '../odontogram/types'
import styles from '../patients/PatientDetailPage.module.css'
import * as api from './api'
import { PLAN_STATUS_LABELS, PRIORITY_LABELS } from './catalog'
import type { ItemOut, PhaseWithItemsOut, PlanStatus, Priority } from './types'

const SURFACES: Surface[] = ['O', 'M', 'D', 'V', 'L', 'P', 'I']

function toothLabel(item: ItemOut): string {
  if (!item.tooth_fdi) return 'General'
  return `Pieza ${item.tooth_fdi}${item.surface ? ` (${item.surface})` : ''}`
}

function ReasonForm({
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
      <button className={styles.linkButton} type="button" onClick={() => setOpen(true)}>
        {label}
      </button>
    )
  }
  return (
    <span>
      <input type="text" placeholder="Motivo" value={reason} onChange={(e) => setReason(e.target.value)} />
      <button
        className={styles.linkButton}
        type="button"
        disabled={!reason.trim() || pending}
        onClick={() => onConfirm(reason)}
      >
        Confirmar
      </button>
    </span>
  )
}

function AddItemForm({
  planId,
  phaseId,
  patientId,
  onAdded,
}: {
  planId: string
  phaseId: string
  patientId: string
  onAdded: () => void
}) {
  const queryClient = useQueryClient()
  // A3/A4: AddItemForm solo se muestra cuando el que llama ya confirmo canWrite
  // (ver mas abajo), asi que iniciar una atencion aqui mismo siempre es valido.
  const encounterPicker = useEncounterPicker(patientId, true)
  const catalogQuery = useQuery({
    queryKey: ['procedure-catalog'],
    queryFn: api.listProcedureCatalog,
  })

  const [procedureCode, setProcedureCode] = useState('')
  const [toothFdi, setToothFdi] = useState('')
  const [surface, setSurface] = useState<Surface | ''>('')
  const [findingCode, setFindingCode] = useState<FindingCode | ''>('')

  const mutation = useMutation({
    mutationFn: () =>
      api.addItem(planId, phaseId, {
        encounter_id: encounterPicker.encounterId,
        procedure_code: procedureCode,
        tooth_fdi: toothFdi ? Number(toothFdi) : null,
        surface: toothFdi && surface ? surface : null,
        finding_code: toothFdi && findingCode ? findingCode : null,
      }),
    onSuccess: () => {
      setProcedureCode('')
      setToothFdi('')
      setSurface('')
      setFindingCode('')
      queryClient.invalidateQueries({ queryKey: ['treatment-plan', planId] })
      onAdded()
    },
  })

  return (
    <form
      className={styles.form}
      onSubmit={(e) => {
        e.preventDefault()
        mutation.mutate()
      }}
    >
      <EncounterPickerField encounterPicker={encounterPicker} />
      <select
        aria-label="Procedimiento"
        value={procedureCode}
        onChange={(e) => setProcedureCode(e.target.value)}
      >
        <option value="">Selecciona un procedimiento...</option>
        {catalogQuery.data?.map((proc) => (
          <option key={proc.code} value={proc.code}>
            {proc.name} (${proc.default_price})
          </option>
        ))}
      </select>
      <input
        type="number"
        placeholder="Pieza FDI (opcional)"
        value={toothFdi}
        onChange={(e) => setToothFdi(e.target.value)}
      />
      {toothFdi && (
        <>
          <select
            aria-label="Superficie"
            value={surface}
            onChange={(e) => setSurface(e.target.value as Surface | '')}
          >
            <option value="">Toda la pieza</option>
            {SURFACES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            aria-label="Hallazgo del odontograma"
            value={findingCode}
            onChange={(e) => setFindingCode(e.target.value as FindingCode | '')}
          >
            <option value="">No reflejar en el odontograma</option>
            {FINDING_CODES.map((code) => (
              <option key={code} value={code}>
                {FINDING_CATALOG[code].label}
              </option>
            ))}
          </select>
        </>
      )}
      <button
        className={styles.primaryButton}
        type="submit"
        disabled={!encounterPicker.encounterId || !procedureCode || mutation.isPending}
        title={!encounterPicker.encounterId ? 'Selecciona o inicia una atencion' : undefined}
      >
        Agregar procedimiento
      </button>
    </form>
  )
}

function DiscountForm({
  planId,
  itemId,
  onApplied,
}: {
  planId: string
  itemId: string
  onApplied: () => void
}) {
  const [open, setOpen] = useState(false)
  const [amount, setAmount] = useState('')
  const [reason, setReason] = useState('')

  const mutation = useMutation({
    mutationFn: () => api.applyDiscount(planId, itemId, amount, reason),
    onSuccess: () => {
      setOpen(false)
      setAmount('')
      setReason('')
      onApplied()
    },
  })

  if (!open) {
    return (
      <button className={styles.linkButton} type="button" onClick={() => setOpen(true)}>
        Descuento
      </button>
    )
  }
  return (
    <span>
      <input
        type="number"
        step="0.01"
        placeholder="Monto"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
      />
      <input type="text" placeholder="Motivo" value={reason} onChange={(e) => setReason(e.target.value)} />
      <button
        className={styles.linkButton}
        type="button"
        disabled={!amount || !reason.trim() || mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        Aplicar
      </button>
    </span>
  )
}

function RegisterPerformedForm({
  patientId,
  item,
  onDone,
}: {
  patientId: string
  item: ItemOut
  onDone: () => void
}) {
  const [open, setOpen] = useState(false)
  const [material, setMaterial] = useState('')

  const mutation = useMutation({
    mutationFn: () =>
      api.registerPerformed({
        patient_id: patientId,
        encounter_id: item.encounter_id,
        planned_id: item.id,
        material: material || null,
      }),
    onSuccess: () => {
      setOpen(false)
      setMaterial('')
      onDone()
    },
  })

  if (!open) {
    return (
      <button className={styles.linkButton} type="button" onClick={() => setOpen(true)}>
        Marcar como realizado
      </button>
    )
  }
  return (
    <span>
      <input
        type="text"
        placeholder="Material (opcional)"
        value={material}
        onChange={(e) => setMaterial(e.target.value)}
      />
      <button
        className={styles.linkButton}
        type="button"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        Confirmar
      </button>
    </span>
  )
}

export function PlanDetail({
  planId,
  patientId,
  onBack,
}: {
  planId: string
  patientId: string
  onBack: () => void
}) {
  const activeRole = useActiveRole()
  const queryClient = useQueryClient()
  const canWrite = canWriteTreatment(activeRole)
  const canAccept = canAcceptBudget(activeRole)

  const planQuery = useQuery({
    queryKey: ['treatment-plan', planId],
    queryFn: () => api.getPlanDetail(planId),
  })
  const performedQuery = useQuery({
    queryKey: ['patient-performed', patientId],
    queryFn: () => api.listPerformed(patientId),
  })

  const [addingPhase, setAddingPhase] = useState(false)
  const [phaseName, setPhaseName] = useState('')
  const [phasePriority, setPhasePriority] = useState<Priority>('media')
  const [addingItemToPhase, setAddingItemToPhase] = useState<string | null>(null)
  const [accepting, setAccepting] = useState(false)
  const [acceptedIds, setAcceptedIds] = useState<Set<string>>(new Set())
  const [acceptedByName, setAcceptedByName] = useState('')

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['treatment-plan', planId] })
    queryClient.invalidateQueries({ queryKey: ['treatment-plans', patientId] })
    queryClient.invalidateQueries({ queryKey: ['patient-performed', patientId] })
    queryClient.invalidateQueries({ queryKey: ['odontogram', patientId] })
  }

  const statusMutation = useMutation({
    mutationFn: ({ status, reason }: { status: PlanStatus; reason?: string }) =>
      api.changePlanStatus(planId, status, reason),
    onSuccess: invalidate,
  })

  const addPhaseMutation = useMutation({
    mutationFn: () => api.addPhase(planId, { name: phaseName, priority: phasePriority }),
    onSuccess: () => {
      setAddingPhase(false)
      setPhaseName('')
      invalidate()
    },
  })

  const annulItemMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      api.annulItem(planId, itemId, reason),
    onSuccess: invalidate,
  })

  const acceptMutation = useMutation({
    mutationFn: () => api.acceptPlan(planId, Array.from(acceptedIds), acceptedByName),
    onSuccess: () => {
      setAccepting(false)
      invalidate()
    },
  })

  if (planQuery.isLoading || !planQuery.data) return <p>Cargando plan...</p>
  const plan = planQuery.data
  const performedPlannedIds = new Set(
    (performedQuery.data ?? []).map((p) => p.planned_id).filter((id): id is string => !!id),
  )
  const allActiveItemIds = plan.phases.flatMap((phase) => phase.items.map((item) => item.id))

  return (
    <div className={styles.card}>
      <button className={styles.linkButton} type="button" onClick={onBack}>
        Volver a los planes
      </button>
      <h2>{plan.title}</h2>
      <p>
        Estado: <strong>{PLAN_STATUS_LABELS[plan.status]}</strong> · Atiende:{' '}
        {plan.professional_name} · Total: ${plan.total}
        {plan.accepted_at && (
          <>
            {' '}
            · Aceptado ({plan.acceptance_type}) por {plan.accepted_by_name} el{' '}
            {new Date(plan.accepted_at).toLocaleDateString('es-MX')}
          </>
        )}
        {plan.rejected_reason && <> · Rechazado: {plan.rejected_reason}</>}
      </p>

      <div>
        <button
          className={styles.linkButton}
          type="button"
          onClick={async () => {
            // Abrir la pestaña ya dentro del .then()/await pierde el gesto del
            // usuario y el bloqueador de popups la descarta en algunos navegadores;
            // se abre en blanco de inmediato y se le asigna la URL del blob despues.
            const newTab = window.open('', '_blank')
            const url = await api.getPlanPdfBlobUrl(planId)
            if (newTab) newTab.location.href = url
          }}
        >
          Descargar PDF del presupuesto
        </button>
      </div>

      {canWrite && plan.status === 'BORRADOR' && (
        <button
          className={styles.primaryButton}
          type="button"
          onClick={() => statusMutation.mutate({ status: 'PRESENTADO' })}
        >
          Presentar al paciente
        </button>
      )}

      {canAccept && plan.status === 'PRESENTADO' && !accepting && (
        <div>
          <button className={styles.primaryButton} type="button" onClick={() => setAccepting(true)}>
            Aceptar presupuesto
          </button>
          <ReasonForm
            label="Rechazar"
            pending={statusMutation.isPending}
            onConfirm={(reason) => statusMutation.mutate({ status: 'RECHAZADO', reason })}
          />
        </div>
      )}

      {accepting && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            acceptMutation.mutate()
          }}
        >
          <p>Selecciona los procedimientos que el paciente acepta:</p>
          {plan.phases.flatMap((phase) => phase.items).map((item) => (
            <label key={item.id} className={styles.infoRow}>
              <input
                type="checkbox"
                checked={acceptedIds.has(item.id)}
                onChange={(e) => {
                  const next = new Set(acceptedIds)
                  if (e.target.checked) next.add(item.id)
                  else next.delete(item.id)
                  setAcceptedIds(next)
                }}
              />
              {item.procedure_name} — {toothLabel(item)} (${item.subtotal})
            </label>
          ))}
          <input
            type="text"
            placeholder="Nombre de quien acepta"
            required
            value={acceptedByName}
            onChange={(e) => setAcceptedByName(e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={acceptedIds.size === 0 || !acceptedByName.trim() || acceptMutation.isPending}
          >
            Confirmar aceptacion
          </button>
          <button className={styles.linkButton} type="button" onClick={() => setAccepting(false)}>
            Cancelar
          </button>
        </form>
      )}

      {canWrite && plan.status === 'ACEPTADO' && (
        <button
          className={styles.primaryButton}
          type="button"
          onClick={() => statusMutation.mutate({ status: 'EN_PROGRESO' })}
        >
          Iniciar progreso
        </button>
      )}
      {canWrite && plan.status === 'EN_PROGRESO' && (
        <button
          className={styles.primaryButton}
          type="button"
          onClick={() => statusMutation.mutate({ status: 'TERMINADO' })}
        >
          Marcar plan como terminado
        </button>
      )}

      {plan.phases.map((phase: PhaseWithItemsOut) => (
        <div key={phase.id} className={styles.card}>
          <h3>
            {phase.name} ({PRIORITY_LABELS[phase.priority]}) — ${phase.phase_total}
          </h3>
          {phase.items.map((item) => (
            <div key={item.id} className={styles.contactItem}>
              <span>
                {item.procedure_name} — {toothLabel(item)} · {item.quantity}x ${item.unit_price}
                {item.discount_amount && ` − $${item.discount_amount}`} = ${item.subtotal}
                {item.accepted && ' · aceptado'}
                {performedPlannedIds.has(item.id) && ' · realizado'}
              </span>
              {canWrite && plan.status === 'BORRADOR' && (
                <span>
                  <DiscountForm planId={planId} itemId={item.id} onApplied={invalidate} />
                  <ReasonForm
                    label="Anular"
                    pending={annulItemMutation.isPending}
                    onConfirm={(reason) => annulItemMutation.mutate({ itemId: item.id, reason })}
                  />
                </span>
              )}
              {canWrite &&
                item.accepted &&
                !performedPlannedIds.has(item.id) &&
                (plan.status === 'ACEPTADO' || plan.status === 'EN_PROGRESO') && (
                  <RegisterPerformedForm patientId={patientId} item={item} onDone={invalidate} />
                )}
            </div>
          ))}

          {canWrite && plan.status === 'BORRADOR' && (
            <>
              {addingItemToPhase === phase.id ? (
                <AddItemForm
                  planId={planId}
                  phaseId={phase.id}
                  patientId={patientId}
                  onAdded={() => setAddingItemToPhase(null)}
                />
              ) : (
                <button
                  className={styles.linkButton}
                  type="button"
                  onClick={() => setAddingItemToPhase(phase.id)}
                >
                  Agregar procedimiento
                </button>
              )}
            </>
          )}
        </div>
      ))}

      {canWrite && plan.status === 'BORRADOR' && (
        <>
          {!addingPhase ? (
            <button className={styles.primaryButton} type="button" onClick={() => setAddingPhase(true)}>
              Agregar fase
            </button>
          ) : (
            <form
              className={styles.form}
              onSubmit={(e) => {
                e.preventDefault()
                addPhaseMutation.mutate()
              }}
            >
              <input
                type="text"
                placeholder="Nombre de la fase"
                required
                value={phaseName}
                onChange={(e) => setPhaseName(e.target.value)}
              />
              <select
                aria-label="Prioridad de la fase"
                value={phasePriority}
                onChange={(e) => setPhasePriority(e.target.value as Priority)}
              >
                {Object.entries(PRIORITY_LABELS).map(([code, label]) => (
                  <option key={code} value={code}>
                    {label}
                  </option>
                ))}
              </select>
              <button
                className={styles.primaryButton}
                type="submit"
                disabled={!phaseName.trim() || addPhaseMutation.isPending}
              >
                Guardar fase
              </button>
            </form>
          )}
        </>
      )}
      {allActiveItemIds.length === 0 && plan.phases.length === 0 && (
        <p>Este plan todavia no tiene fases.</p>
      )}
    </div>
  )
}
