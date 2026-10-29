import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../auth/store'
import { EncounterPickerField } from '../encounters/EncounterPicker'
import { useEncounterPicker } from '../encounters/useEncounterPicker'
import * as treatmentApi from '../treatment/api'
import { useThemeStore } from '../../theme/store'
import * as api from './api'
import {
  categoryForTemplateCode,
  isPediatricTemplateCode,
  SIGNER_RELATIONSHIP_LABELS,
  TEMPLATE_CATEGORY_LABELS,
  TEMPLATE_CODE_LABELS,
} from './catalog'
import { ClinicalDocumentsSection } from './ClinicalDocumentsSection'
import styles from './ConsentsTab.module.css'
import { SignaturePad } from './SignaturePad'
import type {
  ConsentOut,
  DocumentTemplateOut,
  SignerRelationship,
  TemplateCategory,
  TemplateCode,
} from './types'

// Copia minima, solo para la vista previa, de documents/rules.py::render_template
// (fuente de verdad real: sustitucion literal de {{a.b}}, sin condicionales ni
// expresiones). Se duplica aqui a proposito para previsualizar sin pedirle nada
// al backend -- la plantilla ya la tenemos completa en el navegador.
const PREVIEW_VARIABLE_PATTERN = /\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}/g

function lookupPreviewValue(variables: Record<string, unknown>, path: string): unknown {
  let value: unknown = variables
  for (const part of path.split('.')) {
    if (typeof value !== 'object' || value === null || !(part in value)) return ''
    value = (value as Record<string, unknown>)[part]
  }
  return value
}

function escapePreviewHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function renderTemplatePreview(htmlContent: string, variables: Record<string, unknown>): string {
  return htmlContent.replace(PREVIEW_VARIABLE_PATTERN, (_match, path: string) => {
    const value = lookupPreviewValue(variables, path)
    return value === '' || value === null || value === undefined
      ? ''
      : escapePreviewHtml(String(value))
  })
}

// Las plantillas de consentimiento son contenido legal de la clinica: no se crean
// ni editan desde la ficha de un paciente (eso quedo fuera de este submenu a
// peticion expresa). Aqui solo se consultan y se puede ver como se verian.
function TemplatesSection({
  patientName,
  patientAge,
}: {
  patientName: string
  patientAge: number
}) {
  const templatesQuery = useQuery({ queryKey: ['document-templates'], queryFn: api.listTemplates })
  const [previewId, setPreviewId] = useState<string | null>(null)
  const previewTemplate = templatesQuery.data?.find((t) => t.id === previewId) ?? null
  const categories: TemplateCategory[] = ['consentimiento', 'aviso_privacidad', 'carta']

  return (
    <details className={styles.card}>
      <summary>Plantillas de consentimiento</summary>
      {categories.map((category) => {
        const templatesInCategory = (templatesQuery.data ?? []).filter(
          (t) => categoryForTemplateCode(t.code) === category,
        )
        if (!templatesInCategory.length) return null
        return (
          <div key={category}>
            <p className={styles.sectionTitle}>{TEMPLATE_CATEGORY_LABELS[category]}</p>
            {templatesInCategory.map((template) => (
              <div key={template.id} className={styles.contactItem}>
                <button
                  type="button"
                  className={styles.linkButton}
                  onClick={() => setPreviewId(previewId === template.id ? null : template.id)}
                >
                  {TEMPLATE_CODE_LABELS[template.code]}: {template.name} (version {template.version}
                  )
                </button>
              </div>
            ))}
          </div>
        )
      })}
      {!templatesQuery.data?.length && <p>Sin plantillas configuradas todavia.</p>}

      {previewTemplate && (
        <TemplatePreview
          template={previewTemplate}
          patientName={patientName}
          patientAge={patientAge}
        />
      )}
    </details>
  )
}

