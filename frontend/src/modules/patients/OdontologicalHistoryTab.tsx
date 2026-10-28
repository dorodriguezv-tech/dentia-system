import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { canReadOdontogram, canWriteOdontogram } from '../auth/roles'
import { useActiveRole } from '../auth/store'
import * as catalogsApi from '../catalogs/api'
import type { CatalogItemOut } from '../catalogs/types'
import { EncounterPickerField } from '../encounters/EncounterPicker'
import type { EncounterPicker } from '../encounters/useEncounterPicker'
import * as odontoApi from '../odontologicalHistory/api'
import {
  KENNEDY_CLASS_LABELS,
  ORAL_HEALTH_SELF_PERCEPTION_LABELS,
  PERIODONTAL_ANSWER_LABELS,
  RADIOGRAPHIC_FINDING_LABELS,
  RADIOGRAPHIC_FINDING_TYPES,
  type FixedProsthesisEntry,
  type KennedyClass,
  type OdontogramDiagnosisDetailOut,
  type OdontologicalExamOut,
  type OralHealthSelfPerception,
  type ParallelometerAnalysisOut,
  type ParallelometerEntry,
  type PeriodontalAnamnesisOut,
  type PeriodontalAnswer,
  type RadiographicAnalysisOut,
  type RadiographicFindingDetail,
  type RadiographicFindingType,
  type RemovablePartialDentureDesignOut,
  type ToothDiagnosisEntryOut,
  type ToothTreatmentPlanEntryOut,
} from '../odontologicalHistory/types'
import { Odontograma } from '../odontogram/Odontograma'
import { LOWER_PERMANENT_ROW, UPPER_PERMANENT_ROW } from '../odontogram/toothRules'
import { PeriodontogramSection } from '../periodontogram/PeriodontogramSection'
import * as recordsApi from '../records/api'
import { ADICCIONES_LABELS } from '../records/types'
import { latestActive, saveWithAutoCorrection } from './historyHelpers'
import { AnnulButton, DetailList, EditingBanner, MissingDataBadge } from './historyShared'
import styles from './PatientDetailPage.module.css'

/** Fase C (rediseno del expediente, docs/clinica): Historia Clinica
 * Odontologica -- sigue los mismos patrones ya establecidos en
 * ExpedienteTab.tsx (Fase A) para la Historia Clinica General: secciones
 * <details> cerradas por defecto con badge "Faltan datos", vista "ya
 * guardado" tipo <dl> con todos los campos capturados, "Ninguno" mutuamente
 * excluyente en checklists, fecha de captura visible, y una sola atencion
 * compartida con un solo picker "ancla" (aqui: Odontograma de diagnostico).
 */

// --------------------------------------------------------------------------------
// 1. Exploracion cabeza/cuello + biotipo facial + ATM + tejidos blandos.
// --------------------------------------------------------------------------------

const EXAM_DEFAULTS = {
  skull_type: '',
  facial_biotype: '',
  facial_biotype_observations: '',
  apertura_conservada_mm: '',
  apertura_limitada_mm: '',
  chasquidos_derecho: false,
  crepitacion_derecho: false,
  chasquidos_izquierdo: false,
  crepitacion_izquierdo: false,
  dolor_apertura_lateralidad: false,
  fatiga_dolor_muscular: false,
  desviacion_apertura_cierre: false,
  atm_observaciones: '',
  ganglios: '',
  carrillos: '',
  labios: '',
  lengua: '',
  piso_boca: '',
  region_retromolar: '',
  paladar_duro_blando: '',
  faringe: '',
  encia_libre_marginal: '',
  tejidos_blandos_observaciones: '',
}

const ATM_BOOLEAN_FIELDS: { key: keyof typeof EXAM_DEFAULTS; label: string }[] = [
  { key: 'chasquidos_derecho', label: 'Chasquidos (derecho)' },
  { key: 'crepitacion_derecho', label: 'Crepitación (derecho)' },
  { key: 'chasquidos_izquierdo', label: 'Chasquidos (izquierdo)' },
  { key: 'crepitacion_izquierdo', label: 'Crepitación (izquierdo)' },
  { key: 'dolor_apertura_lateralidad', label: 'Dolor a la apertura/lateralidad' },
  { key: 'fatiga_dolor_muscular', label: 'Fatiga o dolor muscular' },
  { key: 'desviacion_apertura_cierre', label: 'Desviación a la apertura/cierre' },
]

const TEJIDOS_BLANDOS_FIELDS: { key: keyof typeof EXAM_DEFAULTS; label: string }[] = [
  { key: 'ganglios', label: 'Ganglios' },
  { key: 'carrillos', label: 'Carrillos' },
  { key: 'labios', label: 'Labios' },
  { key: 'lengua', label: 'Lengua' },
  { key: 'piso_boca', label: 'Piso de boca' },
  { key: 'region_retromolar', label: 'Región retromolar' },
  { key: 'paladar_duro_blando', label: 'Paladar duro/blando' },
  { key: 'faringe', label: 'Faringe' },
  { key: 'encia_libre_marginal', label: 'Encía libre/marginal' },
]

