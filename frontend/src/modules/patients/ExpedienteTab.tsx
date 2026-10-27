import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { EncounterPickerField } from '../encounters/EncounterPicker'
import { useEncounterPicker, type EncounterPicker } from '../encounters/useEncounterPicker'
import { canReadRecords, canWriteDiagnosis, canWriteRecords } from '../auth/roles'
import { useActiveRole } from '../auth/store'
import * as catalogsApi from '../catalogs/api'
import type { CatalogItemOut } from '../catalogs/types'
import { DIAGNOSIS_CATALOG } from '../diagnosis/catalog'
import * as diagnosisApi from '../diagnosis/api'
import type { DiagnosisCode, DiagnosisOut } from '../diagnosis/types'
import * as recordsApi from '../records/api'
import {
  ADICCIONES_KEYS,
  ADICCIONES_LABELS,
  BLEEDING_GUMS_LABELS,
  FAMILY_STATUS_LABELS,
  FOOD_QUALITY_LABELS,
  GLUCOSE_TIMING_LABELS,
  HEALTH_COVERAGE_LABELS,
  MARITAL_STATUSES,
  MARITAL_STATUS_LABELS,
  PATIENT_ATTITUDE_LABELS,
  REPRODUCTOR_FEMENINO_FIELDS,
  REPRODUCTOR_MASCULINO_FIELDS,
  SERVICIOS_BASICOS_KEYS,
  SERVICIOS_BASICOS_LABELS,
  SEVERITY_LABELS,
  SYSTEMS_REVIEW_SYSTEMS,
  SYSTEMS_REVIEW_SYSTEM_LABELS,
  type AddictionEntry,
  type AllergyOut,
  type BleedingGumsLevel,
  type DiseaseEntry,
  type FamilyHistoryEntryOut,
  type FamilyStatus,
  type FoodQualityLevel,
  type GlucoseTiming,
  type HealthCoverageType,
  type MaritalStatus,
  type MedicationOut,
  type PatientAttitude,
  type PersonalNonPathologicalHistoryOut,
  type PersonalPathologicalHistoryOut,
  type ServiceEntry,
  type Severity,
  type SystemsReviewEntryOut,
  type VitalSignsOut,
} from '../records/types'
import * as patientsApi from './api'
import { EndodonticHistoryTab } from './EndodonticHistoryTab'
import { latestActive, saveWithAutoCorrection } from './historyHelpers'
import { AnnulButton, DetailList, EditingBanner, MissingDataBadge } from './historyShared'
import { OdontologicalHistoryTab } from './OdontologicalHistoryTab'
import styles from './PatientDetailPage.module.css'
import { PediatricHistoryTab } from './PediatricHistoryTab'
import type { PatientOut } from './types'

function calculateAge(dateOfBirth: string): number {
  const dob = new Date(dateOfBirth)
  const today = new Date()
  let age = today.getFullYear() - dob.getFullYear()
  const monthDiff = today.getMonth() - dob.getMonth()
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
    age -= 1
  }
  return age
}

const SEX_LABELS: Record<string, string> = { F: 'Femenino', M: 'Masculino', X: 'Otro' }

function AllergiesSection({
  patientId,
  canWrite,
  encounterPicker,
}: {
  patientId: string
  canWrite: boolean
  encounterPicker: EncounterPicker
}) {
  const queryClient = useQueryClient()
  const allergiesQuery = useQuery({
    queryKey: ['patient-allergies', patientId],
    queryFn: () => recordsApi.listAllergies(patientId),
  })

  const { encounterId } = encounterPicker
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

  const activeAllergies = allergiesQuery.data?.filter((item: AllergyOut) => item.is_active) ?? []

  return (
    <details className={styles.card}>
      <summary>
        Alergias
        <MissingDataBadge hasActiveEntries={activeAllergies.length > 0} />
      </summary>
      {activeAllergies.map((item) => (
        <div key={item.id} className={styles.contactItem}>
          <span>
            {new Date(item.created_at).toLocaleString('es-MX')} — {item.substance} (
            {SEVERITY_LABELS[item.severity]})
            {item.reaction && ` — ${item.reaction}`}
          </span>
          {canWrite && (
            <AnnulButton onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })} />
          )}
        </div>
      ))}
      {activeAllergies.length === 0 && <p>Sin alergias registradas.</p>}

      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
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
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            Agregar alergia
          </button>
        </form>
      )}
    </details>
  )
}

function MedicationsSection({
  patientId,
  canWrite,
  encounterPicker,
}: {
  patientId: string
  canWrite: boolean
  encounterPicker: EncounterPicker
}) {
  const queryClient = useQueryClient()
  const medicationsQuery = useQuery({
    queryKey: ['patient-medications', patientId],
    queryFn: () => recordsApi.listMedications(patientId),
  })

  const { encounterId } = encounterPicker
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

  const activeMedications =
    medicationsQuery.data?.filter((item: MedicationOut) => item.is_active) ?? []

  return (
    <details className={styles.card}>
      <summary>
        Medicamentos
        <MissingDataBadge hasActiveEntries={activeMedications.length > 0} />
      </summary>
      {activeMedications.map((item) => (
        <div key={item.id} className={styles.contactItem}>
          <span>
            {new Date(item.created_at).toLocaleString('es-MX')} — {item.name}
            {item.dose && ` — ${item.dose}`}
            {item.frequency && ` · ${item.frequency}`}
          </span>
          {canWrite && (
            <AnnulButton onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })} />
          )}
        </div>
      ))}
      {activeMedications.length === 0 && <p>Sin medicamentos registrados.</p>}

      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
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
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            Agregar medicamento
          </button>
        </form>
      )}
    </details>
  )
}

