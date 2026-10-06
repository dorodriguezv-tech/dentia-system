import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as encountersApi from '../encounters/api'
import { canReadRecords, canWriteDiagnosis, canWriteRecords } from '../auth/roles'
import { useActiveRole } from '../auth/store'
import { DIAGNOSIS_CATALOG } from '../diagnosis/catalog'
import * as diagnosisApi from '../diagnosis/api'
import type { DiagnosisCode, DiagnosisOut } from '../diagnosis/types'
import * as recordsApi from '../records/api'
import {
  HISTORY_CATEGORY_LABELS,
  SEVERITY_LABELS,
  type AllergyOut,
  type HistoryCategory,
  type MedicalHistoryOut,
  type MedicationOut,
  type Severity,
  type VitalSignsOut,
} from '../records/types'
import styles from './PatientDetailPage.module.css'

function EncounterSelect({
  encounters,
  value,
  onChange,
}: {
  encounters: { id: string; started_at: string; chief_complaint: string | null }[]
  value: string
  onChange: (encounterId: string) => void
}) {
  return (
    <select aria-label="Atencion" value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">Selecciona una atencion...</option>
      {encounters.map((encounter) => (
        <option key={encounter.id} value={encounter.id}>
          {new Date(encounter.started_at).toLocaleDateString('es-MX')} —{' '}
          {encounter.chief_complaint ?? 'Sin motivo'}
        </option>
      ))}
    </select>
  )
}

function AnnulButton({ onAnnul }: { onAnnul: (reason: string) => void }) {
  const [reason, setReason] = useState('')
  const [open, setOpen] = useState(false)

  if (!open) {
    return (
      <button className={styles.linkButton} type="button" onClick={() => setOpen(true)}>
        Anular
      </button>
    )
  }

  return (
    <span>
      <input
        type="text"
        placeholder="Motivo de anulacion"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <button
        className={styles.linkButton}
        type="button"
        disabled={!reason.trim()}
        onClick={() => onAnnul(reason)}
      >
        Confirmar
      </button>
    </span>
  )
}

function HistorySection({ patientId, canWrite }: { patientId: string; canWrite: boolean }) {
  const queryClient = useQueryClient()
  const encountersQuery = useQuery({
    queryKey: ['patient-encounters', patientId],
    queryFn: () => encountersApi.listPatientEncounters(patientId),
  })
  const historyQuery = useQuery({
    queryKey: ['patient-history', patientId],
    queryFn: () => recordsApi.listHistory(patientId),
  })

  const [encounterId, setEncounterId] = useState('')
  const [category, setCategory] = useState<HistoryCategory>('heredofamiliar')
  const [text, setText] = useState('')

  const createMutation = useMutation({
    mutationFn: () =>
      recordsApi.createHistory(patientId, { encounter_id: encounterId, category, text }),
    onSuccess: () => {
      setText('')
      queryClient.invalidateQueries({ queryKey: ['patient-history', patientId] })
      queryClient.invalidateQueries({ queryKey: ['patient-summary', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      recordsApi.annulHistory(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patient-history', patientId] })
      queryClient.invalidateQueries({ queryKey: ['patient-summary', patientId] })
    },
  })

  return (
    <details className={styles.card} open>
      <summary>Antecedentes</summary>
      {historyQuery.data
        ?.filter((item: MedicalHistoryOut) => item.is_active)
        .map((item) => (
          <div key={item.id} className={styles.contactItem}>
            <span>
              {HISTORY_CATEGORY_LABELS[item.category]}: {item.text}
            </span>
            {canWrite && (
              <AnnulButton
                onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })}
              />
            )}
          </div>
        ))}
      {historyQuery.data?.filter((item) => item.is_active).length === 0 && (
        <p>Sin antecedentes registrados.</p>
      )}

      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <EncounterSelect
            encounters={encountersQuery.data ?? []}
            value={encounterId}
            onChange={setEncounterId}
          />
          <select
            aria-label="Categoria del antecedente"
            value={category}
            onChange={(e) => setCategory(e.target.value as HistoryCategory)}
          >
            {Object.entries(HISTORY_CATEGORY_LABELS).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Descripcion"
            required
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || !text.trim() || createMutation.isPending}
          >
            Agregar antecedente
          </button>
        </form>
      )}
    </details>
  )
}