function TemplatePreview({
  template,
  patientName,
  patientAge,
}: {
  template: DocumentTemplateOut
  patientName: string
  patientAge: number
}) {
  const user = useAuthStore((s) => s.user)
  const branding = useThemeStore((s) => s.branding)

  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  const fecha =
    `${pad(now.getDate())}/${pad(now.getMonth() + 1)}/${now.getFullYear()} ` +
    `${pad(now.getHours())}:${pad(now.getMinutes())}`

  const previewHtml = renderTemplatePreview(template.html_content, {
    paciente: { nombre: patientName, edad: patientAge },
    clinica: { nombre: branding?.display_name ?? '' },
    profesional: { nombre: user?.full_name ?? '', cedula: user?.professional_license ?? '' },
    fecha,
  })

  return (
    <div className={styles.templatePreview}>
      <p className={styles.templatePreviewHint}>
        Asi se vera para este paciente (si la plantilla se liga a un procedimiento o a un plan de
        tratamiento, esos datos se completan hasta firmar):
      </p>
      {/* Contenido de confianza: la plantilla la escribe quien administra la
          clinica; los datos que se sustituyen (paciente, profesional, clinica) ya
          se muestran en otras pantallas, no vienen de un formulario publico. */}
      <div
        className={styles.templatePreviewContent}
        dangerouslySetInnerHTML={{ __html: previewHtml }}
      />
    </div>
  )
}

async function showConsentPdf(consentId: string, newTab: Window | null) {
  const url = await api.getConsentPdfBlobUrl(consentId)
  if (newTab) newTab.location.href = url
}

// Una sola linea de solo lectura con lo que ya se sabe del paciente (y del
// tutor, si el prefill trae uno) -- "dar la opcion de aceptar que estan bien
// los datos" sin un formulario largo (punto 5 del plan aprobado: simplificar
// el menu de Consentimientos).
function PrefillSummary({ variables }: { variables: Record<string, unknown> | undefined }) {
  if (!variables) return null
  const paciente = variables.paciente as Record<string, unknown> | undefined
  const tutor = variables.tutor as Record<string, unknown> | undefined
  if (!paciente) return null
  const parts = [
    String(paciente.nombre ?? ''),
    paciente.edad != null ? `${paciente.edad} años` : null,
    paciente.expediente ? `Expediente ${paciente.expediente}` : null,
  ].filter(Boolean)
  return (
    <div className={styles.readOnlyBox}>
      <p style={{ margin: 0 }}>Paciente: {parts.join(' · ')}</p>
      {!!tutor?.nombre && (
        <p style={{ margin: '0.2rem 0 0' }}>
          Tutor: {String(tutor.nombre)}
          {tutor.parentesco ? ` (${String(tutor.parentesco)})` : ''}
        </p>
      )}
    </div>
  )
}