function VitalSignsSection({
  patientId,
  canWrite,
  encounterPicker,
}: {
  patientId: string
  canWrite: boolean
  encounterPicker: EncounterPicker
}) {
  const queryClient = useQueryClient()
  const vitalSignsQuery = useQuery({
    queryKey: ['patient-vital-signs', patientId],
    queryFn: () => recordsApi.listVitalSigns(patientId),
  })
  // Punto 9: indice de glucosa obligatorio si el paciente tiene diabetes marcada
  // como antecedente patologico personal ACTIVO. Misma query-key que
  // PathologicalHistorySection (['general-history-pathological', patientId]) para
  // compartir la cache de TanStack Query en vez de duplicar la peticion.
  const pathologicalHistoryQuery = useQuery({
    queryKey: ['general-history-pathological', patientId],
    queryFn: () => recordsApi.listPathologicalHistory(patientId),
  })
  const hasDiabetes =
    pathologicalHistoryQuery.data?.some(
      (item) => item.is_active && item.diseases?.diabetes?.present,
    ) ?? false

  const { encounterId } = encounterPicker
  const [bpSystolic, setBpSystolic] = useState('')
  const [bpDiastolic, setBpDiastolic] = useState('')
  const [heartRate, setHeartRate] = useState('')
  const [temperature, setTemperature] = useState('')
  // Fase A (rediseno del expediente, docs/clinica): campos nuevos del formato
  // de signos vitales y exploracion fisica de la Historia Clinica General.
  const [heightM, setHeightM] = useState('')
  const [weightKg, setWeightKg] = useState('')
  const [spo2, setSpo2] = useState('')
  const [glucoseIndex, setGlucoseIndex] = useState('')
  const [glucoseTiming, setGlucoseTiming] = useState<GlucoseTiming | ''>('')
  const [patientAttitude, setPatientAttitude] = useState<PatientAttitude | ''>('')
  const [asaClassification, setAsaClassification] = useState('')

  const previewBmi =
    heightM && weightKg && Number(heightM) > 0
      ? Math.round((Number(weightKg) / Number(heightM) ** 2) * 10) / 10
      : null

  const createMutation = useMutation({
    mutationFn: () =>
      recordsApi.createVitalSigns(patientId, {
        encounter_id: encounterId,
        bp_systolic: bpSystolic ? Number(bpSystolic) : null,
        bp_diastolic: bpDiastolic ? Number(bpDiastolic) : null,
        heart_rate: heartRate ? Number(heartRate) : null,
        temperature: temperature ? Number(temperature) : null,
        height_m: heightM ? Number(heightM) : null,
        weight_kg: weightKg ? Number(weightKg) : null,
        spo2: spo2 ? Number(spo2) : null,
        glucose_index: glucoseIndex ? Number(glucoseIndex) : null,
        glucose_timing: glucoseTiming || null,
        patient_attitude: patientAttitude || null,
        asa_classification: asaClassification || null,
      }),
    onSuccess: () => {
      setBpSystolic('')
      setBpDiastolic('')
      setHeartRate('')
      setTemperature('')
      setHeightM('')
      setWeightKg('')
      setSpo2('')
      setGlucoseIndex('')
      setGlucoseTiming('')
      setPatientAttitude('')
      setAsaClassification('')
      queryClient.invalidateQueries({ queryKey: ['patient-vital-signs', patientId] })
    },
  })

  return (
    <details className={styles.card}>
      <summary>Signos vitales y exploración física</summary>
      {vitalSignsQuery.data?.map((item: VitalSignsOut) => (
        <div key={item.id} className={styles.contactItem}>
          <span>
            {new Date(item.recorded_at).toLocaleString('es-MX')} —{' '}
            {item.bp_systolic && item.bp_diastolic
              ? `${item.bp_systolic}/${item.bp_diastolic} mmHg`
              : ''}
            {item.heart_rate && ` · ${item.heart_rate} lpm`}
            {item.temperature && ` · ${item.temperature} °C`}
            {item.height_m && ` · Talla ${item.height_m} m`}
            {item.weight_kg && ` · Peso ${item.weight_kg} kg`}
            {item.body_mass_index && ` · IMC ${item.body_mass_index}`}
            {item.spo2 != null && ` · SpO2 ${item.spo2}%`}
            {item.glucose_index != null &&
              ` · Glucosa ${item.glucose_index}${
                item.glucose_timing ? ` (${GLUCOSE_TIMING_LABELS[item.glucose_timing]})` : ''
              }`}
            {item.patient_attitude && ` · ${PATIENT_ATTITUDE_LABELS[item.patient_attitude]}`}
            {item.asa_classification && ` · ASA ${item.asa_classification}`}
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
          <EncounterPickerField encounterPicker={encounterPicker} />
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
          <input
            type="number"
            step="0.01"
            placeholder="Talla (m)"
            value={heightM}
            onChange={(e) => setHeightM(e.target.value)}
          />
          <input
            type="number"
            step="0.1"
            placeholder="Peso (kg)"
            value={weightKg}
            onChange={(e) => setWeightKg(e.target.value)}
          />
          {previewBmi !== null && <p>IMC calculado: {previewBmi}</p>}
          <input
            type="number"
            placeholder="SpO2 (%)"
            value={spo2}
            onChange={(e) => setSpo2(e.target.value)}
          />
          <input
            type="number"
            step="0.1"
            placeholder="Indice de glucosa"
            required={hasDiabetes}
            value={glucoseIndex}
            onChange={(e) => setGlucoseIndex(e.target.value)}
          />
          {hasDiabetes && (
            <p className={styles.complianceNote}>
              Paciente con diabetes: registra el índice de glucosa.
            </p>
          )}
          <select
            aria-label="Momento de la glucosa"
            value={glucoseTiming}
            onChange={(e) => setGlucoseTiming(e.target.value as GlucoseTiming | '')}
          >
            <option value="">Glucosa: sin especificar</option>
            {Object.entries(GLUCOSE_TIMING_LABELS).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
          <select
            aria-label="Actitud del paciente"
            value={patientAttitude}
            onChange={(e) => setPatientAttitude(e.target.value as PatientAttitude | '')}
          >
            <option value="">Actitud: sin especificar</option>
            {Object.entries(PATIENT_ATTITUDE_LABELS).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Clasificacion ASA (p.ej. ASA I)"
            value={asaClassification}
            onChange={(e) => setAsaClassification(e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            Agregar signos vitales
          </button>
        </form>
      )}
    </details>
  )
}

/** Datos generales (autollenado desde Patient, solo lectura) de la Historia
 * Clinica General -- regla de Fase A: lo que ya existe en Patient nunca se
 * vuelve a teclear. */
function DatosGeneralesSection({ patient }: { patient: PatientOut }) {
  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>Datos generales</summary>
      <dl>
        <div className={styles.infoRow}>
          <dt>Nombre completo</dt>
          <dd>{patient.full_name}</dd>
        </div>
        <div className={styles.infoRow}>
          <dt>Domicilio</dt>
          <dd>{patient.address ?? '-'}</dd>
        </div>
        <div className={styles.infoRow}>
          <dt>Edad</dt>
          <dd>{calculateAge(patient.date_of_birth)} años</dd>
        </div>
        <div className={styles.infoRow}>
          <dt>Fecha de nacimiento</dt>
          <dd>{patient.date_of_birth}</dd>
        </div>
        <div className={styles.infoRow}>
          <dt>Lugar de nacimiento</dt>
          <dd>{patient.birth_place ?? '-'}</dd>
        </div>
        <div className={styles.infoRow}>
          <dt>Tipo sanguíneo</dt>
          <dd>{patient.blood_type ?? '-'}</dd>
        </div>
        <div className={styles.infoRow}>
          <dt>Sexo</dt>
          <dd>{patient.sex ? SEX_LABELS[patient.sex] : '-'}</dd>
        </div>
        <div className={styles.infoRow}>
          <dt>Escolaridad</dt>
          <dd>{patient.education_level ?? '-'}</dd>
        </div>
        <div className={styles.infoRow}>
          <dt>Sabe leer y escribir</dt>
          <dd>
            {patient.can_read_write === null || patient.can_read_write === undefined
              ? '-'
              : patient.can_read_write
                ? 'Sí'
                : 'No'}
          </dd>
        </div>
        <div className={styles.infoRow}>
          <dt>Religión</dt>
          <dd>{patient.religion ?? '-'}</dd>
        </div>
        <div className={styles.infoRow}>
          <dt>Grupo étnico</dt>
          <dd>{patient.ethnic_group ?? '-'}</dd>
        </div>
        <div className={styles.infoRow}>
          <dt>Raza</dt>
          <dd>{patient.race ?? '-'}</dd>
        </div>
        <div className={styles.infoRow}>
          <dt>Teléfono</dt>
          <dd>{patient.phone ?? '-'}</dd>
        </div>
        <div className={styles.infoRow}>
          <dt>Correo</dt>
          <dd>{patient.email ?? '-'}</dd>
        </div>
        <div className={styles.infoRow}>
          <dt>Ocupación</dt>
          <dd>{patient.occupation ?? '-'}</dd>
        </div>
        <div className={styles.infoRow}>
          <dt>Estado civil</dt>
          <dd>{patient.marital_status ?? '-'}</dd>
        </div>
      </dl>
      <p className={styles.complianceNote}>
        El motivo de consulta y las alergias se capturan en las secciones
        correspondientes de este mismo expediente (atención activa y Alergias).
      </p>
    </details>
  )
}

function FamilyHistorySection({
  patientId,
  canWrite,
  encounterPicker,
  relationshipCatalog,
  conditionCatalog,
}: {
  patientId: string
  canWrite: boolean
  encounterPicker: EncounterPicker
  relationshipCatalog: CatalogItemOut[]
  conditionCatalog: CatalogItemOut[]
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['general-history-family', patientId],
    queryFn: () => recordsApi.listFamilyHistory(patientId),
  })

  const { encounterId } = encounterPicker
  const [relationshipCode, setRelationshipCode] = useState('')
  const [status, setStatus] = useState<FamilyStatus>('en_vida')
  const [conditions, setConditions] = useState<Record<string, boolean>>({})
  // Correccion UX (ronda 2.2): FamilyHistorySection es una LISTA de entradas
  // independientes (varios familiares), no un singleton -- el patron "editar"
  // aqui es por fila: "Modificar" precarga el formulario con ESA fila y, al
  // guardar, anula automaticamente esa fila y crea la nueva con los datos
  // corregidos (igual regla de auditoria que el patron de singleton).
  const [editingId, setEditingId] = useState<string | null>(null)

  function startEdit(item: FamilyHistoryEntryOut) {
    setEditingId(item.id)
    setRelationshipCode(item.relationship_code)
    setStatus(item.status)
    setConditions(
      Object.fromEntries(Object.entries(item.conditions).filter(([, present]) => present)),
    )
  }

  function cancelEdit() {
    setEditingId(null)
    setRelationshipCode('')
    setStatus('en_vida')
    setConditions({})
  }

  const editingEntry = editingId
    ? (listQuery.data ?? []).find((item) => item.id === editingId && item.is_active)
    : undefined

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        editingEntry,
        (itemId, reason) => recordsApi.annulFamilyHistory(patientId, itemId, reason),
        () =>
          recordsApi.createFamilyHistory(patientId, {
            encounter_id: encounterId,
            relationship_code: relationshipCode,
            status,
            conditions,
          }),
      ),
    onSuccess: () => {
      setEditingId(null)
      setRelationshipCode('')
      setStatus('en_vida')
      setConditions({})
      queryClient.invalidateQueries({ queryKey: ['general-history-family', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      recordsApi.annulFamilyHistory(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-history-family', patientId] })
    },
  })

  function relationshipLabel(code: string): string {
    return relationshipCatalog.find((c) => c.code === code)?.name ?? code
  }

  function activeConditionLabels(item: FamilyHistoryEntryOut): string {
    const names = Object.entries(item.conditions)
      .filter(([, present]) => present)
      .map(([code]) => conditionCatalog.find((c) => c.code === code)?.name ?? code)
    return names.length > 0 ? names.join(', ') : 'Sin condiciones marcadas'
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Antecedentes heredofamiliares
        <MissingDataBadge hasActiveEntries={activeEntries.length > 0} />
      </summary>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Parentesco</th>
              <th>Estado</th>
              <th>Condiciones</th>
              {canWrite && <th></th>}
            </tr>
          </thead>
          <tbody>
            {activeEntries.map((item) => (
              <tr key={item.id}>
                <td>{new Date(item.created_at).toLocaleString('es-MX')}</td>
                <td>{relationshipLabel(item.relationship_code)}</td>
                <td>{FAMILY_STATUS_LABELS[item.status]}</td>
                <td>{activeConditionLabels(item)}</td>
                {canWrite && (
                  <td>
                    <button
                      className={styles.linkButton}
                      type="button"
                      onClick={() => startEdit(item)}
                    >
                      Modificar
                    </button>{' '}
                    <AnnulButton
                      onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })}
                    />
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {activeEntries.length === 0 && <p>Sin antecedentes heredofamiliares registrados.</p>}
      </div>

      {canWrite && editingEntry && <EditingBanner createdAt={editingEntry.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <select
            aria-label="Parentesco"
            value={relationshipCode}
            onChange={(e) => setRelationshipCode(e.target.value)}
          >
            <option value="">Selecciona un parentesco...</option>
            {relationshipCatalog.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </select>
          <select
            aria-label="Estado del familiar"
            value={status}
            onChange={(e) => setStatus(e.target.value as FamilyStatus)}
          >
            {Object.entries(FAMILY_STATUS_LABELS).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
          <p className={styles.fieldsetLabel}>Condiciones</p>
          <div className={styles.checkboxGrid}>
            {conditionCatalog.map((item) => (
              <label key={item.code} className={styles.checkboxItem}>
                <input
                  type="checkbox"
                  checked={conditions[item.code] ?? false}
                  onChange={(e) =>
                    setConditions((prev) => ({ ...prev, [item.code]: e.target.checked }))
                  }
                />
                {item.name}
              </label>
            ))}
          </div>
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || !relationshipCode || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {editingEntry ? 'Guardar cambios' : 'Agregar antecedente heredofamiliar'}
          </button>
          {editingId && (
            <button className={styles.linkButton} type="button" onClick={cancelEdit}>
              Cancelar edición
            </button>
          )}
        </form>
      )}
    </details>
  )
}

const PATHOLOGICAL_DEFAULTS = {
  dolor_masticar: false,
  sensibilidad_frio: false,
  sensibilidad_calor: false,
  sensibilidad_dulce: false,
  sensibilidad_localizacion: '',
  sangrado_encias: 'nunca' as BleedingGumsLevel,
  dolor_cepillado: false,
  aftas_ulceras: false,
  perdida_piezas: false,
  perdida_piezas_causa: '',
  anestesia_previa: false,
  extracciones: false,
  extracciones_texto: '',
  complicaciones_operatorias: false,
  complicaciones_operatorias_texto: '',
  traumatismo_dental: false,
  traumatismo_dental_texto: '',
  infecciones_dentales: false,
  infecciones_dentales_texto: '',
  estres: false,
  estres_texto: '',
  hospitalizacion_emergencia: false,
  hospitalizacion_emergencia_texto: '',
  infecciones_frecuentes: false,
  infecciones_frecuentes_zona: '',
  tiempo_evolucion: '',
}

const PATHOLOGICAL_BOOLEAN_TEXT_FIELDS: {
  key: keyof typeof PATHOLOGICAL_DEFAULTS
  textKey: keyof typeof PATHOLOGICAL_DEFAULTS
  label: string
}[] = [
  { key: 'extracciones', textKey: 'extracciones_texto', label: 'Extracciones' },
  {
    key: 'complicaciones_operatorias',
    textKey: 'complicaciones_operatorias_texto',
    label: 'Complicaciones operatorias',
  },
  { key: 'traumatismo_dental', textKey: 'traumatismo_dental_texto', label: 'Traumatismo dental' },
  {
    key: 'infecciones_dentales',
    textKey: 'infecciones_dentales_texto',
    label: 'Infecciones dentales',
  },
  { key: 'estres', textKey: 'estres_texto', label: 'Estrés' },
  {
    key: 'hospitalizacion_emergencia',
    textKey: 'hospitalizacion_emergencia_texto',
    label: 'Hospitalización de emergencia',
  },
]

function PathologicalHistorySection({
  patientId,
  canWrite,
  encounterPicker,
  diseaseCatalog,
}: {
  patientId: string
  canWrite: boolean
  encounterPicker: EncounterPicker
  diseaseCatalog: CatalogItemOut[]
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['general-history-pathological', patientId],
    queryFn: () => recordsApi.listPathologicalHistory(patientId),
  })

  const { encounterId } = encounterPicker
  const [form, setForm] = useState(PATHOLOGICAL_DEFAULTS)
  const [diseases, setDiseases] = useState<Record<string, DiseaseEntry>>({})
  // Punto 3: "Ninguna" es mutuamente excluyente con el resto del checklist de
  // Enfermedades -- solo de UI, no se envia como codigo de catalogo.
  const [noDiseases, setNoDiseases] = useState(false)

  function update<K extends keyof typeof PATHOLOGICAL_DEFAULTS>(
    key: K,
    value: (typeof PATHOLOGICAL_DEFAULTS)[K],
  ) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  function toggleDisease(code: string, present: boolean) {
    setDiseases((prev) => ({ ...prev, [code]: { ...prev[code], present } }))
    if (present) setNoDiseases(false)
  }

  function toggleNoDiseases(checked: boolean) {
    setNoDiseases(checked)
    if (checked) setDiseases({})
  }

  // Correccion UX (ronda 2.2): esta seccion es "una sola entrada vigente a la
  // vez" -- la mas reciente activa se precarga en el formulario para editarla
  // (anular+recapturar por dentro) en vez de siempre invitar a "agregar otra".
  const current = latestActive(listQuery.data)

  useEffect(() => {
    if (current) {
      // Correccion UX (ronda 2.2): precarga intencional del formulario al
      // cambiar la entrada activa a editar -- no es sincronizacion con un
      // sistema externo, por eso se suprime la regla.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setForm({
        dolor_masticar: current.dolor_masticar,
        sensibilidad_frio: current.sensibilidad_frio,
        sensibilidad_calor: current.sensibilidad_calor,
        sensibilidad_dulce: current.sensibilidad_dulce,
        sensibilidad_localizacion: current.sensibilidad_localizacion ?? '',
        sangrado_encias: current.sangrado_encias,
        dolor_cepillado: current.dolor_cepillado,
        aftas_ulceras: current.aftas_ulceras,
        perdida_piezas: current.perdida_piezas,
        perdida_piezas_causa: current.perdida_piezas_causa ?? '',
        anestesia_previa: current.anestesia_previa,
        extracciones: current.extracciones,
        extracciones_texto: current.extracciones_texto ?? '',
        complicaciones_operatorias: current.complicaciones_operatorias,
        complicaciones_operatorias_texto: current.complicaciones_operatorias_texto ?? '',
        traumatismo_dental: current.traumatismo_dental,
        traumatismo_dental_texto: current.traumatismo_dental_texto ?? '',
        infecciones_dentales: current.infecciones_dentales,
        infecciones_dentales_texto: current.infecciones_dentales_texto ?? '',
        estres: current.estres,
        estres_texto: current.estres_texto ?? '',
        hospitalizacion_emergencia: current.hospitalizacion_emergencia,
        hospitalizacion_emergencia_texto: current.hospitalizacion_emergencia_texto ?? '',
        infecciones_frecuentes: current.infecciones_frecuentes,
        infecciones_frecuentes_zona: current.infecciones_frecuentes_zona ?? '',
        tiempo_evolucion: current.tiempo_evolucion ?? '',
      })
      setDiseases(current.diseases)
      setNoDiseases(false)
    } else {
      setForm(PATHOLOGICAL_DEFAULTS)
      setDiseases({})
      setNoDiseases(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      // Punto 5: campos opcionales vacios se normalizan a null (no '') antes de
      // enviar -- el backend los declara `str | None`.
      saveWithAutoCorrection(
        current,
        (itemId, reason) => recordsApi.annulPathologicalHistory(patientId, itemId, reason),
        () =>
          recordsApi.createPathologicalHistory(patientId, {
            encounter_id: encounterId,
            dolor_masticar: form.dolor_masticar,
            sensibilidad_frio: form.sensibilidad_frio,
            sensibilidad_calor: form.sensibilidad_calor,
            sensibilidad_dulce: form.sensibilidad_dulce,
            sensibilidad_localizacion: form.sensibilidad_localizacion || null,
            sangrado_encias: form.sangrado_encias,
            dolor_cepillado: form.dolor_cepillado,
            aftas_ulceras: form.aftas_ulceras,
            perdida_piezas: form.perdida_piezas,
            perdida_piezas_causa: form.perdida_piezas_causa || null,
            anestesia_previa: form.anestesia_previa,
            extracciones: form.extracciones,
            extracciones_texto: form.extracciones_texto || null,
            complicaciones_operatorias: form.complicaciones_operatorias,
            complicaciones_operatorias_texto: form.complicaciones_operatorias_texto || null,
            traumatismo_dental: form.traumatismo_dental,
            traumatismo_dental_texto: form.traumatismo_dental_texto || null,
            infecciones_dentales: form.infecciones_dentales,
            infecciones_dentales_texto: form.infecciones_dentales_texto || null,
            estres: form.estres,
            estres_texto: form.estres_texto || null,
            hospitalizacion_emergencia: form.hospitalizacion_emergencia,
            hospitalizacion_emergencia_texto: form.hospitalizacion_emergencia_texto || null,
            infecciones_frecuentes: form.infecciones_frecuentes,
            infecciones_frecuentes_zona: form.infecciones_frecuentes_zona || null,
            tiempo_evolucion: form.tiempo_evolucion || null,
            diseases,
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-history-pathological', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      recordsApi.annulPathologicalHistory(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-history-pathological', patientId] })
    },
  })

  // Punto 6: vista detallada (todos los campos capturados), en vez del resumen
  // de una sola linea que omitia la mayoria.
  function detailRows(item: PersonalPathologicalHistoryOut): [string, string][] {
    const rows: [string, string][] = []
    if (item.dolor_masticar) rows.push(['Dolor al masticar', 'Sí'])
    if (item.sensibilidad_frio) rows.push(['Sensibilidad al frío', 'Sí'])
    if (item.sensibilidad_calor) rows.push(['Sensibilidad al calor', 'Sí'])
    if (item.sensibilidad_dulce) rows.push(['Sensibilidad al dulce', 'Sí'])
    if (item.sensibilidad_localizacion) {
      rows.push(['Localización de la sensibilidad', item.sensibilidad_localizacion])
    }
    if (item.sangrado_encias !== 'nunca') {
      rows.push(['Sangrado de encías', BLEEDING_GUMS_LABELS[item.sangrado_encias]])
    }
    if (item.dolor_cepillado) rows.push(['Dolor al cepillado', 'Sí'])
    if (item.aftas_ulceras) rows.push(['Aftas o úlceras', 'Sí'])
    if (item.perdida_piezas) rows.push(['Pérdida de piezas', item.perdida_piezas_causa || 'Sí'])
    if (item.anestesia_previa) rows.push(['Anestesia previa', 'Sí'])
    for (const { key, textKey, label } of PATHOLOGICAL_BOOLEAN_TEXT_FIELDS) {
      if (item[key as keyof PersonalPathologicalHistoryOut] as boolean) {
        const detail = item[textKey as keyof PersonalPathologicalHistoryOut] as string | null
        rows.push([label, detail || 'Sí'])
      }
    }
    if (item.infecciones_frecuentes) {
      rows.push(['Infecciones frecuentes', item.infecciones_frecuentes_zona || 'Sí'])
    }
    if (item.tiempo_evolucion) rows.push(['Tiempo de evolución', item.tiempo_evolucion])
    const presentDiseases = Object.entries(item.diseases)
      .filter(([, info]) => info.present)
      .map(([code, info]) => {
        const name = diseaseCatalog.find((c) => c.code === code)?.name ?? code
        return info.evolution ? `${name} (${info.evolution})` : name
      })
    if (presentDiseases.length > 0) rows.push(['Enfermedades', presentDiseases.join(', ')])
    return rows
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Antecedentes personales patológicos
        <MissingDataBadge hasActiveEntries={activeEntries.length > 0} />
      </summary>
      {listQuery.data?.map((item) => (
        <div key={item.id} className={styles.contactItem}>
          <div>
            <p>
              {new Date(item.created_at).toLocaleString('es-MX')}
              {!item.is_active && ' (anulado)'}
            </p>
            <DetailList rows={detailRows(item)} />
          </div>
          {canWrite && item.is_active && (
            <AnnulButton onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })} />
          )}
        </div>
      ))}
      {listQuery.data?.length === 0 && <p>Sin antecedentes patológicos registrados.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <div className={styles.checkboxGrid}>
            <label className={styles.checkboxItem}>
              <input
                type="checkbox"
                checked={form.dolor_masticar}
                onChange={(e) => update('dolor_masticar', e.target.checked)}
              />
              Dolor al masticar
            </label>
            <label className={styles.checkboxItem}>
              <input
                type="checkbox"
                checked={form.sensibilidad_frio}
                onChange={(e) => update('sensibilidad_frio', e.target.checked)}
              />
              Sensibilidad al frío
            </label>
            <label className={styles.checkboxItem}>
              <input
                type="checkbox"
                checked={form.sensibilidad_calor}
                onChange={(e) => update('sensibilidad_calor', e.target.checked)}
              />
              Sensibilidad al calor
            </label>
            <label className={styles.checkboxItem}>
              <input
                type="checkbox"
                checked={form.sensibilidad_dulce}
                onChange={(e) => update('sensibilidad_dulce', e.target.checked)}
              />
              Sensibilidad al dulce
            </label>
          </div>
          <input
            type="text"
            placeholder="Localización de la sensibilidad (opcional)"
            value={form.sensibilidad_localizacion}
            onChange={(e) => update('sensibilidad_localizacion', e.target.value)}
          />
          <select
            aria-label="Sangrado de encías"
            value={form.sangrado_encias}
            onChange={(e) => update('sangrado_encias', e.target.value as BleedingGumsLevel)}
          >
            {Object.entries(BLEEDING_GUMS_LABELS).map(([code, label]) => (
              <option key={code} value={code}>
                Sangrado de encías: {label}
              </option>
            ))}
          </select>
          <div className={styles.checkboxGrid}>
            <label className={styles.checkboxItem}>
              <input
                type="checkbox"
                checked={form.dolor_cepillado}
                onChange={(e) => update('dolor_cepillado', e.target.checked)}
              />
              Dolor al cepillado
            </label>
            <label className={styles.checkboxItem}>
              <input
                type="checkbox"
                checked={form.aftas_ulceras}
                onChange={(e) => update('aftas_ulceras', e.target.checked)}
              />
              Aftas o úlceras
            </label>
            <label className={styles.checkboxItem}>
              <input
                type="checkbox"
                checked={form.anestesia_previa}
                onChange={(e) => update('anestesia_previa', e.target.checked)}
              />
              Anestesia previa
            </label>
          </div>
          <label className={styles.checkboxRowWithText}>
            <input
              type="checkbox"
              checked={form.perdida_piezas}
              onChange={(e) => update('perdida_piezas', e.target.checked)}
            />
            Pérdida de piezas
            {form.perdida_piezas && (
              <input
                type="text"
                placeholder="Causa"
                value={form.perdida_piezas_causa}
                onChange={(e) => update('perdida_piezas_causa', e.target.value)}
              />
            )}
          </label>
          {PATHOLOGICAL_BOOLEAN_TEXT_FIELDS.map(({ key, textKey, label }) => (
            <label key={key} className={styles.checkboxRowWithText}>
              <input
                type="checkbox"
                checked={form[key] as boolean}
                onChange={(e) => update(key, e.target.checked as (typeof form)[typeof key])}
              />
              {label}
              {(form[key] as boolean) && (
                <input
                  type="text"
                  placeholder="Detalle"
                  value={form[textKey] as string}
                  onChange={(e) => update(textKey, e.target.value as (typeof form)[typeof textKey])}
                />
              )}
            </label>
          ))}
          <label className={styles.checkboxRowWithText}>
            <input
              type="checkbox"
              checked={form.infecciones_frecuentes}
              onChange={(e) => update('infecciones_frecuentes', e.target.checked)}
            />
            Infecciones frecuentes
            {form.infecciones_frecuentes && (
              <input
                type="text"
                placeholder="Zona"
                value={form.infecciones_frecuentes_zona}
                onChange={(e) => update('infecciones_frecuentes_zona', e.target.value)}
              />
            )}
          </label>
          <input
            type="text"
            placeholder="Tiempo de evolución (opcional)"
            value={form.tiempo_evolucion}
            onChange={(e) => update('tiempo_evolucion', e.target.value)}
          />
          <p className={styles.fieldsetLabel}>Enfermedades</p>
          <div className={styles.checkboxGrid}>
            <label className={styles.checkboxItem}>
              <input
                type="checkbox"
                checked={noDiseases}
                onChange={(e) => toggleNoDiseases(e.target.checked)}
              />
              Ninguna
            </label>
            {diseaseCatalog.map((item) => (
              <label key={item.code} className={styles.checkboxRowWithText}>
                <input
                  type="checkbox"
                  checked={diseases[item.code]?.present ?? false}
                  onChange={(e) => toggleDisease(item.code, e.target.checked)}
                />
                {item.name}
                {diseases[item.code]?.present && (
                  <input
                    type="text"
                    placeholder="Evolución"
                    value={diseases[item.code]?.evolution ?? ''}
                    onChange={(e) =>
                      setDiseases((prev) => ({
                        ...prev,
                        [item.code]: { ...prev[item.code], present: true, evolution: e.target.value },
                      }))
                    }
                  />
                )}
              </label>
            ))}
          </div>
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Agregar antecedente patológico'}
          </button>
        </form>
      )}
    </details>
  )
}

const NON_PATHOLOGICAL_DEFAULTS = {
  comidas_dia: '',
  calidad_alimentacion: '' as FoodQualityLevel | '',
  agua_litros_dia: '',
  trastornos_sueno: false,
  trastornos_sueno_texto: '',
  cepillados_dia: '',
  hilo_dental: false,
  enjuague_bucal: false,
  deportes: false,
  deportes_cual: '',
  derechohabiencia: '' as HealthCoverageType | '',
  // Correccion Fase A: estado_civil ya no es un catalogo cerrado -- el select
  // ofrece MARITAL_STATUSES como sugerencias mas "otro" con texto libre a
  // teclear (estado_civil_otro). El valor final que se envia es `string`.
  estado_civil_option: '' as MaritalStatus | 'otro' | '',
  estado_civil_otro: '',
  medicamentos_suplementos: false,
  medicamentos_controlados: false,
  medicamentos_texto: '',
}

function NonPathologicalHistorySection({
  patientId,
  canWrite,
  encounterPicker,
}: {
  patientId: string
  canWrite: boolean
  encounterPicker: EncounterPicker
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['general-history-non-pathological', patientId],
    queryFn: () => recordsApi.listNonPathologicalHistory(patientId),
  })

  const { encounterId } = encounterPicker
  const [form, setForm] = useState(NON_PATHOLOGICAL_DEFAULTS)
  const [servicios, setServicios] = useState<Record<string, ServiceEntry>>({})
  const [adicciones, setAdicciones] = useState<Record<string, AddictionEntry>>({})
  // Punto 3: "Ninguna" mutuamente excluyente en el checklist de Adicciones.
  const [noAddictions, setNoAddictions] = useState(false)

  function update<K extends keyof typeof NON_PATHOLOGICAL_DEFAULTS>(
    key: K,
    value: (typeof NON_PATHOLOGICAL_DEFAULTS)[K],
  ) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  function toggleAddiction(key: string, has: boolean) {
    setAdicciones((prev) => ({ ...prev, [key]: { ...prev[key], has } }))
    if (has) setNoAddictions(false)
  }

  function toggleNoAddictions(checked: boolean) {
    setNoAddictions(checked)
    if (checked) setAdicciones({})
  }

  // Punto 4: el valor final de estado_civil es texto libre -- si eligio una
  // opcion sugerida se envia tal cual, si eligio "Otro" se envia lo que
  // escribio (o el literal "otro" si lo dejo vacio).
  const estadoCivilFinal =
    form.estado_civil_option === ''
      ? null
      : form.estado_civil_option === 'otro'
        ? form.estado_civil_otro.trim() || 'otro'
        : form.estado_civil_option

  // Correccion UX (ronda 2.2): entrada activa mas reciente -- se precarga el
  // formulario para "editarla" (anular+recapturar por dentro).
  const current = latestActive(listQuery.data)

  useEffect(() => {
    if (current) {
      const knownStatus =
        current.estado_civil && MARITAL_STATUSES.includes(current.estado_civil as MaritalStatus)
          ? (current.estado_civil as MaritalStatus)
          : null
      // Correccion UX (ronda 2.2): precarga intencional del formulario al
      // cambiar la entrada activa a editar -- no es sincronizacion con un
      // sistema externo, por eso se suprime la regla.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setForm({
        comidas_dia: current.comidas_dia != null ? String(current.comidas_dia) : '',
        calidad_alimentacion: current.calidad_alimentacion ?? '',
        agua_litros_dia: current.agua_litros_dia != null ? String(current.agua_litros_dia) : '',
        trastornos_sueno: current.trastornos_sueno,
        trastornos_sueno_texto: current.trastornos_sueno_texto ?? '',
        cepillados_dia: current.cepillados_dia != null ? String(current.cepillados_dia) : '',
        hilo_dental: current.hilo_dental,
        enjuague_bucal: current.enjuague_bucal,
        deportes: current.deportes,
        deportes_cual: current.deportes_cual ?? '',
        derechohabiencia: current.derechohabiencia ?? '',
        estado_civil_option: knownStatus ?? (current.estado_civil ? 'otro' : ''),
        estado_civil_otro: knownStatus ? '' : (current.estado_civil ?? ''),
        medicamentos_suplementos: current.medicamentos_suplementos,
        medicamentos_controlados: current.medicamentos_controlados,
        medicamentos_texto: current.medicamentos_texto ?? '',
      })
      setServicios(current.servicios_basicos)
      setAdicciones(current.adicciones)
      setNoAddictions(false)
    } else {
      setForm(NON_PATHOLOGICAL_DEFAULTS)
      setServicios({})
      setAdicciones({})
      setNoAddictions(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => recordsApi.annulNonPathologicalHistory(patientId, itemId, reason),
        () =>
          recordsApi.createNonPathologicalHistory(patientId, {
            encounter_id: encounterId,
            // Punto 5: campos opcionales vacios se normalizan a null (no ''), y
            // comidas_dia/cepillados_dia se redondean a entero antes de enviar
            // (el backend los declara `int`, ge=0 le=20 -- un decimal como "2.5"
            // causaba 422 "datos de entrada invalidos").
            comidas_dia: form.comidas_dia ? Math.round(Number(form.comidas_dia)) : null,
            calidad_alimentacion: form.calidad_alimentacion || null,
            agua_litros_dia: form.agua_litros_dia ? Number(form.agua_litros_dia) : null,
            trastornos_sueno: form.trastornos_sueno,
            trastornos_sueno_texto: form.trastornos_sueno_texto || null,
            cepillados_dia: form.cepillados_dia ? Math.round(Number(form.cepillados_dia)) : null,
            hilo_dental: form.hilo_dental,
            enjuague_bucal: form.enjuague_bucal,
            deportes: form.deportes,
            deportes_cual: form.deportes_cual || null,
            derechohabiencia: form.derechohabiencia || null,
            estado_civil: estadoCivilFinal,
            medicamentos_suplementos: form.medicamentos_suplementos,
            medicamentos_controlados: form.medicamentos_controlados,
            medicamentos_texto: form.medicamentos_texto || null,
            servicios_basicos: servicios,
            adicciones,
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-history-non-pathological', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      recordsApi.annulNonPathologicalHistory(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-history-non-pathological', patientId] })
    },
  })

  // Punto 6: vista detallada (todos los campos capturados), en vez del resumen
  // de una sola linea que omitia la mayoria.
  function detailRows(item: PersonalNonPathologicalHistoryOut): [string, string][] {
    const rows: [string, string][] = []
    if (item.comidas_dia != null) rows.push(['Comidas al día', String(item.comidas_dia)])
    if (item.calidad_alimentacion) {
      rows.push(['Calidad de la alimentación', FOOD_QUALITY_LABELS[item.calidad_alimentacion]])
    }
    if (item.agua_litros_dia != null) {
      rows.push(['Agua (litros/día)', String(item.agua_litros_dia)])
    }
    if (item.trastornos_sueno) {
      rows.push(['Trastornos del sueño', item.trastornos_sueno_texto || 'Sí'])
    }
    if (item.cepillados_dia != null) rows.push(['Cepillados al día', String(item.cepillados_dia)])
    if (item.hilo_dental) rows.push(['Hilo dental', 'Sí'])
    if (item.enjuague_bucal) rows.push(['Enjuague bucal', 'Sí'])
    if (item.deportes) rows.push(['Practica deportes', item.deportes_cual || 'Sí'])
    if (item.derechohabiencia) rows.push(['Derechohabiencia', HEALTH_COVERAGE_LABELS[item.derechohabiencia]])
    if (item.estado_civil) rows.push(['Estado civil', item.estado_civil])
    if (item.medicamentos_suplementos) rows.push(['Medicamentos o suplementos', 'Sí'])
    if (item.medicamentos_controlados) rows.push(['Medicamentos controlados', 'Sí'])
    if (item.medicamentos_texto) rows.push(['Detalle de medicamentos', item.medicamentos_texto])
    const activeServices = Object.entries(item.servicios_basicos)
      .filter(([, info]) => info.has)
      .map(
        ([key]) =>
          SERVICIOS_BASICOS_LABELS[key as keyof typeof SERVICIOS_BASICOS_LABELS] ?? key,
      )
    if (activeServices.length > 0) rows.push(['Servicios básicos', activeServices.join(', ')])
    const activeAddictions = Object.entries(item.adicciones)
      .filter(([, info]) => info.has)
      .map(([code, info]) => {
        const name = ADICCIONES_LABELS[code as keyof typeof ADICCIONES_LABELS] ?? code
        return info.detail ? `${name} (${info.detail})` : name
      })
    if (activeAddictions.length > 0) rows.push(['Adicciones', activeAddictions.join(', ')])
    return rows
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Antecedentes personales no patológicos
        <MissingDataBadge hasActiveEntries={activeEntries.length > 0} />
      </summary>
      {listQuery.data?.map((item) => (
        <div key={item.id} className={styles.contactItem}>
          <div>
            <p>
              {new Date(item.created_at).toLocaleString('es-MX')}
              {!item.is_active && ' (anulado)'}
            </p>
            <DetailList rows={detailRows(item)} />
          </div>
          {canWrite && item.is_active && (
            <AnnulButton onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })} />
          )}
        </div>
      ))}
      {listQuery.data?.length === 0 && <p>Sin antecedentes no patológicos registrados.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <input
            type="number"
            step="1"
            min="0"
            max="20"
            placeholder="Comidas al día"
            value={form.comidas_dia}
            onChange={(e) => update('comidas_dia', e.target.value)}
          />
          <select
            aria-label="Calidad de la alimentación"
            value={form.calidad_alimentacion}
            onChange={(e) => update('calidad_alimentacion', e.target.value as FoodQualityLevel | '')}
          >
            <option value="">Calidad de alimentación: sin especificar</option>
            {Object.entries(FOOD_QUALITY_LABELS).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
          <input
            type="number"
            step="0.1"
            placeholder="Agua (litros/día)"
            value={form.agua_litros_dia}
            onChange={(e) => update('agua_litros_dia', e.target.value)}
          />
          <label className={styles.checkboxRowWithText}>
            <input
              type="checkbox"
              checked={form.trastornos_sueno}
              onChange={(e) => update('trastornos_sueno', e.target.checked)}
            />
            Trastornos del sueño
            {form.trastornos_sueno && (
              <input
                type="text"
                placeholder="Detalle"
                value={form.trastornos_sueno_texto}
                onChange={(e) => update('trastornos_sueno_texto', e.target.value)}
              />
            )}
          </label>
          <input
            type="number"
            step="1"
            min="0"
            max="20"
            placeholder="Cepillados al día"
            value={form.cepillados_dia}
            onChange={(e) => update('cepillados_dia', e.target.value)}
          />
          <div className={styles.checkboxGrid}>
            <label className={styles.checkboxItem}>
              <input
                type="checkbox"
                checked={form.hilo_dental}
                onChange={(e) => update('hilo_dental', e.target.checked)}
              />
              Hilo dental
            </label>
            <label className={styles.checkboxItem}>
              <input
                type="checkbox"
                checked={form.enjuague_bucal}
                onChange={(e) => update('enjuague_bucal', e.target.checked)}
              />
              Enjuague bucal
            </label>
          </div>
          <label className={styles.checkboxRowWithText}>
            <input
              type="checkbox"
              checked={form.deportes}
              onChange={(e) => update('deportes', e.target.checked)}
            />
            Practica deportes
            {form.deportes && (
              <input
                type="text"
                placeholder="¿Cuál?"
                value={form.deportes_cual}
                onChange={(e) => update('deportes_cual', e.target.value)}
              />
            )}
          </label>
          <select
            aria-label="Derechohabiencia"
            value={form.derechohabiencia}
            onChange={(e) => update('derechohabiencia', e.target.value as HealthCoverageType | '')}
          >
            <option value="">Derechohabiencia: sin especificar</option>
            {Object.entries(HEALTH_COVERAGE_LABELS).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
          <select
            aria-label="Estado civil (no patológico)"
            value={form.estado_civil_option}
            onChange={(e) =>
              update('estado_civil_option', e.target.value as MaritalStatus | 'otro' | '')
            }
          >
            <option value="">Estado civil: sin especificar</option>
            {MARITAL_STATUSES.map((code) => (
              <option key={code} value={code}>
                {MARITAL_STATUS_LABELS[code]}
              </option>
            ))}
            <option value="otro">Otro</option>
          </select>
          {form.estado_civil_option === 'otro' && (
            <input
              type="text"
              aria-label="Estado civil: cual otro"
              placeholder="¿Cuál?"
              maxLength={60}
              value={form.estado_civil_otro}
              onChange={(e) => update('estado_civil_otro', e.target.value)}
            />
          )}
          <div className={styles.checkboxGrid}>
            <label className={styles.checkboxItem}>
              <input
                type="checkbox"
                checked={form.medicamentos_suplementos}
                onChange={(e) => update('medicamentos_suplementos', e.target.checked)}
              />
              Medicamentos o suplementos
            </label>
            <label className={styles.checkboxItem}>
              <input
                type="checkbox"
                checked={form.medicamentos_controlados}
                onChange={(e) => update('medicamentos_controlados', e.target.checked)}
              />
              Medicamentos controlados
            </label>
          </div>
          <input
            type="text"
            placeholder="Detalle de medicamentos (opcional)"
            value={form.medicamentos_texto}
            onChange={(e) => update('medicamentos_texto', e.target.value)}
          />
          <p className={styles.fieldsetLabel}>Servicios básicos</p>
          <div className={styles.checkboxGrid}>
            {SERVICIOS_BASICOS_KEYS.map((key) => (
              <label key={key} className={styles.checkboxItem}>
                <input
                  type="checkbox"
                  checked={servicios[key]?.has ?? false}
                  onChange={(e) =>
                    setServicios((prev) => ({
                      ...prev,
                      [key]: { ...prev[key], has: e.target.checked },
                    }))
                  }
                />
                {SERVICIOS_BASICOS_LABELS[key]}
              </label>
            ))}
          </div>
          <p className={styles.fieldsetLabel}>Adicciones</p>
          <div className={styles.checkboxGrid}>
            <label className={styles.checkboxItem}>
              <input
                type="checkbox"
                checked={noAddictions}
                onChange={(e) => toggleNoAddictions(e.target.checked)}
              />
              Ninguna
            </label>
            {ADICCIONES_KEYS.map((key) => (
              <label key={key} className={styles.checkboxRowWithText}>
                <input
                  type="checkbox"
                  checked={adicciones[key]?.has ?? false}
                  onChange={(e) => toggleAddiction(key, e.target.checked)}
                />
                {ADICCIONES_LABELS[key]}
                {adicciones[key]?.has && (
                  <input
                    type="text"
                    placeholder="Detalle"
                    value={adicciones[key]?.detail ?? ''}
                    onChange={(e) =>
                      setAdicciones((prev) => ({
                        ...prev,
                        [key]: { ...prev[key], has: true, detail: e.target.value },
                      }))
                    }
                  />
                )}
              </label>
            ))}
          </div>
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Agregar antecedente no patológico'}
          </button>
        </form>
      )}
    </details>
  )
}

