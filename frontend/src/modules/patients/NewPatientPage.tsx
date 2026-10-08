import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ApiRequestError } from '../../api/client'
import * as agendaApi from '../agenda/api'
import * as api from './api'
import styles from './NewPatientPage.module.css'
import {
  CONTACT_ROLE_LABELS,
  type ContactCreateInput,
  type ContactRole,
  type DuplicateCandidateOut,
  type PatientCreateInput,
  type SexCode,
} from './types'

type Step = 'datos' | 'duplicados' | 'contactos'

const EMPTY_PATIENT: PatientCreateInput = {
  first_name: '',
  last_name_paternal: '',
  last_name_maternal: '',
  date_of_birth: '',
  sex: null,
  phone: '',
  email: '',
  address: '',
  default_resource_id: null,
  primary_provider_id: null,
}

export function NewPatientPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [step, setStep] = useState<Step>('datos')
  // Fase 13.4 (resto), "alta_rapida_paciente": Dentia abre esta pantalla con el
  // nombre/telefono dictados ya prellenados -- el alta se termina aqui a mano,
  // con la deteccion de duplicados obligatoria de siempre (CLAUDE.md regla 9:
  // la IA nunca crea el paciente directamente).
  const [patient, setPatient] = useState<PatientCreateInput>(() => ({
    ...EMPTY_PATIENT,
    first_name: searchParams.get('first_name') ?? '',
    last_name_paternal: searchParams.get('last_name_paternal') ?? '',
    phone: searchParams.get('phone') ?? '',
  }))
  // B3 (Parte B, Fase 12.2): gabinete y profesional tratante por defecto, opcionales
  // desde el alta -- la agenda los preselecciona despues al agendar.
  const providersQuery = useQuery({ queryKey: ['providers'], queryFn: agendaApi.listProviders })
  const resourcesQuery = useQuery({
    queryKey: ['resources'],
    queryFn: () => agendaApi.listResources(),
  })
  const [duplicates, setDuplicates] = useState<DuplicateCandidateOut[]>([])
  const [contacts, setContacts] = useState<ContactCreateInput[]>([])
  const [checking, setChecking] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function updateField<K extends keyof PatientCreateInput>(key: K, value: PatientCreateInput[K]) {
    setPatient((prev) => ({ ...prev, [key]: value }))
  }

  async function handleDatosSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setChecking(true)
    try {
      const candidates = await api.checkDuplicates({
        first_name: patient.first_name,
        last_name_paternal: patient.last_name_paternal,
        last_name_maternal: patient.last_name_maternal,
        date_of_birth: patient.date_of_birth || null,
        phone: patient.phone || null,
      })
      if (candidates.length > 0) {
        setDuplicates(candidates)
        setStep('duplicados')
      } else {
        setStep('contactos')
      }
    } catch {
      setError('No se pudo verificar duplicados. Intenta de nuevo.')
    } finally {
      setChecking(false)
    }
  }

  async function handleCreate() {
    setCreating(true)
    setError(null)
    try {
      const created = await api.createPatient({
        ...patient,
        last_name_maternal: patient.last_name_maternal || null,
        phone: patient.phone || null,
        email: patient.email || null,
        address: patient.address || null,
      })
      for (const contact of contacts) {
        await api.createContact(created.id, contact)
      }
      navigate(`/pacientes/${created.id}`)
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'No se pudo crear el paciente')
    } finally {
      setCreating(false)
    }
  }

  return (
    <section>
      <h1>Nuevo paciente</h1>
      <div className={styles.card}>
        <div className={styles.steps}>
          <span className={step === 'datos' ? styles.stepActive : undefined}>1. Datos</span>
          <span>›</span>
          <span className={step === 'duplicados' ? styles.stepActive : undefined}>
            2. Posibles duplicados
          </span>
          <span>›</span>
          <span className={step === 'contactos' ? styles.stepActive : undefined}>3. Contactos</span>
        </div>

        {error && <div className={styles.errorBox}>{error}</div>}

        {step === 'datos' && (
          <form onSubmit={handleDatosSubmit}>
            <div className={styles.grid}>
              <div className={styles.field}>
                <label htmlFor="first_name">Nombre(s)</label>
                <input
                  id="first_name"
                  required
                  value={patient.first_name}
                  onChange={(e) => updateField('first_name', e.target.value)}
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="last_name_paternal">Apellido paterno</label>
                <input
                  id="last_name_paternal"
                  required
                  value={patient.last_name_paternal}
                  onChange={(e) => updateField('last_name_paternal', e.target.value)}
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="last_name_maternal">Apellido materno</label>
                <input
                  id="last_name_maternal"
                  value={patient.last_name_maternal ?? ''}
                  onChange={(e) => updateField('last_name_maternal', e.target.value)}
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="date_of_birth">Fecha de nacimiento</label>
                <input
                  id="date_of_birth"
                  type="date"
                  required
                  value={patient.date_of_birth}
                  onChange={(e) => updateField('date_of_birth', e.target.value)}
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="sex">Sexo</label>
                <select
                  id="sex"
                  value={patient.sex ?? ''}
                  onChange={(e) => updateField('sex', (e.target.value || null) as SexCode | null)}
                >
                  <option value="">Sin especificar</option>
                  <option value="F">Femenino</option>
                  <option value="M">Masculino</option>
                  <option value="X">Otro</option>
                </select>
              </div>
              <div className={styles.field}>
                <label htmlFor="phone">Telefono</label>
                <input
                  id="phone"
                  value={patient.phone ?? ''}
                  onChange={(e) => updateField('phone', e.target.value)}
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="email">Correo</label>
                <input
                  id="email"
                  type="email"
                  value={patient.email ?? ''}
                  onChange={(e) => updateField('email', e.target.value)}
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="address">Direccion</label>
                <input
                  id="address"
                  value={patient.address ?? ''}
                  onChange={(e) => updateField('address', e.target.value)}
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="primary_provider_id">Profesional tratante (opcional)</label>
                <select
                  id="primary_provider_id"
                  value={patient.primary_provider_id ?? ''}
                  onChange={(e) => updateField('primary_provider_id', e.target.value || null)}
                >
                  <option value="">Sin asignar</option>
                  {providersQuery.data?.map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {provider.full_name}
                    </option>
                  ))}
                </select>
              </div>
              <div className={styles.field}>
                <label htmlFor="default_resource_id">Gabinete por defecto (opcional)</label>
                <select
                  id="default_resource_id"
                  value={patient.default_resource_id ?? ''}
                  onChange={(e) => updateField('default_resource_id', e.target.value || null)}
                >
                  <option value="">Sin asignar</option>
                  {resourcesQuery.data?.map((resource) => (
                    <option key={resource.id} value={resource.id}>
                      {resource.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className={styles.actions}>
              <button
                className={styles.secondaryButton}
                type="button"
                onClick={() => navigate('/pacientes')}
              >
                Cancelar
              </button>
              <button className={styles.primaryButton} type="submit" disabled={checking}>
                {checking ? 'Verificando...' : 'Siguiente'}
              </button>
            </div>
          </form>
        )}

        {step === 'duplicados' && (
          <div>
            <div className={styles.warningBox}>
              Encontramos pacientes parecidos. Revisa antes de continuar para no duplicar un
              expediente.
            </div>
            <div className={styles.duplicateList}>
              {duplicates.map((d) => (
                <div key={d.id} className={styles.duplicateCard}>
                  <strong>{d.full_name}</strong> — Expediente #{d.expediente_number}
                  <div>
                    Nacimiento: {d.date_of_birth} {d.phone && `· Tel: ${d.phone}`} · Similitud:{' '}
                    {Math.round(d.similarity * 100)}%
                  </div>
                </div>
              ))}
            </div>
            <div className={styles.actions}>
              <button
                className={styles.secondaryButton}
                type="button"
                onClick={() => setStep('datos')}
              >
                Volver a datos
              </button>
              <button
                className={styles.primaryButton}
                type="button"
                onClick={() => setStep('contactos')}
              >
                Ninguno es el mismo paciente, continuar
              </button>
            </div>
          </div>
        )}

        {step === 'contactos' && (
          <ContactsStep
            contacts={contacts}
            onChange={setContacts}
            onBack={() => setStep('datos')}
            onSubmit={handleCreate}
            creating={creating}
          />
        )}
      </div>
    </section>
  )
}

function ContactsStep({
  contacts,
  onChange,
  onBack,
  onSubmit,
  creating,
}: {
  contacts: ContactCreateInput[]
  onChange: (contacts: ContactCreateInput[]) => void
  onBack: () => void
  onSubmit: () => void
  creating: boolean
}) {
  const [role, setRole] = useState<ContactRole>('guardian')
  const [fullName, setFullName] = useState('')
  const [relationshipLabel, setRelationshipLabel] = useState('')
  const [phone, setPhone] = useState('')

  function addContact() {
    if (!fullName.trim()) return
    onChange([
      ...contacts,
      {
        role,
        full_name: fullName,
        relationship_label: relationshipLabel || null,
        phone: phone || null,
      },
    ])
    setFullName('')
    setRelationshipLabel('')
    setPhone('')
  }

  return (
    <div>
      <p>Tutor/responsable y contacto de emergencia (opcional, puedes agregarlos despues).</p>

      <div className={styles.contactList}>
        {contacts.map((c, i) => (
          <div key={i} className={styles.contactItem}>
            <span>
              {c.full_name} — {CONTACT_ROLE_LABELS[c.role]}
            </span>
            <button
              className={styles.linkButton}
              type="button"
              onClick={() => onChange(contacts.filter((_, idx) => idx !== i))}
            >
              Quitar
            </button>
          </div>
        ))}
      </div>

      <div className={styles.grid}>
        <div className={styles.field}>
          <label>Tipo</label>
          <select value={role} onChange={(e) => setRole(e.target.value as ContactRole)}>
            {Object.entries(CONTACT_ROLE_LABELS).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className={styles.field}>
          <label>Nombre</label>
          <input value={fullName} onChange={(e) => setFullName(e.target.value)} />
        </div>
        <div className={styles.field}>
          <label>Parentesco</label>
          <input value={relationshipLabel} onChange={(e) => setRelationshipLabel(e.target.value)} />
        </div>
        <div className={styles.field}>
          <label>Telefono</label>
          <input value={phone} onChange={(e) => setPhone(e.target.value)} />
        </div>
      </div>
      <div className={styles.actions}>
        <button className={styles.secondaryButton} type="button" onClick={addContact}>
          Agregar contacto
        </button>
      </div>

      <div className={styles.actionsSpaced}>
        <button className={styles.secondaryButton} type="button" onClick={onBack}>
          Atras
        </button>
        <button
          className={styles.primaryButton}
          type="button"
          onClick={onSubmit}
          disabled={creating}
        >
          {creating ? 'Creando...' : 'Crear paciente'}
        </button>
      </div>
    </div>
  )
}