function AllergiesSection({ patientId, canWrite }: { patientId: string; canWrite: boolean }) {
  const queryClient = useQueryClient()
  const encountersQuery = useQuery({
    queryKey: ['patient-encounters', patientId],
    queryFn: () => encountersApi.listPatientEncounters(patientId),
  })
  const allergiesQuery = useQuery({
    queryKey: ['patient-allergies', patientId],
    queryFn: () => recordsApi.listAllergies(patientId),
  })

  const [encounterId, setEncounterId] = useState('')
  const [substance, setSubstance] = useState('')
  const [reaction, setReaction] = useState('')
  const [severity, setSeverity] = useState<Severity>('leve')

  const createMutation = useMutation({
    mutationFn: () =>
      recordsApi.createAllergy(patientId, {
        encounter_id: encounterId,
        substance,
        reaction: reaction || null,
        severity,
      }),
    onSuccess: () => {
      setSubstance('')
      setReaction('')
      queryClient.invalidateQueries({ queryKey: ['patient-allergies', patientId] })
      queryClient.invalidateQueries({ queryKey: ['patient-summary', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      recordsApi.annulAllergy(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patient-allergies', patientId] })
      queryClient.invalidateQueries({ queryKey: ['patient-summary', patientId] })
    },
  })

  return (
    <details className={styles.card} open>
      <summary>Alergias</summary>
      {allergiesQuery.data
        ?.filter((item: AllergyOut) => item.is_active)
        .map((item) => (
          <div key={item.id} className={styles.contactItem}>
            <span>
              {item.substance} ({SEVERITY_LABELS[item.severity]})
              {item.reaction && ` — ${item.reaction}`}
            </span>
            {canWrite && (
              <AnnulButton
                onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })}
              />
            )}
          </div>
        ))}
      {allergiesQuery.data?.filter((item) => item.is_active).length === 0 && (
        <p>Sin alergias registradas.</p>
      )}

      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <EncounterSelect
            encounters={encountersQuery.data ?? []}
            value={encounterId}
            onChange={setEncounterId}
          />
          <input
            type="text"
            placeholder="Sustancia"
            required
            value={substance}
            onChange={(e) => setSubstance(e.target.value)}
          />
          <input
            type="text"
            placeholder="Reaccion (opcional)"
            value={reaction}
            onChange={(e) => setReaction(e.target.value)}
          />
          <select
            aria-label="Severidad de la alergia"
            value={severity}
            onChange={(e) => setSeverity(e.target.value as Severity)}
          >
            {Object.entries(SEVERITY_LABELS).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || !substance.trim() || createMutation.isPending}
          >
            Agregar alergia
          </button>
        </form>
      )}
    </details>
  )
}