function SystemsReviewSection({
  patientId,
  canWrite,
  encounterPicker,
  findingCatalog,
}: {
  patientId: string
  canWrite: boolean
  encounterPicker: EncounterPicker
  findingCatalog: CatalogItemOut[]
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['general-history-systems-review', patientId],
    queryFn: () => recordsApi.listSystemsReview(patientId),
  })

  const { encounterId } = encounterPicker
  const [findings, setFindings] = useState<Record<string, Record<string, DiseaseEntry>>>({})
  const [reproductorMasculino, setReproductorMasculino] = useState<Record<string, unknown>>({})
  const [reproductorFemenino, setReproductorFemenino] = useState<Record<string, unknown>>({})
  // Punto 3: "Niega todos / Negados" mutuamente excluyente DENTRO de cada
  // aparato/sistema (un booleano por sistema, no global).
  const [negatedSystems, setNegatedSystems] = useState<Record<string, boolean>>({})

  function toggleFinding(system: string, code: string, present: boolean) {
    setFindings((prev) => ({
      ...prev,
      [system]: { ...prev[system], [code]: { ...prev[system]?.[code], present } },
    }))
    if (present) setNegatedSystems((prev) => ({ ...prev, [system]: false }))
  }

  function setFindingEvolution(system: string, code: string, evolution: string) {
    setFindings((prev) => ({
      ...prev,
      [system]: { ...prev[system], [code]: { ...prev[system]?.[code], present: true, evolution } },
    }))
  }

  function toggleNegatedSystem(system: string, checked: boolean) {
    setNegatedSystems((prev) => ({ ...prev, [system]: checked }))
    if (checked) setFindings((prev) => ({ ...prev, [system]: {} }))
  }

  // Correccion UX (ronda 2.2): entrada activa mas reciente -- se precarga el
  // formulario para "editarla" (anular+recapturar por dentro).
  const current = latestActive(listQuery.data)

  useEffect(() => {
    if (current) {
      // Correccion UX (ronda 2.2): precarga intencional del formulario al
      // cambiar la entrada activa a editar -- no es sincronizacion con un
      // sistema externo, por eso se suprime la regla.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFindings({
        hematologico: current.hematologico,
        cardiovascular: current.cardiovascular,
        neurologico: current.neurologico,
        endocrino: current.endocrino,
        respiratorio: current.respiratorio,
        genitourinario: current.genitourinario,
      })
      setReproductorMasculino(current.reproductor_masculino)
      setReproductorFemenino(current.reproductor_femenino)
      setNegatedSystems({})
    } else {
      setFindings({})
      setReproductorMasculino({})
      setReproductorFemenino({})
      setNegatedSystems({})
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => recordsApi.annulSystemsReview(patientId, itemId, reason),
        () =>
          recordsApi.createSystemsReview(patientId, {
            encounter_id: encounterId,
            hematologico: findings.hematologico ?? {},
            cardiovascular: findings.cardiovascular ?? {},
            neurologico: findings.neurologico ?? {},
            endocrino: findings.endocrino ?? {},
            respiratorio: findings.respiratorio ?? {},
            genitourinario: findings.genitourinario ?? {},
            reproductor_masculino: reproductorMasculino,
            reproductor_femenino: reproductorFemenino,
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-history-systems-review', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      recordsApi.annulSystemsReview(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-history-systems-review', patientId] })
    },
  })

  // Punto 6: vista detallada (todos los campos capturados, incluyendo
  // reproductor masculino/femenino -- BUG confirmado: el resumen anterior
  // nunca los mostraba aunque si se capturaban y guardaban).
  function detailRows(item: SystemsReviewEntryOut): [string, string][] {
    const rows: [string, string][] = []
    for (const system of SYSTEMS_REVIEW_SYSTEMS) {
      const entries = Object.entries(item[system])
        .filter(([, info]) => info.present)
        .map(([code, info]) => {
          const name = findingCatalog.find((c) => c.code === code)?.name ?? code
          return info.evolution ? `${name} (${info.evolution})` : name
        })
      if (entries.length > 0) {
        rows.push([SYSTEMS_REVIEW_SYSTEM_LABELS[system], entries.join(', ')])
      }
    }
    for (const field of REPRODUCTOR_MASCULINO_FIELDS) {
      const value = item.reproductor_masculino[field.key]
      if (field.type === 'checkbox') {
        if (value) rows.push([field.label, 'Sí'])
      } else if (value) {
        rows.push([field.label, String(value)])
      }
    }
    for (const field of REPRODUCTOR_FEMENINO_FIELDS) {
      const value = item.reproductor_femenino[field.key]
      if (field.type === 'checkbox') {
        if (value) rows.push([field.label, 'Sí'])
      } else if (value) {
        rows.push([field.label, String(value)])
      }
    }
    return rows
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Interrogatorio por aparatos y sistemas
        <MissingDataBadge hasActiveEntries={activeEntries.length > 0} />
      </summary>
      {listQuery.data?.map((item) => (
        <div key={item.id} className={styles.contactItem}>
          <div>
            <p>
              {new Date(item.created_at).toLocaleString('es-MX')}
              {!item.is_active && ' (anulado)'}
            </p>
            <DetailList rows={detailRows(item)} />
          </div>
          {canWrite && item.is_active && (
            <AnnulButton onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })} />
          )}
        </div>
      ))}
      {listQuery.data?.length === 0 && <p>Sin interrogatorio por aparatos y sistemas registrado.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          {SYSTEMS_REVIEW_SYSTEMS.map((system) => {
            const items = findingCatalog.filter((c) => c.extra.system === system)
            if (items.length === 0) return null
            return (
              <div key={system}>
                <p className={styles.fieldsetLabel}>{SYSTEMS_REVIEW_SYSTEM_LABELS[system]}</p>
                <div className={styles.checkboxGrid}>
                  <label className={styles.checkboxItem}>
                    <input
                      type="checkbox"
                      checked={negatedSystems[system] ?? false}
                      onChange={(e) => toggleNegatedSystem(system, e.target.checked)}
                    />
                    Niega todos
                  </label>
                  {items.map((item) => (
                    <label key={item.code} className={styles.checkboxRowWithText}>
                      <input
                        type="checkbox"
                        checked={findings[system]?.[item.code]?.present ?? false}
                        onChange={(e) => toggleFinding(system, item.code, e.target.checked)}
                      />
                      {item.name}
                      {findings[system]?.[item.code]?.present && (
                        <input
                          type="text"
                          placeholder="Evolución"
                          value={findings[system]?.[item.code]?.evolution ?? ''}
                          onChange={(e) => setFindingEvolution(system, item.code, e.target.value)}
                        />
                      )}
                    </label>
                  ))}
                </div>
              </div>
            )
          })}

          {/* Punto 7: una fila por campo (reutiliza el patron de styles.form, no
              el checkboxGrid denso -- antes se veian amontonados). */}
          <p className={styles.fieldsetLabel}>Reproductor masculino</p>
          <div className={styles.form}>
            {REPRODUCTOR_MASCULINO_FIELDS.map((field) =>
              field.type === 'checkbox' ? (
                <label key={field.key} className={styles.fieldRowCheckbox}>
                  <input
                    type="checkbox"
                    checked={Boolean(reproductorMasculino[field.key])}
                    onChange={(e) =>
                      setReproductorMasculino((prev) => ({ ...prev, [field.key]: e.target.checked }))
                    }
                  />
                  {field.label}
                </label>
              ) : (
                <label key={field.key} className={styles.fieldRow}>
                  <span>{field.label}</span>
                  <input
                    type={field.type}
                    aria-label={field.label}
                    value={(reproductorMasculino[field.key] as string) ?? ''}
                    onChange={(e) =>
                      setReproductorMasculino((prev) => ({ ...prev, [field.key]: e.target.value }))
                    }
                  />
                </label>
              ),
            )}
          </div>

          <p className={styles.fieldsetLabel}>Reproductor femenino</p>
          <div className={styles.form}>
            {REPRODUCTOR_FEMENINO_FIELDS.map((field) =>
              field.type === 'checkbox' ? (
                <label key={field.key} className={styles.fieldRowCheckbox}>
                  <input
                    type="checkbox"
                    checked={Boolean(reproductorFemenino[field.key])}
                    onChange={(e) =>
                      setReproductorFemenino((prev) => ({ ...prev, [field.key]: e.target.checked }))
                    }
                  />
                  {field.label}
                </label>
              ) : (
                <label key={field.key} className={styles.fieldRow}>
                  <span>{field.label}</span>
                  <input
                    type={field.type}
                    aria-label={field.label}
                    value={(reproductorFemenino[field.key] as string) ?? ''}
                    onChange={(e) =>
                      setReproductorFemenino((prev) => ({ ...prev, [field.key]: e.target.value }))
                    }
                  />
                </label>
              ),
            )}
          </div>

          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Agregar interrogatorio por aparatos y sistemas'}
          </button>
        </form>
      )}
    </details>
  )
}

