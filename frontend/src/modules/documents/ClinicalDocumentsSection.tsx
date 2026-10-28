import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as encountersApi from '../encounters/api'
import type { TimelineEntryOut } from '../encounters/types'
import { EncounterPickerField } from '../encounters/EncounterPicker'
import { useEncounterPicker } from '../encounters/useEncounterPicker'
import * as recordsApi from '../records/api'
import * as treatmentApi from '../treatment/api'
import * as api from './api'
import styles from './ConsentsTab.module.css'
import type {
  CounterReferralNoteOut,
  PrescriptionMedicationItem,
  PrescriptionOut,
  ReferralNoteOut,
} from './types'

/** Fase D (docs/clinica, "Documentos imprimibles nuevos"): receta, hoja de
 * referencia/interconsulta, hoja de contrarreferencia, PDF de la nota de
 * evolucion mas reciente y PDF de la ficha de tratamientos realizados. Por
 * peticion expresa del usuario, "por el momento" estos documentos viven como
 * una seccion mas dentro de la pestana ya existente de Consentimientos, en
 * vez de pestanas nuevas separadas. */

function summarizeAllergies(allergies: { substance: string; is_active: boolean }[]): string {
  const active = allergies.filter((a) => a.is_active)
  if (active.length === 0) return 'No'
  return `Si: ${active.map((a) => a.substance).join(', ')}`
}

function latestVitalsLabel(
  vitalSigns: {
    height_m: number | null
    weight_kg: number | null
    body_mass_index: number | null
    temperature: number | null
    bp_systolic: number | null
    bp_diastolic: number | null
  }[],
): string {
  const v = vitalSigns[0]
  if (!v) return 'Sin signos vitales registrados'
  const parts: string[] = []
  if (v.height_m != null) parts.push(`Talla ${v.height_m} m`)
  if (v.weight_kg != null) parts.push(`Peso ${v.weight_kg} kg`)
  if (v.body_mass_index != null) parts.push(`IMC ${v.body_mass_index}`)
  if (v.temperature != null) parts.push(`Temp ${v.temperature} °C`)
  if (v.bp_systolic != null && v.bp_diastolic != null) {
    parts.push(`T.A. ${v.bp_systolic}/${v.bp_diastolic} mmHg`)
  }
  return parts.length ? parts.join(', ') : 'Sin datos capturados'
}

function summarizeActiveMedications(
  medications: { name: string; dose: string | null; frequency: string | null; is_active: boolean }[],
): string {
  const active = medications.filter((m) => m.is_active)
  if (active.length === 0) return ''
  return active
    .map((m) => [m.name, m.dose, m.frequency].filter(Boolean).join(' '))
    .join(', ')
}

function summarizePerformedProcedures(
  items: { performed_at: string; procedure_name: string }[],
): string {
  if (items.length === 0) return ''
  return items
    .slice(0, 5)
    .map((p) => `${new Date(p.performed_at).toLocaleDateString('es-MX')}: ${p.procedure_name}`)
    .join('; ')
}

function useAutofillSummaries(patientId: string) {
  const allergiesQuery = useQuery({
    queryKey: ['allergies', patientId],
    queryFn: () => recordsApi.listAllergies(patientId),
  })
  const vitalSignsQuery = useQuery({
    queryKey: ['vital-signs', patientId],
    queryFn: () => recordsApi.listVitalSigns(patientId),
  })
  const medicationsQuery = useQuery({
    queryKey: ['medications', patientId],
    queryFn: () => recordsApi.listMedications(patientId),
  })
  const performedQuery = useQuery({
    queryKey: ['procedures-performed', patientId],
    queryFn: () => treatmentApi.listPerformed(patientId),
  })

  return {
    allergiesLabel: allergiesQuery.data ? summarizeAllergies(allergiesQuery.data) : 'Cargando...',
    vitalsLabel: vitalSignsQuery.data ? latestVitalsLabel(vitalSignsQuery.data) : 'Cargando...',
    allergiesTextForAutofill: allergiesQuery.data
      ? allergiesQuery.data
          .filter((a) => a.is_active)
          .map((a) => a.substance)
          .join(', ')
      : '',
    medicamentosTextForAutofill: medicationsQuery.data
      ? summarizeActiveMedications(medicationsQuery.data)
      : '',
    tratamientosTextForAutofill: performedQuery.data
      ? summarizePerformedProcedures(performedQuery.data)
      : '',
  }
}

