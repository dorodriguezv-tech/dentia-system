import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as encountersApi from '../encounters/api'
import * as treatmentApi from '../treatment/api'
import * as api from './api'
import { SIGNER_RELATIONSHIP_LABELS, TEMPLATE_CODE_LABELS, TEMPLATE_CODES } from './catalog'
import styles from './ConsentsTab.module.css'
import { SignaturePad } from './SignaturePad'
import type { ConsentOut, SignerRelationship, TemplateCode } from './types'

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
    <select value={value} onChange={(e) => onChange(e.target.value)}>
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

function TemplatesSection({ canWrite }: { canWrite: boolean }) {
  const queryClient = useQueryClient()
  const templatesQuery = useQuery({ queryKey: ['document-templates'], queryFn: api.listTemplates })

  const [code, setCode] = useState<TemplateCode>('general')
  const [name, setName] = useState('')
  const [htmlContent, setHtmlContent] = useState('')

  const createMutation = useMutation({
    mutationFn: () => api.createTemplateVersion({ code, name, html_content: htmlContent }),
    onSuccess: () => {
      setName('')
      setHtmlContent('')
      queryClient.invalidateQueries({ queryKey: ['document-templates'] })
    },
  })

  return (
    <details className={styles.card}>
      <summary>Plantillas de consentimiento</summary>
      {templatesQuery.data?.map((template) => (
        <div key={template.id} className={styles.contactItem}>
          <span>
            {TEMPLATE_CODE_LABELS[template.code]}: {template.name} (version {template.version})
          </span>
        </div>
      ))}
      {!templatesQuery.data?.length && <p>Sin plantillas configuradas todavia.</p>}

      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <select value={code} onChange={(e) => setCode(e.target.value as TemplateCode)}>
            {TEMPLATE_CODES.map((c) => (
              <option key={c} value={c}>
                {TEMPLATE_CODE_LABELS[c]}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Nombre de la plantilla"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <textarea
            placeholder="Contenido HTML (usa {{paciente.nombre}}, {{procedimiento.nombre}}, {{plan.titulo}}, {{clinica.nombre}}, {{fecha}}, {{profesional.nombre}})"
            required
            rows={5}
            value={htmlContent}
            onChange={(e) => setHtmlContent(e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!name.trim() || !htmlContent.trim() || createMutation.isPending}
          >
            Guardar nueva version
          </button>
        </form>
      )}
    </details>
  )
}

function NewConsentForm({ patientId }: { patientId: string }) {
  const queryClient = useQueryClient()
  const encountersQuery = useQuery({
    queryKey: ['patient-encounters', patientId],
    queryFn: () => encountersApi.listPatientEncounters(patientId),
  })
  const templatesQuery = useQuery({ queryKey: ['document-templates'], queryFn: api.listTemplates })
  const plansQuery = useQuery({
    queryKey: ['treatment-plans', patientId],
    queryFn: () => treatmentApi.listPlans(patientId),
  })

  const [encounterId, setEncounterId] = useState('')
  const [templateCode, setTemplateCode] = useState<TemplateCode | ''>('')
  const [treatmentPlanId, setTreatmentPlanId] = useState('')
  const [signerName, setSignerName] = useState('')
  const [signerRelationship, setSignerRelationship] = useState<SignerRelationship>('paciente')
  const [signature, setSignature] = useState<string | null>(null)

  const createMutation = useMutation({
    mutationFn: () =>
      api.createConsent(patientId, {
        encounter_id: encounterId,
        template_code: templateCode as TemplateCode,
        treatment_plan_id: treatmentPlanId || null,
        signer_name: signerName,
        signer_relationship: signerRelationship,
        signature_png_base64: signature as string,
      }),
    onSuccess: () => {
      setSignerName('')
      setSignature(null)
      queryClient.invalidateQueries({ queryKey: ['consents', patientId] })
    },
  })

  const currentCodes = templatesQuery.data?.map((t) => t.code) ?? []

  return (
    <form
      className={styles.form}
      onSubmit={(e) => {
        e.preventDefault()
        createMutation.mutate()
      }}
    >
      <EncounterSelect encounters={encountersQuery.data ?? []} value={encounterId} onChange={setEncounterId} />
      <select value={templateCode} onChange={(e) => setTemplateCode(e.target.value as TemplateCode)}>
        <option value="">Selecciona una plantilla...</option>
        {currentCodes.map((code) => (
          <option key={code} value={code}>
            {TEMPLATE_CODE_LABELS[code]}
          </option>
        ))}
      </select>
      <select value={treatmentPlanId} onChange={(e) => setTreatmentPlanId(e.target.value)}>
        <option value="">Sin plan de tratamiento vinculado</option>
        {plansQuery.data?.map((plan) => (
          <option key={plan.id} value={plan.id}>
            {plan.title}
          </option>
        ))}
      </select>
      <input
        type="text"
        placeholder="Nombre de quien firma"
        required
        value={signerName}
        onChange={(e) => setSignerName(e.target.value)}
      />
      <select
        value={signerRelationship}
        onChange={(e) => setSignerRelationship(e.target.value as SignerRelationship)}
      >
        {Object.entries(SIGNER_RELATIONSHIP_LABELS).map(([code, label]) => (
          <option key={code} value={code}>
            {label}
          </option>
        ))}
      </select>
      <SignaturePad onChange={setSignature} />
      <button
        className={styles.primaryButton}
        type="submit"
        disabled={
          !encounterId || !templateCode || !signerName.trim() || !signature || createMutation.isPending
        }
      >
        Firmar y generar PDF
      </button>
    </form>
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

  async function openPdf() {
    // window.open se llama sincronico, antes del await, para no perder el gesto del
    // usuario y que el bloqueador de ventanas emergentes no lo descarte (mismo patron
    // que el PDF del presupuesto en la Fase 7).
    const newTab = window.open('', '_blank')
    const url = await api.getConsentPdfBlobUrl(consent.id)
    if (newTab) newTab.location.href = url
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
  canWrite,
  canSign,
}: {
  patientId: string
  canWrite: boolean
  canSign: boolean
}) {
  const consentsQuery = useQuery({
    queryKey: ['consents', patientId],
    queryFn: () => api.listConsents(patientId),
  })

  return (
    <div className={styles.grid}>
      <TemplatesSection canWrite={canWrite} />
      <details className={styles.card} open>
        <summary>Consentimientos firmados</summary>
        {consentsQuery.data?.map((consent) => (
          <ConsentRow key={consent.id} consent={consent} canWrite={canWrite} />
        ))}
        {!consentsQuery.data?.length && <p>Sin consentimientos firmados.</p>}
        {canSign && <NewConsentForm patientId={patientId} />}
      </details>
    </div>
  )
}