function MedicationsSection({ patientId, canWrite }: { patientId: string; canWrite: boolean }) {
  const queryClient = useQueryClient()
  const encountersQuery = useQuery({
    queryKey: ['patient-encounters', patientId],
    queryFn: () => encountersApi.listPatientEncounters(patientId),
  })
  const medicationsQuery = useQuery({
    queryKey: ['patient-medications', patientId],
    queryFn: () => recordsApi.listMedications(patientId),
  })

  const [encounterId, setEncounterId] = useState('')
  const [name, setName] = useState('')
  const [dose, setDose] = useState('')
  const [frequency, setFrequency] = useState('')

  const createMutation = useMutation({
    mutationFn: () =>
      recordsApi.createMedication(patientId, {
        encounter_id: encounterId,
        name,
        dose: dose || null,
        frequency: frequency || null,
      }),
    onSuccess: () => {
      setName('')
      setDose('')
      setFrequency('')
      queryClient.invalidateQueries({ queryKey: ['patient-medications', patientId] })
      queryClient.invalidateQueries({ queryKey: ['patient-summary', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      recordsApi.annulMedication(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patient-medications', patientId] })
      queryClient.invalidateQueries({ queryKey: ['patient-summary', patientId] })
    },
  })

  return (
    <details className={styles.card} open>
      <summary>Medicamentos</summary>
      {medicationsQuery.data
        ?.filter((item: MedicationOut) => item.is_active)
        .map((item) => (
          <div key={item.id} className={styles.contactItem}>
            <span>
              {item.name}
              {item.dose && ` — ${item.dose}`}
              {item.frequency && ` · ${item.frequency}`}
            </span>
            {canWrite && (
              <AnnulButton
                onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })}
              />
            )}
          </div>
        ))}
      {medicationsQuery.data?.filter((item) => item.is_active).length === 0 && (
        <p>Sin medicamentos registrados.</p>
      )}

      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <EncounterSelect
            encounters={encountersQuery.data ?? []}
            value={encounterId}
            onChange={setEncounterId}
          />
          <input
            type="text"
            placeholder="Nombre"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            type="text"
            placeholder="Dosis (opcional)"
            value={dose}
            onChange={(e) => setDose(e.target.value)}
          />
          <input
            type="text"
            placeholder="Frecuencia (opcional)"
            value={frequency}
            onChange={(e) => setFrequency(e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || !name.trim() || createMutation.isPending}
          >
            Agregar medicamento
          </button>
        </form>
      )}
    </details>
  )
}

function VitalSignsSection({ patientId, canWrite }: { patientId: string; canWrite: boolean }) {
  const queryClient = useQueryClient()
  const encountersQuery = useQuery({
    queryKey: ['patient-encounters', patientId],
    queryFn: () => encountersApi.listPatientEncounters(patientId),
  })
  const vitalSignsQuery = useQuery({
    queryKey: ['patient-vital-signs', patientId],
    queryFn: () => recordsApi.listVitalSigns(patientId),
  })

  const [encounterId, setEncounterId] = useState('')
  const [bpSystolic, setBpSystolic] = useState('')
  const [bpDiastolic, setBpDiastolic] = useState('')
  const [heartRate, setHeartRate] = useState('')
  const [temperature, setTemperature] = useState('')

  const createMutation = useMutation({
    mutationFn: () =>
      recordsApi.createVitalSigns(patientId, {
        encounter_id: encounterId,
        bp_systolic: bpSystolic ? Number(bpSystolic) : null,
        bp_diastolic: bpDiastolic ? Number(bpDiastolic) : null,
        heart_rate: heartRate ? Number(heartRate) : null,
        temperature: temperature ? Number(temperature) : null,
      }),
    onSuccess: () => {
      setBpSystolic('')
      setBpDiastolic('')
      setHeartRate('')
      setTemperature('')
      queryClient.invalidateQueries({ queryKey: ['patient-vital-signs', patientId] })
    },
  })

  return (
    <details className={styles.card} open>
      <summary>Signos vitales</summary>
      {vitalSignsQuery.data?.map((item: VitalSignsOut) => (
        <div key={item.id} className={styles.contactItem}>
          <span>
            {new Date(item.recorded_at).toLocaleString('es-MX')} —{' '}
            {item.bp_systolic && item.bp_diastolic
              ? `${item.bp_systolic}/${item.bp_diastolic} mmHg`
              : ''}
            {item.heart_rate && ` · ${item.heart_rate} lpm`}
            {item.temperature && ` · ${item.temperature} °C`}
          </span>
        </div>
      ))}
      {vitalSignsQuery.data?.length === 0 && <p>Sin signos vitales registrados.</p>}

      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <EncounterSelect
            encounters={encountersQuery.data ?? []}
            value={encounterId}
            onChange={setEncounterId}
          />
          <input
            type="number"
            placeholder="Presion sistolica"
            value={bpSystolic}
            onChange={(e) => setBpSystolic(e.target.value)}
          />
          <input
            type="number"
            placeholder="Presion diastolica"
            value={bpDiastolic}
            onChange={(e) => setBpDiastolic(e.target.value)}
          />
          <input
            type="number"
            placeholder="Frecuencia cardiaca"
            value={heartRate}
            onChange={(e) => setHeartRate(e.target.value)}
          />
          <input
            type="number"
            step="0.1"
            placeholder="Temperatura"
            value={temperature}
            onChange={(e) => setTemperature(e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
          >
            Agregar signos vitales
          </button>
        </form>
      )}
    </details>
  )
}