// --------------------------------------------------------------------------- receta

function PrescriptionRow({ item }: { item: PrescriptionOut }) {
  const queryClient = useQueryClient()
  const [reason, setReason] = useState('')
  const [annulling, setAnnulling] = useState(false)

  const annulMutation = useMutation({
    mutationFn: () => api.annulPrescription(item.id, reason),
    onSuccess: () => {
      setAnnulling(false)
      queryClient.invalidateQueries({ queryKey: ['prescriptions', item.patient_id] })
    },
  })

  async function openPdf() {
    const tab = window.open('', '_blank')
    const url = await api.getPrescriptionPdfBlobUrl(item.id)
    if (tab) tab.location.href = url
  }

  return (
    <div className={styles.contactItem}>
      <span>
        Folio {item.folio} — {new Date(item.created_at).toLocaleDateString('es-MX')}
        {!item.is_active && ` — Anulada: ${item.annul_reason}`}
      </span>
      <span className={styles.rowActions}>
        <button className={styles.linkButton} type="button" onClick={openPdf}>
          Ver PDF
        </button>
        {item.is_active && !annulling && (
          <button className={styles.linkButton} type="button" onClick={() => setAnnulling(true)}>
            Anular
          </button>
        )}
        {annulling && (
          <>
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
              onClick={() => annulMutation.mutate()}
            >
              Confirmar
            </button>
          </>
        )}
      </span>
    </div>
  )
}

function PrescriptionSection({
  patientId,
  encounterId,
  allergiesLabel,
  vitalsLabel,
}: {
  patientId: string
  encounterId: string
  allergiesLabel: string
  vitalsLabel: string
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['prescriptions', patientId],
    queryFn: () => api.listPrescriptions(patientId),
  })
  const [diagnostico, setDiagnostico] = useState('')
  const [medications, setMedications] = useState<PrescriptionMedicationItem[]>([
    { nombre: '', detalle: '' },
  ])
  const pendingTabRef = useRef<Window | null>(null)

  const createMutation = useMutation({
    mutationFn: () =>
      api.createPrescription(patientId, {
        encounter_id: encounterId,
        diagnostico,
        medications: medications.filter((m) => m.nombre.trim() && m.detalle.trim()),
      }),
    onSuccess: async (item) => {
      setDiagnostico('')
      setMedications([{ nombre: '', detalle: '' }])
      queryClient.invalidateQueries({ queryKey: ['prescriptions', patientId] })
      const url = await api.getPrescriptionPdfBlobUrl(item.id)
      if (pendingTabRef.current) pendingTabRef.current.location.href = url
      pendingTabRef.current = null
    },
    onError: () => {
      pendingTabRef.current?.close()
      pendingTabRef.current = null
    },
  })

  function updateMedication(index: number, field: 'nombre' | 'detalle', value: string) {
    setMedications((meds) => meds.map((m, i) => (i === index ? { ...m, [field]: value } : m)))
  }
  function addMedicationRow() {
    setMedications((meds) => [...meds, { nombre: '', detalle: '' }])
  }
  function removeMedicationRow(index: number) {
    setMedications((meds) => meds.filter((_, i) => i !== index))
  }

  const validMedicationCount = medications.filter((m) => m.nombre.trim() && m.detalle.trim()).length

  return (
    <details className={styles.card}>
      <summary>Receta{listQuery.data?.length ? ` (${listQuery.data.length})` : ''}</summary>
      {listQuery.data?.map((item) => <PrescriptionRow key={item.id} item={item} />)}
      {!listQuery.data?.length && <p>Sin recetas generadas.</p>}

      <form
        className={styles.form}
        onSubmit={(e) => {
          e.preventDefault()
          pendingTabRef.current = window.open('', '_blank')
          createMutation.mutate()
        }}
      >
        <p className={styles.readOnlyBox}>
          Alergias: {allergiesLabel}
          <br />
          Signos vitales: {vitalsLabel}
        </p>
        <textarea
          placeholder="Diagnostico"
          required
          value={diagnostico}
          onChange={(e) => setDiagnostico(e.target.value)}
        />
        <p className={styles.sectionTitle}>Medicamentos</p>
        {medications.map((m, i) => (
          <div key={i} className={styles.medicationRow}>
            <input
              type="text"
              placeholder="Medicamento"
              value={m.nombre}
              onChange={(e) => updateMedication(i, 'nombre', e.target.value)}
            />
            <textarea
              placeholder="Forma farmaceutica, dosis, frecuencia, via, duracion e indicaciones"
              value={m.detalle}
              onChange={(e) => updateMedication(i, 'detalle', e.target.value)}
            />
            {medications.length > 1 && (
              <button
                className={styles.linkButton}
                type="button"
                onClick={() => removeMedicationRow(i)}
              >
                Quitar
              </button>
            )}
          </div>
        ))}
        <button className={styles.secondaryButton} type="button" onClick={addMedicationRow}>
          Agregar medicamento
        </button>
        <button
          className={styles.primaryButton}
          type="submit"
          disabled={
            !encounterId || !diagnostico.trim() || validMedicationCount === 0 || createMutation.isPending
          }
          title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
        >
          Imprimir / Generar PDF
        </button>
        {createMutation.isError && (
          <p className={styles.errorBox}>No se pudo generar la receta. Intenta de nuevo.</p>
        )}
      </form>
    </details>
  )
}