function OdontologicalExamSection({
  patientId,
  canWrite,
  encounterId,
  skullTypeCatalog,
  facialBiotypeCatalog,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
  skullTypeCatalog: CatalogItemOut[]
  facialBiotypeCatalog: CatalogItemOut[]
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['odonto-history-exam', patientId],
    queryFn: () => odontoApi.listOdontologicalExams(patientId),
  })

  const [form, setForm] = useState(EXAM_DEFAULTS)
  const [noAtmFindings, setNoAtmFindings] = useState(false)

  function update<K extends keyof typeof EXAM_DEFAULTS>(key: K, value: (typeof EXAM_DEFAULTS)[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  function toggleNoAtmFindings(checked: boolean) {
    setNoAtmFindings(checked)
    if (checked) {
      setForm((prev) => {
        const next = { ...prev }
        for (const { key } of ATM_BOOLEAN_FIELDS) {
          ;(next[key] as boolean) = false
        }
        return next
      })
    }
  }

  // Correccion UX (ronda 2.2): entrada activa mas reciente -- se precarga el
  // formulario para "editarla" (anular+recapturar por dentro).
  const current = latestActive(listQuery.data)

  useEffect(() => {
    if (current) {
      setForm({
        skull_type: current.skull_type ?? '',
        facial_biotype: current.facial_biotype ?? '',
        facial_biotype_observations: current.facial_biotype_observations ?? '',
        apertura_conservada_mm:
          current.apertura_conservada_mm != null ? String(current.apertura_conservada_mm) : '',
        apertura_limitada_mm:
          current.apertura_limitada_mm != null ? String(current.apertura_limitada_mm) : '',
        chasquidos_derecho: current.chasquidos_derecho,
        crepitacion_derecho: current.crepitacion_derecho,
        chasquidos_izquierdo: current.chasquidos_izquierdo,
        crepitacion_izquierdo: current.crepitacion_izquierdo,
        dolor_apertura_lateralidad: current.dolor_apertura_lateralidad,
        fatiga_dolor_muscular: current.fatiga_dolor_muscular,
        desviacion_apertura_cierre: current.desviacion_apertura_cierre,
        atm_observaciones: current.atm_observaciones ?? '',
        ganglios: current.ganglios ?? '',
        carrillos: current.carrillos ?? '',
        labios: current.labios ?? '',
        lengua: current.lengua ?? '',
        piso_boca: current.piso_boca ?? '',
        region_retromolar: current.region_retromolar ?? '',
        paladar_duro_blando: current.paladar_duro_blando ?? '',
        faringe: current.faringe ?? '',
        encia_libre_marginal: current.encia_libre_marginal ?? '',
        tejidos_blandos_observaciones: current.tejidos_blandos_observaciones ?? '',
      })
      setNoAtmFindings(false)
    } else {
      setForm(EXAM_DEFAULTS)
      setNoAtmFindings(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => odontoApi.annulOdontologicalExam(patientId, itemId, reason),
        () =>
          odontoApi.createOdontologicalExam(patientId, {
            encounter_id: encounterId,
            skull_type: form.skull_type || null,
            facial_biotype: form.facial_biotype || null,
            facial_biotype_observations: form.facial_biotype_observations || null,
            apertura_conservada_mm: form.apertura_conservada_mm ? Number(form.apertura_conservada_mm) : null,
            apertura_limitada_mm: form.apertura_limitada_mm ? Number(form.apertura_limitada_mm) : null,
            chasquidos_derecho: form.chasquidos_derecho,
            crepitacion_derecho: form.crepitacion_derecho,
            chasquidos_izquierdo: form.chasquidos_izquierdo,
            crepitacion_izquierdo: form.crepitacion_izquierdo,
            dolor_apertura_lateralidad: form.dolor_apertura_lateralidad,
            fatiga_dolor_muscular: form.fatiga_dolor_muscular,
            desviacion_apertura_cierre: form.desviacion_apertura_cierre,
            atm_observaciones: form.atm_observaciones || null,
            ganglios: form.ganglios || null,
            carrillos: form.carrillos || null,
            labios: form.labios || null,
            lengua: form.lengua || null,
            piso_boca: form.piso_boca || null,
            region_retromolar: form.region_retromolar || null,
            paladar_duro_blando: form.paladar_duro_blando || null,
            faringe: form.faringe || null,
            encia_libre_marginal: form.encia_libre_marginal || null,
            tejidos_blandos_observaciones: form.tejidos_blandos_observaciones || null,
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['odonto-history-exam', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      odontoApi.annulOdontologicalExam(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['odonto-history-exam', patientId] })
    },
  })

  function catalogLabel(catalog: CatalogItemOut[], code: string | null): string | null {
    if (!code) return null
    return catalog.find((c) => c.code === code)?.name ?? code
  }

  function detailRows(item: OdontologicalExamOut): [string, string][] {
    const rows: [string, string][] = []
    const skull = catalogLabel(skullTypeCatalog, item.skull_type)
    if (skull) rows.push(['Tipo de cráneo', skull])
    const biotype = catalogLabel(facialBiotypeCatalog, item.facial_biotype)
    if (biotype) rows.push(['Biotipo facial', biotype])
    if (item.facial_biotype_observations) {
      rows.push(['Observaciones del biotipo facial', item.facial_biotype_observations])
    }
    if (item.apertura_conservada_mm != null) {
      rows.push(['Apertura conservada (mm)', String(item.apertura_conservada_mm)])
    }
    if (item.apertura_limitada_mm != null) {
      rows.push(['Apertura limitada (mm)', String(item.apertura_limitada_mm)])
    }
    for (const { key, label } of ATM_BOOLEAN_FIELDS) {
      if (item[key as keyof OdontologicalExamOut]) rows.push([label, 'Sí'])
    }
    if (item.atm_observaciones) rows.push(['Observaciones de ATM', item.atm_observaciones])
    for (const { key, label } of TEJIDOS_BLANDOS_FIELDS) {
      const value = item[key as keyof OdontologicalExamOut] as string | null
      if (value) rows.push([label, value])
    }
    if (item.tejidos_blandos_observaciones) {
      rows.push(['Observaciones de tejidos blandos', item.tejidos_blandos_observaciones])
    }
    return rows
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Exploración cabeza y cuello, ATM y tejidos blandos
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
      {listQuery.data?.length === 0 && <p>Sin exploración registrada.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <p className={styles.fieldsetLabel}>Cabeza y biotipo facial</p>
          <select
            aria-label="Tipo de cráneo"
            value={form.skull_type}
            onChange={(e) => update('skull_type', e.target.value)}
          >
            <option value="">Tipo de cráneo: sin especificar</option>
            {skullTypeCatalog.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </select>
          <select
            aria-label="Biotipo facial"
            value={form.facial_biotype}
            onChange={(e) => update('facial_biotype', e.target.value)}
          >
            <option value="">Biotipo facial: sin especificar</option>
            {facialBiotypeCatalog.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Observaciones del biotipo facial (opcional)"
            value={form.facial_biotype_observations}
            onChange={(e) => update('facial_biotype_observations', e.target.value)}
          />

          <p className={styles.fieldsetLabel}>ATM</p>
          <label className={styles.fieldRow}>
            <span>Apertura conservada (mm)</span>
            <input
              type="number"
              step="0.1"
              min="0"
              max="100"
              aria-label="Apertura conservada (mm)"
              value={form.apertura_conservada_mm}
              onChange={(e) => update('apertura_conservada_mm', e.target.value)}
            />
          </label>
          <label className={styles.fieldRow}>
            <span>Apertura limitada (mm)</span>
            <input
              type="number"
              step="0.1"
              min="0"
              max="100"
              aria-label="Apertura limitada (mm)"
              value={form.apertura_limitada_mm}
              onChange={(e) => update('apertura_limitada_mm', e.target.value)}
            />
          </label>
          <div className={styles.checkboxGrid}>
            <label className={styles.checkboxItem}>
              <input
                type="checkbox"
                checked={noAtmFindings}
                onChange={(e) => toggleNoAtmFindings(e.target.checked)}
              />
              Ninguno
            </label>
            {ATM_BOOLEAN_FIELDS.map(({ key, label }) => (
              <label key={key} className={styles.checkboxItem}>
                <input
                  type="checkbox"
                  checked={form[key] as boolean}
                  onChange={(e) => {
                    update(key, e.target.checked as (typeof form)[typeof key])
                    if (e.target.checked) setNoAtmFindings(false)
                  }}
                />
                {label}
              </label>
            ))}
          </div>
          <input
            type="text"
            placeholder="Observaciones de ATM (opcional)"
            value={form.atm_observaciones}
            onChange={(e) => update('atm_observaciones', e.target.value)}
          />

          <p className={styles.fieldsetLabel}>Tejidos blandos</p>
          {TEJIDOS_BLANDOS_FIELDS.map(({ key, label }) => (
            <input
              key={key}
              type="text"
              placeholder={label}
              value={form[key] as string}
              onChange={(e) => update(key, e.target.value as (typeof form)[typeof key])}
            />
          ))}
          <input
            type="text"
            placeholder="Observaciones de tejidos blandos (opcional)"
            value={form.tejidos_blandos_observaciones}
            onChange={(e) => update('tejidos_blandos_observaciones', e.target.value)}
          />

          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar exploración'}
          </button>
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 2. Anamnesis periodontal.
// --------------------------------------------------------------------------------

const PERIODONTAL_DEFAULTS = {
  cepillado_veces_dia: '',
  cepillado_pasta: '',
  insatisfaccion_motivo: '',
  tratamiento_medico_detalle: '',
  medicamento_actual: '',
  cirugia_detalle: '',
  hormonas_para_que: '',
  habito_danino_cual: '',
  fuma_cigarros_dia: '',
  alcohol_veces_semana: '',
  ultimo_examen_odontologico: '',
  salud_bucal_autopercibida: '' as OralHealthSelfPerception | '',
}

function PeriodontalAnamnesisSection({
  patientId,
  canWrite,
  encounterId,
  questionCatalog,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
  questionCatalog: CatalogItemOut[]
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['odonto-history-periodontal-anamnesis', patientId],
    queryFn: () => odontoApi.listPeriodontalAnamneses(patientId),
  })
  // Autollenado (no recapturar): mismas query-keys que ExpedienteTab.tsx para
  // compartir la cache de TanStack Query en vez de duplicar peticiones.
  const allergiesQuery = useQuery({
    queryKey: ['patient-allergies', patientId],
    queryFn: () => recordsApi.listAllergies(patientId),
  })
  const medicationsQuery = useQuery({
    queryKey: ['patient-medications', patientId],
    queryFn: () => recordsApi.listMedications(patientId),
  })
  const nonPathologicalQuery = useQuery({
    queryKey: ['general-history-non-pathological', patientId],
    queryFn: () => recordsApi.listNonPathologicalHistory(patientId),
  })

  const [answers, setAnswers] = useState<Record<string, PeriodontalAnswer>>({})
  const [form, setForm] = useState(PERIODONTAL_DEFAULTS)

  function update<K extends keyof typeof PERIODONTAL_DEFAULTS>(
    key: K,
    value: (typeof PERIODONTAL_DEFAULTS)[K],
  ) {
    setForm((prev) => ({ ...prev, [key]: value }))
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
      setAnswers(current.answers as Record<string, PeriodontalAnswer>)
      setForm({
        cepillado_veces_dia:
          current.cepillado_veces_dia != null ? String(current.cepillado_veces_dia) : '',
        cepillado_pasta: current.cepillado_pasta ?? '',
        insatisfaccion_motivo: current.insatisfaccion_motivo ?? '',
        tratamiento_medico_detalle: current.tratamiento_medico_detalle ?? '',
        medicamento_actual: current.medicamento_actual ?? '',
        cirugia_detalle: current.cirugia_detalle ?? '',
        hormonas_para_que: current.hormonas_para_que ?? '',
        habito_danino_cual: current.habito_danino_cual ?? '',
        fuma_cigarros_dia: current.fuma_cigarros_dia != null ? String(current.fuma_cigarros_dia) : '',
        alcohol_veces_semana:
          current.alcohol_veces_semana != null ? String(current.alcohol_veces_semana) : '',
        ultimo_examen_odontologico: current.ultimo_examen_odontologico ?? '',
        salud_bucal_autopercibida: current.salud_bucal_autopercibida ?? '',
      })
    } else {
      setAnswers({})
      setForm(PERIODONTAL_DEFAULTS)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => odontoApi.annulPeriodontalAnamnesis(patientId, itemId, reason),
        () =>
          odontoApi.createPeriodontalAnamnesis(patientId, {
            encounter_id: encounterId,
            answers,
            cepillado_veces_dia: form.cepillado_veces_dia
              ? Math.round(Number(form.cepillado_veces_dia))
              : null,
            cepillado_pasta: form.cepillado_pasta || null,
            insatisfaccion_motivo: form.insatisfaccion_motivo || null,
            tratamiento_medico_detalle: form.tratamiento_medico_detalle || null,
            medicamento_actual: form.medicamento_actual || null,
            cirugia_detalle: form.cirugia_detalle || null,
            hormonas_para_que: form.hormonas_para_que || null,
            habito_danino_cual: form.habito_danino_cual || null,
            fuma_cigarros_dia: form.fuma_cigarros_dia ? Math.round(Number(form.fuma_cigarros_dia)) : null,
            alcohol_veces_semana: form.alcohol_veces_semana
              ? Math.round(Number(form.alcohol_veces_semana))
              : null,
            ultimo_examen_odontologico: form.ultimo_examen_odontologico || null,
            salud_bucal_autopercibida: form.salud_bucal_autopercibida || null,
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['odonto-history-periodontal-anamnesis', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      odontoApi.annulPeriodontalAnamnesis(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['odonto-history-periodontal-anamnesis', patientId] })
    },
  })

  function questionLabel(code: string): string {
    return questionCatalog.find((q) => q.code === code)?.name ?? code
  }

  function detailRows(item: PeriodontalAnamnesisOut): [string, string][] {
    const rows: [string, string][] = []
    for (const [code, answer] of Object.entries(item.answers)) {
      const label = PERIODONTAL_ANSWER_LABELS[answer as PeriodontalAnswer] ?? answer
      rows.push([questionLabel(code), label])
    }
    if (item.cepillado_veces_dia != null) rows.push(['Cepillados al día', String(item.cepillado_veces_dia)])
    if (item.cepillado_pasta) rows.push(['Pasta dental', item.cepillado_pasta])
    if (item.insatisfaccion_motivo) rows.push(['Motivo de insatisfacción', item.insatisfaccion_motivo])
    if (item.tratamiento_medico_detalle) {
      rows.push(['Detalle del tratamiento médico', item.tratamiento_medico_detalle])
    }
    if (item.medicamento_actual) rows.push(['Medicamento actual', item.medicamento_actual])
    if (item.cirugia_detalle) rows.push(['Detalle de cirugía', item.cirugia_detalle])
    if (item.hormonas_para_que) rows.push(['Hormonas: ¿para qué?', item.hormonas_para_que])
    if (item.habito_danino_cual) rows.push(['Hábito dañino: ¿cuál?', item.habito_danino_cual])
    if (item.fuma_cigarros_dia != null) rows.push(['Cigarros al día', String(item.fuma_cigarros_dia)])
    if (item.alcohol_veces_semana != null) {
      rows.push(['Alcohol (veces/semana)', String(item.alcohol_veces_semana)])
    }
    if (item.ultimo_examen_odontologico) {
      rows.push(['Último examen odontológico', item.ultimo_examen_odontologico])
    }
    if (item.salud_bucal_autopercibida) {
      rows.push([
        'Salud bucal autopercibida',
        ORAL_HEALTH_SELF_PERCEPTION_LABELS[item.salud_bucal_autopercibida],
      ])
    }
    return rows
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  const latestNonPathological = [...(nonPathologicalQuery.data ?? [])]
    .filter((item) => item.is_active)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0]
  const tabaco = latestNonPathological?.adicciones.tabaco
  const alcohol = latestNonPathological?.adicciones.alcohol
  const activeAllergies = allergiesQuery.data?.filter((a) => a.is_active) ?? []
  const activeMedications = medicationsQuery.data?.filter((m) => m.is_active) ?? []

  function contextNote(code: string): string | null {
    if (code === 'fuma') {
      return tabaco
        ? `Ya capturado en Historia Clínica General: Tabaco ${tabaco.has ? 'Sí' : 'No'}${tabaco.detail ? ` (${tabaco.detail})` : ''}.`
        : null
    }
    if (code === 'consume_alcohol') {
      return alcohol
        ? `Ya capturado en Historia Clínica General: Alcohol ${alcohol.has ? 'Sí' : 'No'}${alcohol.detail ? ` (${alcohol.detail})` : ''}.`
        : null
    }
    if (code === 'alergico_medicamento') {
      return activeAllergies.length > 0
        ? `Alergias ya capturadas en Historia Clínica General: ${activeAllergies.map((a) => a.substance).join(', ')}.`
        : null
    }
    if (code === 'tratamiento_medico_actual') {
      return activeMedications.length > 0
        ? `Medicamentos activos ya capturados en Historia Clínica General: ${activeMedications.map((m) => m.name).join(', ')}.`
        : null
    }
    return null
  }

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Anamnesis periodontal
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
      {listQuery.data?.length === 0 && <p>Sin anamnesis periodontal registrada.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}

      <div>
        <p className={styles.fieldsetLabel}>Datos ya capturados en la Historia Clínica General</p>
        <dl>
          <div className={styles.infoRow}>
            <dt>{ADICCIONES_LABELS.tabaco}</dt>
            <dd>
              {tabaco ? `${tabaco.has ? 'Sí' : 'No'}${tabaco.detail ? ` (${tabaco.detail})` : ''}` : 'Sin registrar'}
            </dd>
          </div>
          <div className={styles.infoRow}>
            <dt>{ADICCIONES_LABELS.alcohol}</dt>
            <dd>
              {alcohol
                ? `${alcohol.has ? 'Sí' : 'No'}${alcohol.detail ? ` (${alcohol.detail})` : ''}`
                : 'Sin registrar'}
            </dd>
          </div>
          <div className={styles.infoRow}>
            <dt>Alergias activas</dt>
            <dd>
              {activeAllergies.length > 0
                ? activeAllergies.map((a) => a.substance).join(', ')
                : 'Ninguna registrada'}
            </dd>
          </div>
          <div className={styles.infoRow}>
            <dt>Medicamentos activos</dt>
            <dd>
              {activeMedications.length > 0
                ? activeMedications.map((m) => m.name).join(', ')
                : 'Ninguno registrado'}
            </dd>
          </div>
        </dl>
        <p className={styles.complianceNote}>
          Ya capturado en Historia Clínica General, revisa esa sección para editarlo.
        </p>
      </div>

      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          {questionCatalog.map((question) => {
            const note = contextNote(question.code)
            return (
              <div key={question.code}>
                <p className={styles.fieldsetLabel}>{question.name}</p>
                {note && <p className={styles.complianceNote}>{note}</p>}
                <div className={styles.checkboxGrid}>
                  {(['si', 'no', 'no_recuerda'] as PeriodontalAnswer[]).map((value) => (
                    <label key={value} className={styles.checkboxItem}>
                      <input
                        type="radio"
                        name={`periodontal-${question.code}`}
                        checked={answers[question.code] === value}
                        onChange={() => setAnswers((prev) => ({ ...prev, [question.code]: value }))}
                      />
                      {PERIODONTAL_ANSWER_LABELS[value]}
                    </label>
                  ))}
                </div>
              </div>
            )
          })}

          <p className={styles.fieldsetLabel}>Datos adicionales de higiene y salud bucal</p>
          <input
            type="number"
            step="1"
            min="0"
            max="20"
            placeholder="Cepillados al día"
            value={form.cepillado_veces_dia}
            onChange={(e) => update('cepillado_veces_dia', e.target.value)}
          />
          <input
            type="text"
            placeholder="Pasta dental utilizada"
            value={form.cepillado_pasta}
            onChange={(e) => update('cepillado_pasta', e.target.value)}
          />
          <input
            type="text"
            placeholder="Motivo de insatisfacción con la apariencia (opcional)"
            value={form.insatisfaccion_motivo}
            onChange={(e) => update('insatisfaccion_motivo', e.target.value)}
          />
          <input
            type="text"
            placeholder="Detalle del tratamiento médico actual (opcional)"
            value={form.tratamiento_medico_detalle}
            onChange={(e) => update('tratamiento_medico_detalle', e.target.value)}
          />
          <input
            type="text"
            placeholder="Medicamento actual (opcional)"
            value={form.medicamento_actual}
            onChange={(e) => update('medicamento_actual', e.target.value)}
          />
          <input
            type="text"
            placeholder="Detalle de cirugía previa (opcional)"
            value={form.cirugia_detalle}
            onChange={(e) => update('cirugia_detalle', e.target.value)}
          />
          <input
            type="text"
            placeholder="Hormonas: ¿para qué? (opcional)"
            value={form.hormonas_para_que}
            onChange={(e) => update('hormonas_para_que', e.target.value)}
          />
          <input
            type="text"
            placeholder="¿Cuál otro hábito dañino? (opcional)"
            value={form.habito_danino_cual}
            onChange={(e) => update('habito_danino_cual', e.target.value)}
          />
          <input
            type="number"
            step="1"
            min="0"
            max="200"
            placeholder="Cigarros al día"
            value={form.fuma_cigarros_dia}
            onChange={(e) => update('fuma_cigarros_dia', e.target.value)}
          />
          <input
            type="number"
            step="1"
            min="0"
            max="100"
            placeholder="Alcohol (veces por semana)"
            value={form.alcohol_veces_semana}
            onChange={(e) => update('alcohol_veces_semana', e.target.value)}
          />
          <input
            type="text"
            placeholder="Último examen odontológico (opcional)"
            value={form.ultimo_examen_odontologico}
            onChange={(e) => update('ultimo_examen_odontologico', e.target.value)}
          />
          <select
            aria-label="Salud bucal autopercibida"
            value={form.salud_bucal_autopercibida}
            onChange={(e) =>
              update('salud_bucal_autopercibida', e.target.value as OralHealthSelfPerception | '')
            }
          >
            <option value="">Salud bucal autopercibida: sin especificar</option>
            {Object.entries(ORAL_HEALTH_SELF_PERCEPTION_LABELS).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>

          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar anamnesis periodontal'}
          </button>
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 3. Auxiliares de diagnostico -- analisis radiografico.
// --------------------------------------------------------------------------------

const EMPTY_RADIOGRAPHIC_FINDING: RadiographicFindingDetail = {
  organos_dentarios: '',
  porcentaje: '',
  alteracion: '',
}

function emptyRadiographicFindings(): Record<RadiographicFindingType, RadiographicFindingDetail> {
  const result = {} as Record<RadiographicFindingType, RadiographicFindingDetail>
  for (const type of RADIOGRAPHIC_FINDING_TYPES) {
    result[type] = { ...EMPTY_RADIOGRAPHIC_FINDING }
  }
  return result
}

function RadiographicAnalysisSection({
  patientId,
  canWrite,
  encounterId,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['odonto-history-radiographic', patientId],
    queryFn: () => odontoApi.listRadiographicAnalyses(patientId),
  })

  const [findings, setFindings] =
    useState<Record<RadiographicFindingType, RadiographicFindingDetail>>(emptyRadiographicFindings)
  const [anexosNota, setAnexosNota] = useState('')

  function updateFinding(
    type: RadiographicFindingType,
    field: keyof RadiographicFindingDetail,
    value: string,
  ) {
    setFindings((prev) => ({ ...prev, [type]: { ...prev[type], [field]: value } }))
  }

  // Correccion UX (ronda 2.2): entrada activa mas reciente -- se precarga el
  // formulario para "editarla" (anular+recapturar por dentro).
  const current = latestActive(listQuery.data)

  useEffect(() => {
    if (current) {
      const next = emptyRadiographicFindings()
      for (const type of RADIOGRAPHIC_FINDING_TYPES) {
        const f = current.findings[type]
        if (f) {
          next[type] = {
            organos_dentarios: f.organos_dentarios,
            porcentaje: f.porcentaje ?? '',
            alteracion: f.alteracion ?? '',
          }
        }
      }
      // Correccion UX (ronda 2.2): precarga intencional del formulario al
      // cambiar la entrada activa a editar -- no es sincronizacion con un
      // sistema externo, por eso se suprime la regla.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFindings(next)
      setAnexosNota(current.anexos_nota ?? '')
    } else {
      setFindings(emptyRadiographicFindings())
      setAnexosNota('')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () => {
      const payload: Partial<Record<RadiographicFindingType, RadiographicFindingDetail>> = {}
      for (const type of RADIOGRAPHIC_FINDING_TYPES) {
        const f = findings[type]
        if (f.organos_dentarios.trim()) {
          payload[type] = {
            organos_dentarios: f.organos_dentarios,
            porcentaje: f.porcentaje || null,
            alteracion: f.alteracion || null,
          }
        }
      }
      return saveWithAutoCorrection(
        current,
        (itemId, reason) => odontoApi.annulRadiographicAnalysis(patientId, itemId, reason),
        () =>
          odontoApi.createRadiographicAnalysis(patientId, {
            encounter_id: encounterId,
            findings: payload,
            anexos_nota: anexosNota || null,
          }),
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['odonto-history-radiographic', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      odontoApi.annulRadiographicAnalysis(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['odonto-history-radiographic', patientId] })
    },
  })

  function detailRows(item: RadiographicAnalysisOut): [string, string][] {
    const rows: [string, string][] = []
    for (const type of RADIOGRAPHIC_FINDING_TYPES) {
      const f = item.findings[type]
      if (f) {
        const parts = [f.organos_dentarios]
        if (f.porcentaje) parts.push(f.porcentaje)
        if (f.alteracion) parts.push(f.alteracion)
        rows.push([RADIOGRAPHIC_FINDING_LABELS[type], parts.join(' · ')])
      }
    }
    if (item.anexos_nota) rows.push(['Nota de anexos', item.anexos_nota])
    return rows
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Análisis radiográfico
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
      {listQuery.data?.length === 0 && <p>Sin análisis radiográfico registrado.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          {RADIOGRAPHIC_FINDING_TYPES.map((type) => (
            <div key={type}>
              <p className={styles.fieldsetLabel}>{RADIOGRAPHIC_FINDING_LABELS[type]}</p>
              <input
                type="text"
                placeholder="Órganos dentarios"
                aria-label={`${RADIOGRAPHIC_FINDING_LABELS[type]}: órganos dentarios`}
                value={findings[type].organos_dentarios}
                onChange={(e) => updateFinding(type, 'organos_dentarios', e.target.value)}
              />
              <input
                type="text"
                placeholder="Porcentaje (opcional)"
                aria-label={`${RADIOGRAPHIC_FINDING_LABELS[type]}: porcentaje`}
                value={findings[type].porcentaje ?? ''}
                onChange={(e) => updateFinding(type, 'porcentaje', e.target.value)}
              />
              <input
                type="text"
                placeholder="Alteración (opcional)"
                aria-label={`${RADIOGRAPHIC_FINDING_LABELS[type]}: alteración`}
                value={findings[type].alteracion ?? ''}
                onChange={(e) => updateFinding(type, 'alteracion', e.target.value)}
              />
            </div>
          ))}
          <input
            type="text"
            placeholder="Nota de anexos (fotos/radiografías en el tab Imágenes, opcional)"
            value={anexosNota}
            onChange={(e) => setAnexosNota(e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar análisis radiográfico'}
          </button>
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 4. Odontograma de diagnostico (embebido) + datos complementarios -- seccion
// "ancla": abierta por defecto, sin badge de "Faltan datos", y es la UNICA
// seccion de esta pestana que renderiza el EncounterPickerField (mismo
// criterio que Signos vitales/Diagnosticos en Fase A).
// --------------------------------------------------------------------------------

function OdontogramDiagnosisSection({
  patientId,
  canWrite,
  encounterPicker,
}: {
  patientId: string
  canWrite: boolean
  encounterPicker: EncounterPicker
}) {
  const activeRole = useActiveRole()
  const canReadOdo = canReadOdontogram(activeRole)
  const canWriteOdo = canWriteOdontogram(activeRole)

  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['odonto-history-diagnosis-detail', patientId],
    queryFn: () => odontoApi.listOdontogramDiagnosisDetails(patientId),
  })

  const { encounterId } = encounterPicker
  const [edentulousAvailable, setEdentulousAvailable] = useState<'' | 'si' | 'no'>('')
  const [edentulousComments, setEdentulousComments] = useState('')
  const [kennedySup, setKennedySup] = useState<KennedyClass | ''>('')
  const [kennedySupMod, setKennedySupMod] = useState(false)
  const [kennedyInf, setKennedyInf] = useState<KennedyClass | ''>('')
  const [kennedyInfMod, setKennedyInfMod] = useState(false)
  const [fixedProsthesis, setFixedProsthesis] = useState<FixedProsthesisEntry[]>([])

  function addFixedProsthesisRow() {
    setFixedProsthesis((prev) => [...prev, { tooth_fdi: '', cr_relation: '' }])
  }
  function updateFixedProsthesisRow(index: number, field: keyof FixedProsthesisEntry, value: string) {
    setFixedProsthesis((prev) => prev.map((row, i) => (i === index ? { ...row, [field]: value } : row)))
  }
  function removeFixedProsthesisRow(index: number) {
    setFixedProsthesis((prev) => prev.filter((_, i) => i !== index))
  }

  // Correccion UX (ronda 2.2): entrada activa mas reciente -- se precarga el
  // formulario para "editarla" (anular+recapturar por dentro). Solo aplica a
  // los datos complementarios (este formulario), no al odontograma en si.
  const current = latestActive(listQuery.data)

  useEffect(() => {
    if (current) {
      // Correccion UX (ronda 2.2): precarga intencional del formulario al
      // cambiar la entrada activa a editar -- no es sincronizacion con un
      // sistema externo, por eso se suprime la regla.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setEdentulousAvailable(
        current.edentulous_space_available === null
          ? ''
          : current.edentulous_space_available
            ? 'si'
            : 'no',
      )
      setEdentulousComments(current.edentulous_space_comments ?? '')
      setKennedySup(current.kennedy_sup_class ?? '')
      setKennedySupMod(current.kennedy_sup_modification)
      setKennedyInf(current.kennedy_inf_class ?? '')
      setKennedyInfMod(current.kennedy_inf_modification)
      setFixedProsthesis(current.fixed_prosthesis_analysis)
    } else {
      setEdentulousAvailable('')
      setEdentulousComments('')
      setKennedySup('')
      setKennedySupMod(false)
      setKennedyInf('')
      setKennedyInfMod(false)
      setFixedProsthesis([])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => odontoApi.annulOdontogramDiagnosisDetail(patientId, itemId, reason),
        () =>
          odontoApi.createOdontogramDiagnosisDetail(patientId, {
            encounter_id: encounterId,
            edentulous_space_available: edentulousAvailable === '' ? null : edentulousAvailable === 'si',
            edentulous_space_comments: edentulousComments || null,
            kennedy_sup_class: kennedySup || null,
            kennedy_sup_modification: kennedySupMod,
            kennedy_inf_class: kennedyInf || null,
            kennedy_inf_modification: kennedyInfMod,
            fixed_prosthesis_analysis: fixedProsthesis.filter(
              (row) => row.tooth_fdi.trim() && row.cr_relation.trim(),
            ),
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['odonto-history-diagnosis-detail', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      odontoApi.annulOdontogramDiagnosisDetail(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['odonto-history-diagnosis-detail', patientId] })
    },
  })

  function detailRows(item: OdontogramDiagnosisDetailOut): [string, string][] {
    const rows: [string, string][] = []
    if (item.edentulous_space_available != null) {
      rows.push([
        '¿Espacio interoclusal para la prótesis?',
        item.edentulous_space_available ? 'Sí' : 'No',
      ])
    }
    if (item.edentulous_space_comments) {
      rows.push(['Comentarios del espacio edéntulo', item.edentulous_space_comments])
    }
    if (item.kennedy_sup_class) {
      rows.push([
        'Kennedy superior',
        `${KENNEDY_CLASS_LABELS[item.kennedy_sup_class]}${item.kennedy_sup_modification ? ' con modificación' : ''}`,
      ])
    }
    if (item.kennedy_inf_class) {
      rows.push([
        'Kennedy inferior',
        `${KENNEDY_CLASS_LABELS[item.kennedy_inf_class]}${item.kennedy_inf_modification ? ' con modificación' : ''}`,
      ])
    }
    if (item.fixed_prosthesis_analysis.length > 0) {
      rows.push([
        'Análisis de prótesis fija',
        item.fixed_prosthesis_analysis.map((r) => `${r.tooth_fdi}: ${r.cr_relation}`).join('; '),
      ])
    }
    return rows
  }

  return (
    // Correccion: esta es la UNICA seccion de la pestana que renderiza el
    // EncounterPickerField -- cerrarla por defecto (ronda 2.1) dejaba sin
    // forma de seleccionar/iniciar una atencion a quien no la abriera
    // primero, deshabilitando en silencio TODO lo demas en Historia
    // Odontologica (incluido el Periodontograma). Se queda abierta, mismo
    // criterio ya aplicado a "Diagnosticos" en Historia General.
    <details className={`${styles.card} ${styles.fullWidth}`} open>
      <summary>Odontograma de diagnóstico</summary>

      {canReadOdo ? (
        <Odontograma patientId={patientId} canWrite={canWriteOdo} />
      ) : (
        <p>No tienes permiso para ver el odontograma.</p>
      )}

      <h3>Datos complementarios del odontograma de diagnóstico</h3>
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
      {listQuery.data?.length === 0 && <p>Sin datos complementarios registrados.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <EncounterPickerField encounterPicker={encounterPicker} />

          <p className={styles.fieldsetLabel}>Espacio edéntulo</p>
          <select
            aria-label="¿Existe espacio interoclusal para la prótesis?"
            value={edentulousAvailable}
            onChange={(e) => setEdentulousAvailable(e.target.value as '' | 'si' | 'no')}
          >
            <option value="">¿Espacio interoclusal para la prótesis?: sin especificar</option>
            <option value="si">Sí</option>
            <option value="no">No</option>
          </select>
          <input
            type="text"
            placeholder="Comentarios del espacio edéntulo (opcional)"
            value={edentulousComments}
            onChange={(e) => setEdentulousComments(e.target.value)}
          />

          <p className={styles.fieldsetLabel}>Clasificación de Kennedy</p>
          <label className={styles.fieldRow}>
            <span>Kennedy superior</span>
            <select
              aria-label="Kennedy superior"
              value={kennedySup}
              onChange={(e) => setKennedySup(e.target.value as KennedyClass | '')}
            >
              <option value="">Sin especificar</option>
              {(['I', 'II', 'III'] as KennedyClass[]).map((c) => (
                <option key={c} value={c}>
                  {KENNEDY_CLASS_LABELS[c]}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.fieldRowCheckbox}>
            <input
              type="checkbox"
              checked={kennedySupMod}
              onChange={(e) => setKennedySupMod(e.target.checked)}
            />
            Kennedy superior con modificación
          </label>
          <label className={styles.fieldRow}>
            <span>Kennedy inferior</span>
            <select
              aria-label="Kennedy inferior"
              value={kennedyInf}
              onChange={(e) => setKennedyInf(e.target.value as KennedyClass | '')}
            >
              <option value="">Sin especificar</option>
              {(['I', 'II', 'III'] as KennedyClass[]).map((c) => (
                <option key={c} value={c}>
                  {KENNEDY_CLASS_LABELS[c]}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.fieldRowCheckbox}>
            <input
              type="checkbox"
              checked={kennedyInfMod}
              onChange={(e) => setKennedyInfMod(e.target.checked)}
            />
            Kennedy inferior con modificación
          </label>

          <p className={styles.fieldsetLabel}>Análisis de prótesis fija</p>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Pieza FDI</th>
                  <th>Relación corona-raíz</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {fixedProsthesis.map((row, index) => (
                  <tr key={index}>
                    <td>
                      <input
                        type="text"
                        aria-label={`Pieza FDI (fila ${index + 1})`}
                        maxLength={2}
                        value={row.tooth_fdi}
                        onChange={(e) => updateFixedProsthesisRow(index, 'tooth_fdi', e.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        type="text"
                        aria-label={`Relación corona-raíz (fila ${index + 1})`}
                        value={row.cr_relation}
                        onChange={(e) => updateFixedProsthesisRow(index, 'cr_relation', e.target.value)}
                      />
                    </td>
                    <td>
                      <button
                        type="button"
                        className={styles.linkButton}
                        onClick={() => removeFixedProsthesisRow(index)}
                      >
                        Quitar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button type="button" className={styles.linkButton} onClick={addFixedProsthesisRow}>
            + Agregar fila
          </button>

          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar datos complementarios'}
          </button>
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 5. Analisis con paralelometro.
// --------------------------------------------------------------------------------

function ParallelometerAnalysisSection({
  patientId,
  canWrite,
  encounterId,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['odonto-history-parallelometer', patientId],
    queryFn: () => odontoApi.listParallelometerAnalyses(patientId),
  })
  const [entries, setEntries] = useState<ParallelometerEntry[]>([])

  function addRow() {
    setEntries((prev) => [...prev, { organo_dental: '', caracteristicas: '', plan_tratamiento: '' }])
  }
  function updateRow(index: number, field: keyof ParallelometerEntry, value: string) {
    setEntries((prev) => prev.map((row, i) => (i === index ? { ...row, [field]: value } : row)))
  }
  function removeRow(index: number) {
    setEntries((prev) => prev.filter((_, i) => i !== index))
  }

  // Correccion UX (ronda 2.2): entrada activa mas reciente -- se precarga el
  // formulario para "editarla" (anular+recapturar por dentro).
  const current = latestActive(listQuery.data)

  useEffect(() => {
    // Correccion UX (ronda 2.2): precarga intencional del formulario al
    // cambiar la entrada activa a editar -- no es sincronizacion con un
    // sistema externo, por eso se suprime la regla.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEntries(current ? current.entries : [])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => odontoApi.annulParallelometerAnalysis(patientId, itemId, reason),
        () =>
          odontoApi.createParallelometerAnalysis(patientId, {
            encounter_id: encounterId,
            entries: entries.filter(
              (e) => e.organo_dental.trim() && e.caracteristicas.trim() && e.plan_tratamiento.trim(),
            ),
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['odonto-history-parallelometer', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      odontoApi.annulParallelometerAnalysis(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['odonto-history-parallelometer', patientId] })
    },
  })

  function detailRows(item: ParallelometerAnalysisOut): [string, string][] {
    return item.entries.map((e, i): [string, string] => [
      `Entrada ${i + 1} — ${e.organo_dental}`,
      `Características: ${e.caracteristicas} · Plan de tratamiento: ${e.plan_tratamiento}`,
    ])
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Análisis con paralelómetro
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
      {listQuery.data?.length === 0 && <p>Sin análisis con paralelómetro registrado.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Órgano dental</th>
                  <th>Características</th>
                  <th>Plan de tratamiento</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {entries.map((row, index) => (
                  <tr key={index}>
                    <td>
                      <input
                        type="text"
                        aria-label={`Órgano dental (fila ${index + 1})`}
                        value={row.organo_dental}
                        onChange={(e) => updateRow(index, 'organo_dental', e.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        type="text"
                        aria-label={`Características (fila ${index + 1})`}
                        value={row.caracteristicas}
                        onChange={(e) => updateRow(index, 'caracteristicas', e.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        type="text"
                        aria-label={`Plan de tratamiento (fila ${index + 1})`}
                        value={row.plan_tratamiento}
                        onChange={(e) => updateRow(index, 'plan_tratamiento', e.target.value)}
                      />
                    </td>
                    <td>
                      <button type="button" className={styles.linkButton} onClick={() => removeRow(index)}>
                        Quitar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button type="button" className={styles.linkButton} onClick={addRow}>
            + Agregar fila
          </button>
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar análisis con paralelómetro'}
          </button>
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 6. Diseno de protesis parcial removible.
// --------------------------------------------------------------------------------

const RPD_DEFAULTS = {
  conector_mayor: '',
  conector_menor: '',
  retenedores_directos: '',
  conectores_indirectos: '',
  base_protesica: '',
  dientes_artificiales: '',
}

const RPD_FIELD_LABELS: { key: keyof typeof RPD_DEFAULTS; label: string }[] = [
  { key: 'conector_mayor', label: 'Conector mayor' },
  { key: 'conector_menor', label: 'Conector menor' },
  { key: 'retenedores_directos', label: 'Retenedores directos' },
  { key: 'conectores_indirectos', label: 'Conectores indirectos' },
  { key: 'base_protesica', label: 'Base protésica' },
  { key: 'dientes_artificiales', label: 'Dientes artificiales' },
]

function RemovablePartialDentureDesignSection({
  patientId,
  canWrite,
  encounterId,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['odonto-history-rpd-design', patientId],
    queryFn: () => odontoApi.listRemovablePartialDentureDesigns(patientId),
  })
  const [form, setForm] = useState(RPD_DEFAULTS)

  function update<K extends keyof typeof RPD_DEFAULTS>(key: K, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }))
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
      setForm({
        conector_mayor: current.conector_mayor ?? '',
        conector_menor: current.conector_menor ?? '',
        retenedores_directos: current.retenedores_directos ?? '',
        conectores_indirectos: current.conectores_indirectos ?? '',
        base_protesica: current.base_protesica ?? '',
        dientes_artificiales: current.dientes_artificiales ?? '',
      })
    } else {
      setForm(RPD_DEFAULTS)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => odontoApi.annulRemovablePartialDentureDesign(patientId, itemId, reason),
        () =>
          odontoApi.createRemovablePartialDentureDesign(patientId, {
            encounter_id: encounterId,
            conector_mayor: form.conector_mayor || null,
            conector_menor: form.conector_menor || null,
            retenedores_directos: form.retenedores_directos || null,
            conectores_indirectos: form.conectores_indirectos || null,
            base_protesica: form.base_protesica || null,
            dientes_artificiales: form.dientes_artificiales || null,
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['odonto-history-rpd-design', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      odontoApi.annulRemovablePartialDentureDesign(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['odonto-history-rpd-design', patientId] })
    },
  })

  function detailRows(item: RemovablePartialDentureDesignOut): [string, string][] {
    const rows: [string, string][] = []
    for (const { key, label } of RPD_FIELD_LABELS) {
      const value = item[key as keyof RemovablePartialDentureDesignOut] as string | null
      if (value) rows.push([label, value])
    }
    return rows
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={styles.card}>
      <summary>
        Diseño de prótesis parcial removible
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
      {listQuery.data?.length === 0 && <p>Sin diseño de prótesis parcial removible registrado.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          {RPD_FIELD_LABELS.map(({ key, label }) => (
            <input
              key={key}
              type="text"
              placeholder={label}
              value={form[key]}
              onChange={(e) => update(key, e.target.value)}
            />
          ))}
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar diseño de PPR'}
          </button>
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 7/8. Diagnostico y plan de tratamiento por organo dental -- grilla de las 32
// piezas FDI permanentes, arcada superior arriba e inferior abajo (igual
// disposicion que el PDF).
// --------------------------------------------------------------------------------

function ToothGridFields({
  values,
  onChange,
  ariaLabelPrefix,
}: {
  values: Record<string, string>
  onChange: (tooth: string, value: string) => void
  ariaLabelPrefix: string
}) {
  return (
    <>
      <p className={styles.fieldsetLabel}>Arcada superior</p>
      <div className={styles.checkboxGrid}>
        {UPPER_PERMANENT_ROW.map((tooth) => (
          <label key={tooth} className={styles.fieldRow}>
            <span>{tooth}</span>
            <input
              type="text"
              aria-label={`${ariaLabelPrefix} pieza ${tooth}`}
              value={values[String(tooth)] ?? ''}
              onChange={(e) => onChange(String(tooth), e.target.value)}
            />
          </label>
        ))}
      </div>
      <p className={styles.fieldsetLabel}>Arcada inferior</p>
      <div className={styles.checkboxGrid}>
        {LOWER_PERMANENT_ROW.map((tooth) => (
          <label key={tooth} className={styles.fieldRow}>
            <span>{tooth}</span>
            <input
              type="text"
              aria-label={`${ariaLabelPrefix} pieza ${tooth}`}
              value={values[String(tooth)] ?? ''}
              onChange={(e) => onChange(String(tooth), e.target.value)}
            />
          </label>
        ))}
      </div>
    </>
  )
}

function ToothDiagnosisSection({
  patientId,
  canWrite,
  encounterId,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['odonto-history-tooth-diagnosis', patientId],
    queryFn: () => odontoApi.listToothDiagnosisEntries(patientId),
  })
  const [diagnoses, setDiagnoses] = useState<Record<string, string>>({})
  const [observaciones, setObservaciones] = useState('')

  const createMutation = useMutation({
    mutationFn: () =>
      odontoApi.createToothDiagnosisEntry(patientId, {
        encounter_id: encounterId,
        diagnoses: Object.fromEntries(Object.entries(diagnoses).filter(([, v]) => v.trim())),
        observaciones: observaciones || null,
      }),
    onSuccess: () => {
      setDiagnoses({})
      setObservaciones('')
      queryClient.invalidateQueries({ queryKey: ['odonto-history-tooth-diagnosis', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      odontoApi.annulToothDiagnosisEntry(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['odonto-history-tooth-diagnosis', patientId] })
    },
  })

  function detailRows(item: ToothDiagnosisEntryOut): [string, string][] {
    const rows: [string, string][] = Object.entries(item.diagnoses)
      .filter(([, v]) => v)
      .map(([tooth, v]): [string, string] => [`Pieza ${tooth}`, v])
    if (item.observaciones) rows.push(['Observaciones', item.observaciones])
    return rows
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Diagnóstico por órgano dental
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
      {listQuery.data?.length === 0 && <p>Sin diagnóstico por órgano dental registrado.</p>}

      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <ToothGridFields
            values={diagnoses}
            onChange={(tooth, value) => setDiagnoses((prev) => ({ ...prev, [tooth]: value }))}
            ariaLabelPrefix="Diagnóstico"
          />
          <input
            type="text"
            placeholder="Observaciones (opcional)"
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            Guardar diagnóstico por órgano dental
          </button>
        </form>
      )}
    </details>
  )
}

function ToothTreatmentPlanSection({
  patientId,
  canWrite,
  encounterId,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['odonto-history-tooth-treatment-plan', patientId],
    queryFn: () => odontoApi.listToothTreatmentPlanEntries(patientId),
  })
  const [plans, setPlans] = useState<Record<string, string>>({})
  const [observaciones, setObservaciones] = useState('')

  const createMutation = useMutation({
    mutationFn: () =>
      odontoApi.createToothTreatmentPlanEntry(patientId, {
        encounter_id: encounterId,
        plans: Object.fromEntries(Object.entries(plans).filter(([, v]) => v.trim())),
        observaciones: observaciones || null,
      }),
    onSuccess: () => {
      setPlans({})
      setObservaciones('')
      queryClient.invalidateQueries({ queryKey: ['odonto-history-tooth-treatment-plan', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      odontoApi.annulToothTreatmentPlanEntry(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['odonto-history-tooth-treatment-plan', patientId] })
    },
  })

  function detailRows(item: ToothTreatmentPlanEntryOut): [string, string][] {
    const rows: [string, string][] = Object.entries(item.plans)
      .filter(([, v]) => v)
      .map(([tooth, v]): [string, string] => [`Pieza ${tooth}`, v])
    if (item.observaciones) rows.push(['Observaciones', item.observaciones])
    return rows
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Plan de tratamiento por órgano dental
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
      {listQuery.data?.length === 0 && <p>Sin plan de tratamiento por órgano dental registrado.</p>}

      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <ToothGridFields
            values={plans}
            onChange={(tooth, value) => setPlans((prev) => ({ ...prev, [tooth]: value }))}
            ariaLabelPrefix="Plan de tratamiento"
          />
          <input
            type="text"
            placeholder="Observaciones (opcional)"
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            Guardar plan de tratamiento por órgano dental
          </button>
        </form>
      )}
    </details>
  )
}

/** PDF: mismo patron que GeneralHistoryPdfButton de ExpedienteTab.tsx (Fase A)
 * -- window.open sincronico antes del await para no perder el gesto del
 * usuario y que el bloqueador de ventanas emergentes no lo descarte. */
function OdontologicalHistoryPdfButton({ patientId }: { patientId: string }) {
  const [error, setError] = useState(false)
  const [generating, setGenerating] = useState(false)

  async function handleClick() {
    setError(false)
    setGenerating(true)
    const newTab = window.open('', '_blank')
    try {
      const url = await odontoApi.getOdontologicalHistoryPdfBlobUrl(patientId)
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

export function OdontologicalHistoryTab({
  patientId,
  canWrite,
  encounterPicker,
}: {
  patientId: string
  canWrite: boolean
  encounterPicker: EncounterPicker
}) {
  const { encounterId } = encounterPicker

  const skullTypeCatalogQuery = useQuery({
    queryKey: ['catalog-items', 'skull_type'],
    queryFn: () => catalogsApi.listCatalogItems('skull_type', false),
  })
  const facialBiotypeCatalogQuery = useQuery({
    queryKey: ['catalog-items', 'facial_biotype'],
    queryFn: () => catalogsApi.listCatalogItems('facial_biotype', false),
  })
  const periodontalQuestionCatalogQuery = useQuery({
    queryKey: ['catalog-items', 'periodontal_anamnesis_question'],
    queryFn: () => catalogsApi.listCatalogItems('periodontal_anamnesis_question', false),
  })

  return (
    <>
      <OdontologicalHistoryPdfButton patientId={patientId} />
      <OdontologicalExamSection
        patientId={patientId}
        canWrite={canWrite}
        encounterId={encounterId}
        skullTypeCatalog={skullTypeCatalogQuery.data ?? []}
        facialBiotypeCatalog={facialBiotypeCatalogQuery.data ?? []}
      />
      <PeriodontalAnamnesisSection
        patientId={patientId}
        canWrite={canWrite}
        encounterId={encounterId}
        questionCatalog={periodontalQuestionCatalogQuery.data ?? []}
      />
      <RadiographicAnalysisSection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
      <OdontogramDiagnosisSection
        patientId={patientId}
        canWrite={canWrite}
        encounterPicker={encounterPicker}
      />
      <PeriodontogramSection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
      <ParallelometerAnalysisSection
        patientId={patientId}
        canWrite={canWrite}
        encounterId={encounterId}
      />
      <RemovablePartialDentureDesignSection
        patientId={patientId}
        canWrite={canWrite}
        encounterId={encounterId}
      />
      <ToothDiagnosisSection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
      <ToothTreatmentPlanSection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
    </>
  )
}