function DiagnosisSection({ patientId, canWrite }: { patientId: string; canWrite: boolean }) {
  const queryClient = useQueryClient()
  const encountersQuery = useQuery({
    queryKey: ['patient-encounters', patientId],
    queryFn: () => encountersApi.listPatientEncounters(patientId),
  })
  const diagnosesQuery = useQuery({
    queryKey: ['patient-diagnoses', patientId],
    queryFn: () => diagnosisApi.listDiagnoses(patientId),
  })

  const [encounterId, setEncounterId] = useState('')
  const [code, setCode] = useState<DiagnosisCode | ''>('')
  const [text, setText] = useState('')

  const createMutation = useMutation({
    mutationFn: () =>
      diagnosisApi.createDiagnosis(patientId, {
        encounter_id: encounterId,
        code: code || null,
        text,
      }),
    onSuccess: () => {
      setText('')
      setCode('')
      queryClient.invalidateQueries({ queryKey: ['patient-diagnoses', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      diagnosisApi.annulDiagnosis(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patient-diagnoses', patientId] })
    },
  })

  return (
    <details className={styles.card} open>
      <summary>Diagnosticos</summary>
      {diagnosesQuery.data
        ?.filter((item: DiagnosisOut) => item.is_active)
        .map((item) => (
          <div key={item.id} className={styles.contactItem}>
            <span>
              {item.code && `${DIAGNOSIS_CATALOG[item.code]}: `}
              {item.text}
              {item.tooth_fdi &&
                ` (pieza ${item.tooth_fdi}${item.surface ? ` ${item.surface}` : ''})`}
            </span>
            {canWrite && (
              <AnnulButton
                onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })}
              />
            )}
          </div>
        ))}
      {diagnosesQuery.data?.filter((item) => item.is_active).length === 0 && (
        <p>Sin diagnosticos registrados.</p>
      )}

      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <EncounterSelect
            encounters={encountersQuery.data ?? []}
            value={encounterId}
            onChange={setEncounterId}
          />
          <select
            aria-label="Codigo del catalogo de diagnosticos"
            value={code}
            onChange={(e) => setCode(e.target.value as DiagnosisCode | '')}
          >
            <option value="">Sin codigo del catalogo...</option>
            {Object.entries(DIAGNOSIS_CATALOG).map(([c, label]) => (
              <option key={c} value={c}>
                {label}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Descripcion del diagnostico"
            required
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || !text.trim() || createMutation.isPending}
          >
            Agregar diagnostico
          </button>
        </form>
      )}
    </details>
  )
}

export function ExpedienteTab({ patientId }: { patientId: string }) {
  const activeRole = useActiveRole()

  if (!canReadRecords(activeRole)) {
    return <p>No tienes permiso para ver el expediente clinico.</p>
  }

  const canWrite = canWriteRecords(activeRole)

  return (
    <div className={styles.grid}>
      <HistorySection patientId={patientId} canWrite={canWrite} />
      <AllergiesSection patientId={patientId} canWrite={canWrite} />
      <MedicationsSection patientId={patientId} canWrite={canWrite} />
      <VitalSignsSection patientId={patientId} canWrite={canWrite} />
      <DiagnosisSection patientId={patientId} canWrite={canWriteDiagnosis(activeRole)} />
    </div>
  )
}