// --------------------------------------------------------------------------- referencia

function ReferralNoteRow({ item }: { item: ReferralNoteOut }) {
  const queryClient = useQueryClient()
  const [reason, setReason] = useState('')
  const [annulling, setAnnulling] = useState(false)

  const annulMutation = useMutation({
    mutationFn: () => api.annulReferralNote(item.id, reason),
    onSuccess: () => {
      setAnnulling(false)
      queryClient.invalidateQueries({ queryKey: ['referral-notes', item.patient_id] })
    },
  })

  async function openPdf() {
    const tab = window.open('', '_blank')
    const url = await api.getReferralNotePdfBlobUrl(item.id)
    if (tab) tab.location.href = url
  }

  return (
    <div className={styles.contactItem}>
      <span>
        {new Date(item.created_at).toLocaleDateString('es-MX')} — {item.establecimiento_receptor}
        {!item.is_active && ` — Anulada: ${item.annul_reason}`}
      </span>
      <span className={styles.rowActions}>
        <button className={styles.linkButton} type="button" onClick={openPdf}>
          Ver PDF
        </button>
        {item.is_active && !annulling && (
          <button className={styles.linkButton} type="button" onClick={() => setAnnulling(true)}>
            Anular
          </button>
        )}
        {annulling && (
          <>
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
              onClick={() => annulMutation.mutate()}
            >
              Confirmar
            </button>
          </>
        )}
      </span>
    </div>
  )
}