// Paso 2 (ver plan aprobado, punto 5): solo aparece una vez elegido el
// formato, pide el prefill y muestra unicamente lo que ese formato
// necesita -- la mayoria no tiene ningun campo extra y va directo a firmar.
function ConsentSignStep({
  patientId,
  encounterId,
  templateCode,
  treatmentPlanId,
}: {
  patientId: string
  encounterId: string
  templateCode: TemplateCode
  treatmentPlanId: string | null
}) {
  const queryClient = useQueryClient()
  const prefillQuery = useQuery({
    queryKey: ['consent-prefill', patientId, templateCode, encounterId],
    queryFn: () => api.getConsentPrefill(patientId, templateCode, encounterId),
  })

  const [confirmed, setConfirmed] = useState(false)
  // Lo que el prefill ya trae (editable: cada campo solo se "pisa" aqui una
  // vez que el usuario lo toca) -- derivado en el render en vez de copiarlo a
  // estado dentro de un efecto, para no duplicar la fuente de verdad del query.
  const [extraOverrides, setExtraOverrides] = useState<Record<string, string>>({})
  const [showWitnesses, setShowWitnesses] = useState(false)
  const [witness1, setWitness1] = useState('')
  const [witness2, setWitness2] = useState('')
  const [signerNameOverride, setSignerNameOverride] = useState<string | null>(null)
  const [signerRelationshipOverride, setSignerRelationshipOverride] =
    useState<SignerRelationship | null>(null)
  const [signature, setSignature] = useState<string | null>(null)
  // A peticion del operador: al crear el PDF, la firma debe borrarse sola (antes
  // quedaba dibujada, lista para firmarse "encima" sin querer en el siguiente
  // consentimiento). Remonta el SignaturePad (canvas en blanco de verdad, no solo
  // el valor exportado) en vez de depender de un metodo imperativo expuesto.
  const [signaturePadKey, setSignaturePadKey] = useState(0)
  const pendingTabRef = useRef<Window | null>(null)

  const extraValues: Record<string, string> = {}
  for (const [key, field] of Object.entries(prefillQuery.data?.extra_fields ?? {})) {
    extraValues[key] = key in extraOverrides ? extraOverrides[key] : (field.value ?? '')
  }
  // Si es un formato pediatrico con tutor registrado, quien firma por defecto
  // es el tutor (siempre editable).
  const tutor = prefillQuery.data?.variables.tutor as { nombre?: string } | undefined
  const defaultSignerIsTutor = !!tutor?.nombre && isPediatricTemplateCode(templateCode)
  const signerName = signerNameOverride ?? (defaultSignerIsTutor ? (tutor?.nombre ?? '') : '')
  const signerRelationship: SignerRelationship =
    signerRelationshipOverride ?? (defaultSignerIsTutor ? 'tutor' : 'paciente')

  const createMutation = useMutation({
    mutationFn: () =>
      api.createConsent(patientId, {
        encounter_id: encounterId,
        template_code: templateCode,
        treatment_plan_id: treatmentPlanId,
        signer_name: signerName,
        signer_relationship: signerRelationship,
        signature_png_base64: signature as string,
        extra_fields: extraValues,
        witness1_name: witness1.trim() || null,
        witness2_name: witness2.trim() || null,
      }),
    onSuccess: (consent) => {
      setConfirmed(false)
      setSignerNameOverride(null)
      setSignature(null)
      setSignaturePadKey((k) => k + 1)
      queryClient.invalidateQueries({ queryKey: ['consents', patientId] })
      // El consentimiento ya queda guardado en el expediente al crearse (no hay un
      // paso de "previsualizar antes de guardar" aparte): se muestra el PDF de una
      // vez para poder revisarlo e imprimirlo sin tener que buscarlo despues en la
      // lista de abajo. La pestana ya se abrio sincronica en el submit (mas abajo)
      // para que el bloqueador de ventanas emergentes no la descarte.
      void showConsentPdf(consent.id, pendingTabRef.current)
      pendingTabRef.current = null
    },
    onError: () => {
      pendingTabRef.current?.close()
      pendingTabRef.current = null
    },
  })

  if (prefillQuery.isLoading) {
    return <p className={styles.hint}>Cargando datos del paciente...</p>
  }

  const extraSpecs = Object.entries(prefillQuery.data?.extra_fields ?? {})
  const missingRequired = extraSpecs.filter(
    ([key, field]) => field.required && !(extraValues[key] ?? '').trim(),
  )

  if (!confirmed) {
    return (
      <div>
        <PrefillSummary variables={prefillQuery.data?.variables} />
        <button type="button" className={styles.secondaryButton} onClick={() => setConfirmed(true)}>
          Datos correctos, continuar
        </button>
      </div>
    )
  }

  return (
    <form
      className={styles.form}
      onSubmit={(e) => {
        e.preventDefault()
        pendingTabRef.current = window.open('', '_blank')
        createMutation.mutate()
      }}
    >
      <PrefillSummary variables={prefillQuery.data?.variables} />
      {extraSpecs.map(([key, field]) => (
        <label key={key}>
          {field.label}
          {field.required && !(extraValues[key] ?? '').trim() && (
            <span className={styles.errorBox} style={{ marginLeft: '0.4rem' }}>
              Falta completar
            </span>
          )}
          {field.multiline ? (
            <textarea
              value={extraValues[key] ?? ''}
              onChange={(e) => setExtraOverrides((v) => ({ ...v, [key]: e.target.value }))}
            />
          ) : (
            <input
              type="text"
              value={extraValues[key] ?? ''}
              onChange={(e) => setExtraOverrides((v) => ({ ...v, [key]: e.target.value }))}
            />
          )}
        </label>
      ))}
      {showWitnesses ? (
        <>
          <input
            type="text"
            placeholder="Nombre del primer testigo (opcional)"
            value={witness1}
            onChange={(e) => setWitness1(e.target.value)}
          />
          <input
            type="text"
            placeholder="Nombre del segundo testigo (opcional)"
            value={witness2}
            onChange={(e) => setWitness2(e.target.value)}
          />
        </>
      ) : (
        <button type="button" className={styles.linkButton} onClick={() => setShowWitnesses(true)}>
          ¿Hay testigos? Agregar nombres
        </button>
      )}
      <input
        type="text"
        placeholder="Nombre de quien firma"
        required
        value={signerName}
        onChange={(e) => setSignerNameOverride(e.target.value)}
      />
      <select
        value={signerRelationship}
        onChange={(e) => setSignerRelationshipOverride(e.target.value as SignerRelationship)}
      >
        {Object.entries(SIGNER_RELATIONSHIP_LABELS).map(([code, label]) => (
          <option key={code} value={code}>
            {label}
          </option>
        ))}
      </select>
      <SignaturePad key={signaturePadKey} onChange={setSignature} />
      <button
        className={styles.primaryButton}
        type="submit"
        disabled={
          missingRequired.length > 0 || !signerName.trim() || !signature || createMutation.isPending
        }
      >
        Firmar y generar PDF
      </button>
      {createMutation.isError && (
        <p className={styles.errorBox}>No se pudo generar el consentimiento. Intenta de nuevo.</p>
      )}
    </form>
  )
}

