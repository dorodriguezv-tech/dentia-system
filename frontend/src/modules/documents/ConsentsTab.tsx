import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiRequestBlobUrl, resolveApiAssetUrl } from '../../api/client'
import { EncounterPickerField } from '../encounters/EncounterPicker'
import { useEncounterPicker } from '../encounters/useEncounterPicker'
import * as documentSettingsApi from '../document_settings/api'
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

function formatFechaLabel(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}`
  )
}

async function showConsentPdf(consentId: string, newTab: Window | null) {
  const url = await api.getConsentPdfBlobUrl(consentId)
  if (newTab) newTab.location.href = url
}

// Los logos de "Formatos de documentos" exigen sesion y sucursal activa (a
// diferencia del logo de Marca y Temas, que es publico) -- se piden como blob
// autenticado, mismo patron que DocumentSettingsPage.tsx::useLogoUrl.
function useLogoBlobUrl(side: 'left' | 'right', hasLogo: boolean): string | null {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!hasLogo) return
    let objectUrl: string | null = null
    let cancelled = false
    apiRequestBlobUrl(`/document-settings/logo-${side}`).then((u) => {
      if (cancelled) {
        URL.revokeObjectURL(u)
        return
      }
      objectUrl = u
      setUrl(u)
    })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [side, hasLogo])

  return url
}

interface ClinicHeader {
  institutionalTitle: string
  placeLabel: string | null
  logoLeftUrl: string | null
  logoRightUrl: string | null
}

// Mismo criterio de fallback que el backend (documents/pdf_header.py::get_pdf_header_info):
// sin logo/titulo propio en "Formatos de documentos", se usa el de Marca y Temas.
function useClinicHeader(): ClinicHeader {
  const branding = useThemeStore((s) => s.branding)
  const settingsQuery = useQuery({
    queryKey: ['document-settings'],
    queryFn: documentSettingsApi.getDocumentSettings,
  })
  const settings = settingsQuery.data
  const logoLeftBlob = useLogoBlobUrl('left', !!settings?.has_logo_left)
  const logoRightBlob = useLogoBlobUrl('right', !!settings?.has_logo_right)

  return {
    institutionalTitle: settings?.institutional_title || branding?.display_name || '',
    placeLabel: settings?.place_label ?? null,
    logoLeftUrl: settings?.has_logo_left
      ? logoLeftBlob
      : branding?.logo_url
        ? resolveApiAssetUrl(branding.logo_url)
        : null,
    logoRightUrl: settings?.has_logo_right ? logoRightBlob : null,
  }
}

function DocumentHeaderPreview({ header }: { header: ClinicHeader }) {
  return (
    <div className={styles.docHeaderRow}>
      <div className={styles.docHeaderLogo}>
        {header.logoLeftUrl && <img src={header.logoLeftUrl} alt="" />}
      </div>
      <div className={styles.docHeaderTitle}>{header.institutionalTitle}</div>
      <div className={styles.docHeaderLogo}>
        {header.logoRightUrl && <img src={header.logoRightUrl} alt="" />}
      </div>
    </div>
  )
}

// El formato elegido: muestra el documento ya con los datos conocidos (punto
// 2d del encargo) -- encabezado+logos+titulo+cuerpo con {{paciente.nombre}},
// {{profesional.nombre}}, etc. ya resueltos, en vivo mientras se escribe. Si
// algo esta mal o falta, "Editar datos" revela los campos que se pueden
// modificar; al guardar vuelve a la vista de documento con los cambios ya
// reflejados. Solo al final, "Imprimir / Generar PDF" firma de verdad.
function TemplateDocumentPanel({
  patientId,
  patientName,
  encounterId,
  template,
  canWrite,
  canSign,
}: {
  patientId: string
  patientName: string
  encounterId: string
  template: DocumentTemplateOut
  canWrite: boolean
  canSign: boolean
}) {
  const templateCode = template.code
  const queryClient = useQueryClient()
  const header = useClinicHeader()
  const prefillQuery = useQuery({
    queryKey: ['consent-prefill', patientId, templateCode, encounterId],
    queryFn: () => api.getConsentPrefill(patientId, templateCode, encounterId),
  })
  const plansQuery = useQuery({
    queryKey: ['treatment-plans', patientId],
    queryFn: () => treatmentApi.listPlans(patientId),
  })
  const consentsQuery = useQuery({
    queryKey: ['consents', patientId],
    queryFn: () => api.listConsents(patientId),
  })

  const [mode, setMode] = useState<'view' | 'edit'>('view')
  // Lo que el prefill ya trae (editable: cada campo solo se "pisa" aqui una
  // vez que el usuario lo toca) -- derivado en el render en vez de copiarlo a
  // estado dentro de un efecto, para no duplicar la fuente de verdad del query.
  const [extraOverrides, setExtraOverrides] = useState<Record<string, string>>({})
  const [witness1, setWitness1] = useState('')
  const [witness2, setWitness2] = useState('')
  const [treatmentPlanId, setTreatmentPlanId] = useState('')
  const [signerNameOverride, setSignerNameOverride] = useState<string | null>(null)
  const [signerRelationshipOverride, setSignerRelationshipOverride] =
    useState<SignerRelationship | null>(null)
  const [signature, setSignature] = useState<string | null>(null)
  // A peticion del operador: al crear el PDF, la firma debe borrarse sola (antes
  // quedaba dibujada, lista para firmarse "encima" sin querer en el siguiente
  // documento). Remonta el SignaturePad (canvas en blanco de verdad, no solo el
  // valor exportado) en vez de depender de un metodo imperativo expuesto.
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

  const previewVariables: Record<string, unknown> = {
    ...(prefillQuery.data?.variables ?? {}),
    firmante: { nombre: signerName },
    testigos: { uno: witness1, dos: witness2 },
    extra: extraValues,
  }
  const bodyHtml = template.html_content
    ? renderTemplatePreview(template.html_content, previewVariables)
    : ''
  const fechaLabel = formatFechaLabel(new Date())

  const createMutation = useMutation({
    mutationFn: () =>
      api.createConsent(patientId, {
        encounter_id: encounterId,
        template_code: templateCode,
        treatment_plan_id: treatmentPlanId || null,
        signer_name: signerName,
        signer_relationship: signerRelationship,
        signature_png_base64: signature as string,
        extra_fields: extraValues,
        witness1_name: witness1.trim() || null,
        witness2_name: witness2.trim() || null,
      }),
    onSuccess: (consent) => {
      setSignerNameOverride(null)
      setSignature(null)
      setSignaturePadKey((k) => k + 1)
      queryClient.invalidateQueries({ queryKey: ['consents', patientId] })
      // El documento ya queda guardado en el expediente al crearse (no hay un
      // paso de "previsualizar antes de guardar" aparte, el documento ya se vio
      // arriba): se muestra el PDF de una vez para poder revisarlo e imprimirlo.
      // La pestana ya se abrio sincronica en el submit (mas abajo) para que el
      // bloqueador de ventanas emergentes no la descarte.
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
  const consentsForTemplate = (consentsQuery.data ?? []).filter(
    (c) => c.template_id === template.id,
  )

  return (
    <div className={styles.docPanel}>
      <div className={styles.docPreview}>
        <DocumentHeaderPreview header={header} />
        <p className={styles.placeDate}>
          {header.placeLabel
            ? `Lugar y fecha: ${header.placeLabel} a ${fechaLabel}`
            : `Fecha: ${fechaLabel}`}
        </p>
        <h3 className={styles.docTitle}>{TEMPLATE_CODE_LABELS[templateCode].toUpperCase()}</h3>
        <p className={styles.docPatientLine}>
          <strong>Paciente:</strong> {patientName}
        </p>
        {/* Contenido de confianza: la plantilla la escribe quien administra la
            clinica; los datos que se sustituyen (paciente, profesional, testigos,
            campos extra) ya se muestran/capturan en esta misma pantalla. */}
        <div dangerouslySetInnerHTML={{ __html: bodyHtml }} />
      </div>

      {mode === 'view' && missingRequired.length > 0 && (
        <div className={styles.errorBox}>
          Faltan datos obligatorios: {missingRequired.map(([, field]) => field.label).join(', ')}.{' '}
          <button type="button" className={styles.linkButton} onClick={() => setMode('edit')}>
            Completar
          </button>
        </div>
      )}

      {mode === 'edit' ? (
        <div className={styles.form}>
          {extraSpecs.map(([key, field]) => (
            <label key={key}>
              {field.label}
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
          <button type="button" className={styles.secondaryButton} onClick={() => setMode('view')}>
            Guardar y ver documento
          </button>
        </div>
      ) : (
        <button type="button" className={styles.linkButton} onClick={() => setMode('edit')}>
          Editar datos
        </button>
      )}

      {canSign && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            pendingTabRef.current = window.open('', '_blank')
            createMutation.mutate()
          }}
        >
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
              missingRequired.length > 0 ||
              !signerName.trim() ||
              !signature ||
              createMutation.isPending
            }
          >
            Imprimir / Generar PDF
          </button>
          {createMutation.isError && (
            <p className={styles.errorBox}>No se pudo generar el documento. Intenta de nuevo.</p>
          )}
        </form>
      )}

      {!!consentsForTemplate.length && (
        <div>
          <p className={styles.sectionTitle}>Firmados previamente con este formato</p>
          {consentsForTemplate.map((consent) => (
            <ConsentRow key={consent.id} consent={consent} canWrite={canWrite} />
          ))}
        </div>
      )}
    </div>
  )
}

function CategoryAccordion({
  category,
  templates,
  selectedCode,
  onSelect,
}: {
  category: TemplateCategory
  templates: DocumentTemplateOut[]
  selectedCode: TemplateCode | null
  onSelect: (code: TemplateCode) => void
}) {
  const sorted = [...templates].sort((a, b) =>
    TEMPLATE_CODE_LABELS[a.code].localeCompare(TEMPLATE_CODE_LABELS[b.code], 'es'),
  )
  if (!sorted.length) return null

  return (
    <details className={styles.subCard}>
      <summary>
        {TEMPLATE_CATEGORY_LABELS[category]} ({sorted.length})
      </summary>
      {sorted.length > 5 ? (
        <select
          value={selectedCode && sorted.some((t) => t.code === selectedCode) ? selectedCode : ''}
          onChange={(e) => onSelect(e.target.value as TemplateCode)}
        >
          <option value="">Selecciona un formato...</option>
          {sorted.map((t) => (
            <option key={t.code} value={t.code}>
              {TEMPLATE_CODE_LABELS[t.code]}
            </option>
          ))}
        </select>
      ) : (
        sorted.map((t) => (
          <div key={t.code} className={styles.contactItem}>
            <button type="button" className={styles.linkButton} onClick={() => onSelect(t.code)}>
              {TEMPLATE_CODE_LABELS[t.code]}
            </button>
          </div>
        ))
      )}
    </details>
  )
}

// Reemplaza a las antiguas "Plantillas de consentimiento" (solo vista previa)
// y "Consentimientos firmados" (solo firma): un formato elegido aqui ya hace
// las dos cosas (ver como queda + firmar e imprimir), ver TemplateDocumentPanel.
function PlantillasSection({
  patientId,
  patientName,
  canWrite,
  canSign,
}: {
  patientId: string
  patientName: string
  canWrite: boolean
  canSign: boolean
}) {
  const encounterPicker = useEncounterPicker(patientId, canSign)
  const templatesQuery = useQuery({ queryKey: ['document-templates'], queryFn: api.listTemplates })
  const [selectedCode, setSelectedCode] = useState<TemplateCode | null>(null)

  const categories: TemplateCategory[] = ['consentimiento', 'aviso_privacidad', 'carta']
  const selectedTemplate = templatesQuery.data?.find((t) => t.code === selectedCode) ?? null

  return (
    <details className={styles.card} open>
      <summary>Plantillas</summary>
      <EncounterPickerField encounterPicker={encounterPicker} />
      {categories.map((category) => (
        <CategoryAccordion
          key={category}
          category={category}
          templates={(templatesQuery.data ?? []).filter(
            (t) => categoryForTemplateCode(t.code) === category,
          )}
          selectedCode={selectedCode}
          onSelect={setSelectedCode}
        />
      ))}
      {!templatesQuery.data?.length && <p>Sin plantillas configuradas todavia.</p>}

      {selectedTemplate &&
        (encounterPicker.encounterId ? (
          <TemplateDocumentPanel
            key={`${selectedTemplate.code}-${encounterPicker.encounterId}`}
            patientId={patientId}
            patientName={patientName}
            encounterId={encounterPicker.encounterId}
            template={selectedTemplate}
            canWrite={canWrite}
            canSign={canSign}
          />
        ) : (
          <p className={styles.hint}>Selecciona o inicia una atención para continuar.</p>
        ))}
    </details>
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
  canWrite,
  canSign,
}: {
  patientId: string
  patientName: string
  patientAge: number
  canWrite: boolean
  canSign: boolean
}) {
  return (
    <div className={styles.grid}>
      <PlantillasSection
        patientId={patientId}
        patientName={patientName}
        canWrite={canWrite}
        canSign={canSign}
      />
      <ClinicalDocumentsSection patientId={patientId} canWrite={canWrite} />
    </div>
  )
}