function ReferralNoteSection({
  patientId,
  encounterId,
  allergiesTextForAutofill,
  medicamentosTextForAutofill,
  tratamientosTextForAutofill,
}: {
  patientId: string
  encounterId: string
  allergiesTextForAutofill: string
  medicamentosTextForAutofill: string
  tratamientosTextForAutofill: string
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['referral-notes', patientId],
    queryFn: () => api.listReferralNotes(patientId),
  })
  const [diagnosticos, setDiagnosticos] = useState('')
  const [medicamentosTexto, setMedicamentosTexto] = useState('')
  const [alergiasTexto, setAlergiasTexto] = useState('')
  const [tratamientosTexto, setTratamientosTexto] = useState('')
  const [observaciones, setObservaciones] = useState('')
  const [motivoInterconsulta, setMotivoInterconsulta] = useState('')
  const [establecimientoReceptor, setEstablecimientoReceptor] = useState('')
  const pendingTabRef = useRef<Window | null>(null)

  const createMutation = useMutation({
    mutationFn: () =>
      api.createReferralNote(patientId, {
        encounter_id: encounterId,
        diagnosticos: diagnosticos || null,
        medicamentos_texto: medicamentosTexto || null,
        alergias_texto: alergiasTexto || null,
        tratamientos_texto: tratamientosTexto || null,
        observaciones: observaciones || null,
        motivo_interconsulta: motivoInterconsulta,
        establecimiento_receptor: establecimientoReceptor,
      }),
    onSuccess: async (item) => {
      setDiagnosticos('')
      setMedicamentosTexto('')
      setAlergiasTexto('')
      setTratamientosTexto('')
      setObservaciones('')
      setMotivoInterconsulta('')
      setEstablecimientoReceptor('')
      queryClient.invalidateQueries({ queryKey: ['referral-notes', patientId] })
      const url = await api.getReferralNotePdfBlobUrl(item.id)
      if (pendingTabRef.current) pendingTabRef.current.location.href = url
      pendingTabRef.current = null
    },
    onError: () => {
      pendingTabRef.current?.close()
      pendingTabRef.current = null
    },
  })

  function autofillFromExpediente() {
    setAlergiasTexto(allergiesTextForAutofill || 'Ninguna')
    setMedicamentosTexto(medicamentosTextForAutofill || 'Ninguno')
    setTratamientosTexto(tratamientosTextForAutofill || 'Sin tratamientos recientes registrados')
  }

  return (
    <details className={styles.card}>
      <summary>Referencia / Interconsulta{listQuery.data?.length ? ` (${listQuery.data.length})` : ''}</summary>
      {listQuery.data?.map((item) => <ReferralNoteRow key={item.id} item={item} />)}
      {!listQuery.data?.length && <p>Sin hojas de referencia generadas.</p>}

      <form
        className={styles.form}
        onSubmit={(e) => {
          e.preventDefault()
          pendingTabRef.current = window.open('', '_blank')
          createMutation.mutate()
        }}
      >
        <button className={styles.secondaryButton} type="button" onClick={autofillFromExpediente}>
          Autollenar desde el expediente
        </button>
        <textarea
          placeholder="Diagnostico(s)"
          value={diagnosticos}
          onChange={(e) => setDiagnosticos(e.target.value)}
        />
        <textarea
          placeholder="Medicamentos"
          value={medicamentosTexto}
          onChange={(e) => setMedicamentosTexto(e.target.value)}
        />
        <textarea
          placeholder="Alergias"
          value={alergiasTexto}
          onChange={(e) => setAlergiasTexto(e.target.value)}
        />
        <textarea
          placeholder="Tratamientos odontologicos realizados"
          value={tratamientosTexto}
          onChange={(e) => setTratamientosTexto(e.target.value)}
        />
        <textarea
          placeholder="Observaciones del Cirujano Dentista"
          value={observaciones}
          onChange={(e) => setObservaciones(e.target.value)}
        />
        <textarea
          placeholder="Motivo de interconsulta"
          required
          value={motivoInterconsulta}
          onChange={(e) => setMotivoInterconsulta(e.target.value)}
        />
        <input
          type="text"
          placeholder="Establecimiento receptor"
          required
          value={establecimientoReceptor}
          onChange={(e) => setEstablecimientoReceptor(e.target.value)}
        />
        <button
          className={styles.primaryButton}
          type="submit"
          disabled={
            !encounterId ||
            !motivoInterconsulta.trim() ||
            !establecimientoReceptor.trim() ||
            createMutation.isPending
          }
          title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
        >
          Imprimir / Generar PDF
        </button>
        {createMutation.isError && (
          <p className={styles.errorBox}>No se pudo generar la hoja de referencia. Intenta de nuevo.</p>
        )}
      </form>
    </details>
  )
}

// ------------------------------------------------------------------- contrarreferencia

function CounterReferralNoteRow({ item }: { item: CounterReferralNoteOut }) {
  const queryClient = useQueryClient()
  const [reason, setReason] = useState('')
  const [annulling, setAnnulling] = useState(false)

  const annulMutation = useMutation({
    mutationFn: () => api.annulCounterReferralNote(item.id, reason),
    onSuccess: () => {
      setAnnulling(false)
      queryClient.invalidateQueries({ queryKey: ['counter-referral-notes', item.patient_id] })
    },
  })

  async function openPdf() {
    const tab = window.open('', '_blank')
    const url = await api.getCounterReferralNotePdfBlobUrl(item.id)
    if (tab) tab.location.href = url
  }

  return (
    <div className={styles.contactItem}>
      <span>
        {new Date(item.created_at).toLocaleDateString('es-MX')} — {item.establecimiento_emisor}
        {!item.is_active && ` — Anulada: ${item.annul_reason}`}
      </span>
      <span className={styles.rowActions}>
        <button className={styles.linkButton} type="button" onClick={openPdf}>
          Ver PDF
        </button>
        {item.is_active && !annulling && (
          <button className={styles.linkButton} type="button" onClick={() => setAnnulling(true)}>
            Anular
          </button>
        )}
        {annulling && (
          <>
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
              onClick={() => annulMutation.mutate()}
            >
              Confirmar
            </button>
          </>
        )}
      </span>
    </div>
  )
}