function NewConsentForm({ patientId }: { patientId: string }) {
  // A3/A4/A5: "Firmar y generar PDF" se quedaba deshabilitado para siempre en un
  // paciente sin atenciones (el mismo selector roto de A3, copiado aqui tambien) --
  // NewConsentForm solo se muestra con canSign (ver ConsentsTab), que exige el mismo
  // permiso que crear una atencion (records.write), asi que iniciar una aqui es valido.
  const encounterPicker = useEncounterPicker(patientId, true)
  const templatesQuery = useQuery({ queryKey: ['document-templates'], queryFn: api.listTemplates })
  const plansQuery = useQuery({
    queryKey: ['treatment-plans', patientId],
    queryFn: () => treatmentApi.listPlans(patientId),
  })

  const [templateCode, setTemplateCode] = useState<TemplateCode | ''>('')
  const [treatmentPlanId, setTreatmentPlanId] = useState('')

  const currentCodes = templatesQuery.data?.map((t) => t.code) ?? []
  const categories: TemplateCategory[] = ['consentimiento', 'aviso_privacidad', 'carta']

  return (
    <div className={styles.form}>
      {/* Paso 1: solo elegir atencion + formato (+ plan, si hay alguno) -- nada
          de campos de firma todavia, para no abrumar con 24 formatos a la vista. */}
      <EncounterPickerField encounterPicker={encounterPicker} />
      <select
        value={templateCode}
        onChange={(e) => setTemplateCode(e.target.value as TemplateCode)}
      >
        <option value="">Selecciona un formato...</option>
        {categories.map((category) => {
          const codesInCategory = currentCodes.filter(
            (c) => categoryForTemplateCode(c) === category,
          )
          if (!codesInCategory.length) return null
          return (
            <optgroup key={category} label={TEMPLATE_CATEGORY_LABELS[category]}>
              {codesInCategory.map((code) => (
                <option key={code} value={code}>
                  {TEMPLATE_CODE_LABELS[code]}
                </option>
              ))}
            </optgroup>
          )
        })}
      </select>
      {!!plansQuery.data?.length && (
        <select value={treatmentPlanId} onChange={(e) => setTreatmentPlanId(e.target.value)}>
          <option value="">Sin plan de tratamiento vinculado</option>
          {plansQuery.data.map((plan) => (
            <option key={plan.id} value={plan.id}>
              {plan.title}
            </option>
          ))}
        </select>
      )}

      {/* Paso 2: aparece solo con atencion + formato ya elegidos. La key fuerza
          a reiniciar todo su estado (firma, campos extra, confirmacion) cada
          vez que cambia el formato o la atencion. */}
      {encounterPicker.encounterId && templateCode ? (
        <ConsentSignStep
          key={`${templateCode}-${encounterPicker.encounterId}`}
          patientId={patientId}
          encounterId={encounterPicker.encounterId}
          templateCode={templateCode}
          treatmentPlanId={treatmentPlanId || null}
        />
      ) : (
        <p className={styles.hint}>
          {!encounterPicker.encounterId
            ? 'Selecciona o inicia una atención para continuar.'
            : 'Elige un formato para continuar.'}
        </p>
      )}
    </div>
  )
}