function DiagnosisSection({
  patientId,
  canWrite,
  encounterPicker,
}: {
  patientId: string
  canWrite: boolean
  encounterPicker: EncounterPicker
}) {
  const queryClient = useQueryClient()
  const diagnosesQuery = useQuery({
    queryKey: ['patient-diagnoses', patientId],
    queryFn: () => diagnosisApi.listDiagnoses(patientId),
  })

  const { encounterId } = encounterPicker
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
          <EncounterPickerField encounterPicker={encounterPicker} />
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
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            Agregar diagnostico
          </button>
        </form>
      )}
    </details>
  )
}

/** A4: boton "Imprimir / Generar PDF" de la Historia Clinica General -- mismo
 * patron que documents/ConsentsTab.tsx::showConsentPdf: window.open se llama
 * sincronico (antes del await) para no perder el gesto del usuario y que el
 * bloqueador de ventanas emergentes no lo descarte. */
function GeneralHistoryPdfButton({ patientId }: { patientId: string }) {
  const [error, setError] = useState(false)
  const [generating, setGenerating] = useState(false)

  async function handleClick() {
    setError(false)
    setGenerating(true)
    const newTab = window.open('', '_blank')
    try {
      const url = await recordsApi.getGeneralHistoryPdfBlobUrl(patientId)
      if (newTab) newTab.location.href = url
    } catch {
      newTab?.close()
      setError(true)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className={styles.fullWidth}>
      <button
        className={styles.primaryButton}
        type="button"
        onClick={() => void handleClick()}
        disabled={generating}
      >
        {generating ? 'Generando PDF...' : 'Imprimir / Generar PDF'}
      </button>
      {error && <p className={styles.errorBox}>No se pudo generar el PDF.</p>}
    </div>
  )
}

function GeneralHistoryTab({
  patientId,
  patient,
  canWrite,
  canWriteDiagnosis: canWriteDx,
  encounterPicker,
}: {
  patientId: string
  patient: PatientOut
  canWrite: boolean
  canWriteDiagnosis: boolean
  encounterPicker: EncounterPicker
}) {
  const relationshipCatalogQuery = useQuery({
    queryKey: ['catalog-items', 'family_relationship'],
    queryFn: () => catalogsApi.listCatalogItems('family_relationship', false),
  })
  const familyConditionCatalogQuery = useQuery({
    queryKey: ['catalog-items', 'family_condition'],
    queryFn: () => catalogsApi.listCatalogItems('family_condition', false),
  })
  const diseaseCatalogQuery = useQuery({
    queryKey: ['catalog-items', 'pathological_condition'],
    queryFn: () => catalogsApi.listCatalogItems('pathological_condition', false),
  })
  const findingCatalogQuery = useQuery({
    queryKey: ['catalog-items', 'systems_review_finding'],
    queryFn: () => catalogsApi.listCatalogItems('systems_review_finding', false),
  })

  return (
    <>
      <GeneralHistoryPdfButton patientId={patientId} />
      <DatosGeneralesSection patient={patient} />
      <VitalSignsSection
        patientId={patientId}
        canWrite={canWrite}
        encounterPicker={encounterPicker}
      />
      <FamilyHistorySection
        patientId={patientId}
        canWrite={canWrite}
        encounterPicker={encounterPicker}
        relationshipCatalog={relationshipCatalogQuery.data ?? []}
        conditionCatalog={familyConditionCatalogQuery.data ?? []}
      />
      <PathologicalHistorySection
        patientId={patientId}
        canWrite={canWrite}
        encounterPicker={encounterPicker}
        diseaseCatalog={diseaseCatalogQuery.data ?? []}
      />
      <NonPathologicalHistorySection
        patientId={patientId}
        canWrite={canWrite}
        encounterPicker={encounterPicker}
      />
      <SystemsReviewSection
        patientId={patientId}
        canWrite={canWrite}
        encounterPicker={encounterPicker}
        findingCatalog={findingCatalogQuery.data ?? []}
      />
      <AllergiesSection
        patientId={patientId}
        canWrite={canWrite}
        encounterPicker={encounterPicker}
      />
      <MedicationsSection
        patientId={patientId}
        canWrite={canWrite}
        encounterPicker={encounterPicker}
      />
      <DiagnosisSection
        patientId={patientId}
        canWrite={canWriteDx}
        encounterPicker={encounterPicker}
      />
    </>
  )
}

type HistoryTab = 'general' | 'odontologica' | 'pediatrica' | 'endodoncia'

const HISTORY_TAB_LABELS: Record<HistoryTab, string> = {
  general: 'Historia Clínica General',
  odontologica: 'Historia Clínica Odontológica',
  pediatrica: 'Historia Clínica Pediátrica',
  endodoncia: 'Historia Clínica de Endodoncia',
}

export function ExpedienteTab({ patientId }: { patientId: string }) {
  const activeRole = useActiveRole()
  const canWrite = canWriteRecords(activeRole)
  // A3: una sola atencion "activa" compartida por toda la pestana -- iniciar una
  // atencion nueva desde cualquier seccion (o la preseleccion automatica de la
  // atencion de hoy) aplica a todas. Crear la atencion exige records.write en el
  // backend, asi que "+ Iniciar atencion nueva" se ofrece con ese mismo permiso, sin
  // importar el permiso especifico de cada seccion (p.ej. diagnosis.write).
  // Se llama antes del `return` de abajo porque los Hooks de React deben correr
  // siempre en el mismo orden, incluso para un rol sin permiso para ver el expediente
  // -- `enabled` evita de todos modos la peticion (y el 403 de auditoria) para ese rol.
  const canRead = canReadRecords(activeRole)
  const encounterPicker = useEncounterPicker(patientId, canWrite, canRead)
  const [historyTab, setHistoryTab] = useState<HistoryTab>('general')

  // Fase A (rediseno del expediente, docs/clinica): autollenado real -- los datos
  // generales de la Historia Clinica General se leen de Patient (misma query-key
  // que ResumenTab.tsx, comparten cache) en vez de volver a capturarlos.
  const patientQuery = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => patientsApi.getPatient(patientId),
    enabled: canRead,
  })

  if (!canRead) {
    return <p>No tienes permiso para ver el expediente clinico.</p>
  }

  return (
    <div className={styles.grid}>
      <p className={styles.complianceNote}>
        Expediente clinico estructurado conforme a la NOM-004-SSA3-2012 (antecedentes,
        alergias, medicamentos, signos vitales, diagnosticos y notas clinicas, cada
        uno con fecha, autor y atencion de origen).
      </p>

      <div className={styles.subTabs}>
        {(Object.keys(HISTORY_TAB_LABELS) as HistoryTab[]).map((tab) => (
          <button
            key={tab}
            type="button"
            className={historyTab === tab ? styles.subTabActive : styles.subTab}
            onClick={() => setHistoryTab(tab)}
          >
            {HISTORY_TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {historyTab === 'general' &&
        (patientQuery.data ? (
          <GeneralHistoryTab
            patientId={patientId}
            patient={patientQuery.data}
            canWrite={canWrite}
            canWriteDiagnosis={canWriteDiagnosis(activeRole)}
            encounterPicker={encounterPicker}
          />
        ) : (
          <p className={styles.fullWidth}>Cargando datos del paciente...</p>
        ))}
      {historyTab === 'odontologica' && (
        <OdontologicalHistoryTab
          patientId={patientId}
          canWrite={canWrite}
          encounterPicker={encounterPicker}
        />
      )}
      {historyTab === 'pediatrica' && (
        <PediatricHistoryTab
          patientId={patientId}
          canWrite={canWrite}
          encounterPicker={encounterPicker}
        />
      )}
      {historyTab === 'endodoncia' && (
        <EndodonticHistoryTab
          patientId={patientId}
          canWrite={canWrite}
          encounterPicker={encounterPicker}
        />
      )}
    </div>
  )
}