function CounterReferralNoteSection({
  patientId,
  encounterId,
  tratamientosTextForAutofill,
}: {
  patientId: string
  encounterId: string
  tratamientosTextForAutofill: string
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['counter-referral-notes', patientId],
    queryFn: () => api.listCounterReferralNotes(patientId),
  })
  const referralsQuery = useQuery({
    queryKey: ['referral-notes', patientId],
    queryFn: () => api.listReferralNotes(patientId),
  })
  const [referralNoteId, setReferralNoteId] = useState('')
  const [motivoContrarreferencia, setMotivoContrarreferencia] = useState('')
  const [tratamientosTexto, setTratamientosTexto] = useState('')
  const [observaciones, setObservaciones] = useState('')
  const [motivoInterconsultaOriginal, setMotivoInterconsultaOriginal] = useState('')
  const [establecimientoEmisor, setEstablecimientoEmisor] = useState('')
  const pendingTabRef = useRef<Window | null>(null)

  const createMutation = useMutation({
    mutationFn: () =>
      api.createCounterReferralNote(patientId, {
        encounter_id: encounterId,
        referral_note_id: referralNoteId || null,
        motivo_contrarreferencia: motivoContrarreferencia,
        tratamientos_texto: tratamientosTexto || null,
        observaciones: observaciones || null,
        motivo_interconsulta_original: motivoInterconsultaOriginal || null,
        establecimiento_emisor: establecimientoEmisor,
      }),
    onSuccess: async (item) => {
      setReferralNoteId('')
      setMotivoContrarreferencia('')
      setTratamientosTexto('')
      setObservaciones('')
      setMotivoInterconsultaOriginal('')
      setEstablecimientoEmisor('')
      queryClient.invalidateQueries({ queryKey: ['counter-referral-notes', patientId] })
      const url = await api.getCounterReferralNotePdfBlobUrl(item.id)
      if (pendingTabRef.current) pendingTabRef.current.location.href = url
      pendingTabRef.current = null
    },
    onError: () => {
      pendingTabRef.current?.close()
      pendingTabRef.current = null
    },
  })

  function selectReferral(id: string) {
    setReferralNoteId(id)
    const referral = referralsQuery.data?.find((r) => r.id === id)
    if (referral) setMotivoInterconsultaOriginal(referral.motivo_interconsulta)
  }

  function autofillTratamientos() {
    setTratamientosTexto(tratamientosTextForAutofill || 'Sin tratamientos recientes registrados')
  }

  return (
    <details className={styles.card}>
      <summary>
        Contrarreferencia{listQuery.data?.length ? ` (${listQuery.data.length})` : ''}
      </summary>
      {listQuery.data?.map((item) => <CounterReferralNoteRow key={item.id} item={item} />)}
      {!listQuery.data?.length && <p>Sin hojas de contrarreferencia generadas.</p>}

      <form
        className={styles.form}
        onSubmit={(e) => {
          e.preventDefault()
          pendingTabRef.current = window.open('', '_blank')
          createMutation.mutate()
        }}
      >
        <select value={referralNoteId} onChange={(e) => selectReferral(e.target.value)}>
          <option value="">Sin ligar a una referencia previa concreta</option>
          {referralsQuery.data?.map((referral) => (
            <option key={referral.id} value={referral.id}>
              {new Date(referral.created_at).toLocaleDateString('es-MX')} —{' '}
              {referral.establecimiento_receptor}
            </option>
          ))}
        </select>
        <textarea
          placeholder="Motivo de la contrarreferencia"
          required
          value={motivoContrarreferencia}
          onChange={(e) => setMotivoContrarreferencia(e.target.value)}
        />
        <button className={styles.secondaryButton} type="button" onClick={autofillTratamientos}>
          Autollenar tratamientos desde el expediente
        </button>
        <textarea
          placeholder="Tratamientos odontologicos realizados"
          value={tratamientosTexto}
          onChange={(e) => setTratamientosTexto(e.target.value)}
        />
        <textarea
          placeholder="Observaciones del clinico"
          value={observaciones}
          onChange={(e) => setObservaciones(e.target.value)}
        />
        <textarea
          placeholder="Motivo de interconsulta original"
          value={motivoInterconsultaOriginal}
          onChange={(e) => setMotivoInterconsultaOriginal(e.target.value)}
        />
        <input
          type="text"
          placeholder="Establecimiento que emite"
          required
          value={establecimientoEmisor}
          onChange={(e) => setEstablecimientoEmisor(e.target.value)}
        />
        <button
          className={styles.primaryButton}
          type="submit"
          disabled={
            !encounterId ||
            !motivoContrarreferencia.trim() ||
            !establecimientoEmisor.trim() ||
            createMutation.isPending
          }
          title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
        >
          Imprimir / Generar PDF
        </button>
        {createMutation.isError && (
          <p className={styles.errorBox}>
            No se pudo generar la hoja de contrarreferencia. Intenta de nuevo.
          </p>
        )}
      </form>
    </details>
  )
}