function ConsentRow({ consent, canWrite }: { consent: ConsentOut; canWrite: boolean }) {
  const queryClient = useQueryClient()
  const [reason, setReason] = useState('')
  const [annulling, setAnnulling] = useState(false)

  const annulMutation = useMutation({
    mutationFn: () => api.annulConsent(consent.id, reason),
    onSuccess: () => {
      setAnnulling(false)
      queryClient.invalidateQueries({ queryKey: ['consents', consent.patient_id] })
    },
  })

  function openPdf() {
    // window.open se llama sincronico, antes del await (dentro de showConsentPdf),
    // para no perder el gesto del usuario y que el bloqueador de ventanas
    // emergentes no lo descarte (mismo patron que el PDF del presupuesto en la Fase 7).
    void showConsentPdf(consent.id, window.open('', '_blank'))
  }

  return (
    <div className={styles.contactItem}>
      <span>
        {consent.signer_name} ({SIGNER_RELATIONSHIP_LABELS[consent.signer_relationship]}) —{' '}
        {new Date(consent.signed_at).toLocaleString('es-MX')}
        {!consent.is_active && ` — Anulado: ${consent.annul_reason}`}
      </span>
      <span className={styles.rowActions}>
        <button className={styles.linkButton} type="button" onClick={openPdf}>
          Ver PDF
        </button>
        {canWrite && consent.is_active && !annulling && (
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

export function ConsentsTab({
  patientId,
  patientName,
  patientAge,
  canWrite,
  canSign,
}: {
  patientId: string
  patientName: string
  patientAge: number
  canWrite: boolean
  canSign: boolean
}) {
  const consentsQuery = useQuery({
    queryKey: ['consents', patientId],
    queryFn: () => api.listConsents(patientId),
  })

  return (
    <div className={styles.grid}>
      <TemplatesSection patientName={patientName} patientAge={patientAge} />
      <details className={styles.card} open>
        <summary>Consentimientos firmados</summary>
        {consentsQuery.data?.map((consent) => (
          <ConsentRow key={consent.id} consent={consent} canWrite={canWrite} />
        ))}
        {!consentsQuery.data?.length && <p>Sin consentimientos firmados.</p>}
        {canSign && <NewConsentForm patientId={patientId} />}
      </details>
      <ClinicalDocumentsSection patientId={patientId} canWrite={canWrite} />
    </div>
  )
}