// --------------------------------------------------------------------- nota de evolucion

function mostRecentNoteId(entries: TimelineEntryOut[]): string | null {
  for (const entry of entries) {
    if (entry.notes.length > 0) return entry.notes[entry.notes.length - 1].id
  }
  return null
}

function ClinicalNotePdfSection({ patientId }: { patientId: string }) {
  const timelineQuery = useQuery({
    queryKey: ['patient-timeline', patientId],
    queryFn: () => encountersApi.getPatientTimeline(patientId),
  })
  const noteId = timelineQuery.data ? mostRecentNoteId(timelineQuery.data) : null

  async function printNote(id: string) {
    const tab = window.open('', '_blank')
    const url = await encountersApi.getNotePdfBlobUrl(id)
    if (tab) tab.location.href = url
  }

  return (
    <details className={styles.card}>
      <summary>Nota de evolucion</summary>
      {timelineQuery.isLoading && <p>Cargando...</p>}
      {!timelineQuery.isLoading && noteId && (
        <button className={styles.primaryButton} type="button" onClick={() => printNote(noteId)}>
          Imprimir / Generar PDF de la nota mas reciente
        </button>
      )}
      {!timelineQuery.isLoading && !noteId && (
        <p>Este paciente todavia no tiene ninguna nota de evolucion capturada.</p>
      )}
    </details>
  )
}

// --------------------------------------------------------------- ficha de tratamientos

function PerformedProceduresPdfSection({ patientId }: { patientId: string }) {
  async function printPdf() {
    const tab = window.open('', '_blank')
    const url = await api.getPatientTreatmentsPerformedPdfBlobUrl(patientId)
    if (tab) tab.location.href = url
  }

  return (
    <details className={styles.card}>
      <summary>Ficha de tratamientos realizados</summary>
      <button className={styles.primaryButton} type="button" onClick={printPdf}>
        Imprimir / Generar PDF
      </button>
    </details>
  )
}

// --------------------------------------------------------------------------------- root

export function ClinicalDocumentsSection({
  patientId,
  canWrite,
}: {
  patientId: string
  canWrite: boolean
}) {
  const encounterPicker = useEncounterPicker(patientId, canWrite)
  const {
    allergiesLabel,
    vitalsLabel,
    allergiesTextForAutofill,
    medicamentosTextForAutofill,
    tratamientosTextForAutofill,
  } = useAutofillSummaries(patientId)

  return (
    <details className={styles.card} open>
      <summary>Otros formatos clinicos</summary>
      {canWrite && (
        <>
          <p className={styles.hint}>Selecciona o inicia la atencion para estos documentos.</p>
          <EncounterPickerField encounterPicker={encounterPicker} />
        </>
      )}
      {canWrite && (
        <PrescriptionSection
          patientId={patientId}
          encounterId={encounterPicker.encounterId}
          allergiesLabel={allergiesLabel}
          vitalsLabel={vitalsLabel}
        />
      )}
      {canWrite && (
        <ReferralNoteSection
          patientId={patientId}
          encounterId={encounterPicker.encounterId}
          allergiesTextForAutofill={allergiesTextForAutofill}
          medicamentosTextForAutofill={medicamentosTextForAutofill}
          tratamientosTextForAutofill={tratamientosTextForAutofill}
        />
      )}
      {canWrite && (
        <CounterReferralNoteSection
          patientId={patientId}
          encounterId={encounterPicker.encounterId}
          tratamientosTextForAutofill={tratamientosTextForAutofill}
        />
      )}
      <ClinicalNotePdfSection patientId={patientId} />
      <PerformedProceduresPdfSection patientId={patientId} />
    </details>
  )
}
