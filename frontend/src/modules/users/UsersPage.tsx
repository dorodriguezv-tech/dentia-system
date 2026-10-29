import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiRequestBlobUrl, ApiRequestError } from '../../api/client'
import * as agendaApi from '../agenda/api'
import type { RoleOut, UserOut } from '../auth/types'
import { ROLES } from '../auth/roles'
import { useAuthStore } from '../auth/store'
import styles from './UsersPage.module.css'
import * as api from './api'
import type { ClinicAssignmentInput } from './types'

// B2 (Parte B, Fase 12.2): copia minima de agenda/rules.py::PROVIDER_ROLES (fuente
// de verdad real) -- solo estos roles tienen un Provider, asi que solo ellos
// necesitan elegir un gabinete por defecto.
const PROVIDER_ROLE_CODES = new Set(['odontologo', 'especialista'])

// Copia minima de app/core/password_policy.py::MIN_PASSWORD_LENGTH (fuente de verdad
// real). Bug real reportado ("al editar un usuario aparece 'Datos de entrada
// invalidos'"): este formulario aceptaba contrasenas de 8 caracteres (minLength
// desalineado del backend, que exige MIN_PASSWORD_LENGTH=12) y el backend las
// rechazaba con un 422 generico que no deja claro cual campo fallo -- se veia como
// si el formulario completo (incluido el nombre) fuera invalido. Si cambia alla,
// cambia aqui tambien.
const MIN_PASSWORD_LENGTH = 12

function initials(fullName: string): string {
  return fullName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('')
}

// Igual que patients/PatientHeader.tsx::usePhotoUrl -- un <img src> directo no puede
// mandar el Authorization header, asi que hay que pedir el archivo con fetch
// autenticado y convertirlo a blob URL.
function usePhotoUrl(userId: string, hasPhoto: boolean): string | null {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!hasPhoto) return

    let objectUrl: string | null = null
    let cancelled = false
    apiRequestBlobUrl(`/users/${userId}/photo`).then((u) => {
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
  }, [userId, hasPhoto])

  return url
}

function UserAvatar({ user }: { user: UserOut }) {
  const photoUrl = usePhotoUrl(user.id, user.has_photo)
  return photoUrl ? (
    <img className={styles.avatar} src={photoUrl} alt="" />
  ) : (
    <div className={styles.avatar}>{initials(user.full_name)}</div>
  )
}

function ResourcePicker({
  clinicId,
  label,
  value,
  onChange,
}: {
  clinicId: string | undefined
  label: string
  value: string
  onChange: (resourceId: string) => void
}) {
  const resourcesQuery = useQuery({
    queryKey: ['resources', clinicId ?? 'active'],
    queryFn: () => agendaApi.listResources(clinicId),
  })
  return (
    <select aria-label={label} value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">Sin gabinete por defecto</option>
      {resourcesQuery.data?.map((resource) => (
        <option key={resource.id} value={resource.id}>
          {resource.name}
        </option>
      ))}
    </select>
  )
}

function UserRow({ user, role }: { user: UserOut; role: RoleOut }) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [fullName, setFullName] = useState(user.full_name)
  const [email, setEmail] = useState(user.email)
  const [roleCode, setRoleCode] = useState(role.code)
  const [professionalLicense, setProfessionalLicense] = useState(user.professional_license ?? '')
  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const isProviderRole = PROVIDER_ROLE_CODES.has(roleCode)

  const updateMutation = useMutation({
    mutationFn: () =>
      api.updateUser(user.id, {
        full_name: fullName,
        email,
        role_code: roleCode,
        professional_license: isProviderRole ? professionalLicense : null,
        ...(newPassword.trim() ? { new_password: newPassword } : {}),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setEditing(false)
      setNewPassword('')
      setError(null)
    },
    onError: (err: unknown) => {
      setError(err instanceof ApiRequestError ? err.message : 'No se pudo guardar')
    },
  })

  const toggleActiveMutation = useMutation({
    mutationFn: (isActive: boolean) => api.updateUser(user.id, { is_active: isActive }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteUser(user.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
    onError: (err: unknown) => {
      setError(err instanceof ApiRequestError ? err.message : 'No se pudo borrar')
      setDeleting(false)
    },
  })

  const photoInputRef = useRef<HTMLInputElement>(null)
  const uploadPhotoMutation = useMutation({
    mutationFn: (file: File) => api.uploadUserPhoto(user.id, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  })

  function handlePhotoSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    uploadPhotoMutation.mutate(file)
  }

  if (editing) {
    return (
      <tr>
        <td colSpan={6}>
          {error && <div className={styles.error}>{error}</div>}
          <form
            className={styles.form}
            onSubmit={(e) => {
              e.preventDefault()
              updateMutation.mutate()
            }}
          >
            <label>
              Nombre completo
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </label>
            <label>
              Usuario (correo de acceso)
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label>
              Rol
              <select value={roleCode} onChange={(e) => setRoleCode(e.target.value)}>
                {ROLES.map((r) => (
                  <option key={r.code} value={r.code}>
                    {r.name}
                  </option>
                ))}
              </select>
            </label>
            {isProviderRole && (
              <label>
                Cedula profesional
                <input
                  type="text"
                  required
                  value={professionalLicense}
                  onChange={(e) => setProfessionalLicense(e.target.value)}
                />
              </label>
            )}
            <label>
              Nueva contrasena (dejar en blanco para no cambiarla, minimo{' '}
              {MIN_PASSWORD_LENGTH} caracteres)
              <input
                type="password"
                minLength={MIN_PASSWORD_LENGTH}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </label>
            <button className={styles.addButton} type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending ? 'Guardando...' : 'Guardar'}
            </button>
            <button className={styles.linkButton} type="button" onClick={() => setEditing(false)}>
              Cancelar
            </button>
          </form>
        </td>
      </tr>
    )
  }

  return (
    <>
      <tr className={user.is_active ? undefined : styles.inactive}>
        <td className={styles.nameCell}>
          <UserAvatar user={user} />
          {user.full_name}
        </td>
        <td>{user.email}</td>
        <td>{role.name}</td>
        <td>{user.professional_license ?? '-'}</td>
        <td>{user.is_active ? 'Activo' : 'Inactivo'}</td>
        <td className={styles.rowActions}>
          <button className={styles.linkButton} type="button" onClick={() => setEditing(true)}>
            Editar
          </button>
          <button
            className={styles.linkButton}
            type="button"
            onClick={() => photoInputRef.current?.click()}
            disabled={uploadPhotoMutation.isPending}
          >
            {uploadPhotoMutation.isPending ? 'Subiendo...' : 'Cambiar foto'}
          </button>
          <input
            ref={photoInputRef}
            type="file"
            accept="image/png,image/jpeg"
            hidden
            onChange={handlePhotoSelected}
          />
          <button
            className={styles.linkButton}
            type="button"
            onClick={() => toggleActiveMutation.mutate(!user.is_active)}
          >
            {user.is_active ? 'Desactivar' : 'Activar'}
          </button>
          {!deleting ? (
            <button
              className={styles.linkButtonDanger}
              type="button"
              onClick={() => setDeleting(true)}
            >
              Borrar
            </button>
          ) : (
            <>
              <span>¿Seguro?</span>
              <button
                className={styles.linkButtonDanger}
                type="button"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate()}
              >
                Confirmar
              </button>
              <button className={styles.linkButton} type="button" onClick={() => setDeleting(false)}>
                Cancelar
              </button>
            </>
          )}
        </td>
      </tr>
      {error && (
        <tr>
          <td colSpan={6}>
            <div className={styles.error}>{error}</div>
          </td>
        </tr>
      )}
    </>
  )
}

export function UsersPage() {
  const queryClient = useQueryClient()
  const usersQuery = useQuery({ queryKey: ['users'], queryFn: api.listUsers })
  const myClinics = useAuthStore((s) => s.clinics)
  const activeClinicId = useAuthStore((s) => s.activeClinicId)

  // B2: el administrador solo puede elegir, al dar de alta, otras sucursales
  // donde tambien administra usuarios (misma regla que aplica el backend).
  const otherAdminClinics = myClinics.filter(
    (c) => c.role.code === 'admin_clinica' && c.clinic.id !== activeClinicId,
  )

  const [showForm, setShowForm] = useState(false)
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [roleCode, setRoleCode] = useState(ROLES[0].code)
  const [professionalLicense, setProfessionalLicense] = useState('')
  const [defaultResourceId, setDefaultResourceId] = useState('')
  const [extraClinicIds, setExtraClinicIds] = useState<Set<string>>(new Set())
  const [extraDefaultResources, setExtraDefaultResources] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)

  const isProviderRole = PROVIDER_ROLE_CODES.has(roleCode)

  const createMutation = useMutation({
    mutationFn: api.createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setShowForm(false)
      setEmail('')
      setFullName('')
      setPassword('')
      setProfessionalLicense('')
      setDefaultResourceId('')
      setExtraClinicIds(new Set())
      setExtraDefaultResources({})
    },
    onError: (err: unknown) => {
      setError(err instanceof ApiRequestError ? err.message : 'No se pudo crear el usuario')
    },
  })

  function toggleExtraClinic(clinicId: string) {
    setExtraClinicIds((prev) => {
      const next = new Set(prev)
      if (next.has(clinicId)) next.delete(clinicId)
      else next.add(clinicId)
      return next
    })
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    const additional_clinics: ClinicAssignmentInput[] = [...extraClinicIds].map((clinicId) => ({
      clinic_id: clinicId,
      default_resource_id: extraDefaultResources[clinicId] || null,
    }))
    createMutation.mutate({
      email,
      full_name: fullName,
      password,
      role_code: roleCode,
      professional_license: isProviderRole ? professionalLicense : null,
      default_resource_id: defaultResourceId || null,
      additional_clinics,
    })
  }

  return (
    <section>
      <div className={styles.toolbar}>
        <h1>Usuarios</h1>
        <button className={styles.addButton} type="button" onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Cancelar' : 'Agregar usuario'}
        </button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {showForm && (
        <form className={styles.form} onSubmit={handleSubmit}>
          <label>
            Correo
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Nombre completo
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </label>
          <label>
            Contrasena temporal (minimo {MIN_PASSWORD_LENGTH} caracteres)
            <input
              type="password"
              required
              minLength={MIN_PASSWORD_LENGTH}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <label>
            Rol
            <select value={roleCode} onChange={(e) => setRoleCode(e.target.value)}>
              {ROLES.map((role) => (
                <option key={role.code} value={role.code}>
                  {role.name}
                </option>
              ))}
            </select>
          </label>

          {isProviderRole && (
            <label>
              Cedula profesional
              <input
                type="text"
                required
                value={professionalLicense}
                onChange={(e) => setProfessionalLicense(e.target.value)}
              />
            </label>
          )}

          {isProviderRole && (
            <label>
              Gabinete por defecto
              <ResourcePicker
                clinicId={undefined}
                label="Gabinete por defecto"
                value={defaultResourceId}
                onChange={setDefaultResourceId}
              />
            </label>
          )}

          {otherAdminClinics.length > 0 && (
            <div className={styles.clinicsBlock}>
              <span>Tambien asignar a otras sucursales</span>
              {otherAdminClinics.map(({ clinic }) => (
                <div key={clinic.id} className={styles.clinicRow}>
                  <label>
                    <input
                      type="checkbox"
                      checked={extraClinicIds.has(clinic.id)}
                      onChange={() => toggleExtraClinic(clinic.id)}
                    />
                    {clinic.name}
                  </label>
                  {isProviderRole && extraClinicIds.has(clinic.id) && (
                    <ResourcePicker
                      clinicId={clinic.id}
                      label={`Gabinete por defecto en ${clinic.name}`}
                      value={extraDefaultResources[clinic.id] ?? ''}
                      onChange={(resourceId) =>
                        setExtraDefaultResources((prev) => ({ ...prev, [clinic.id]: resourceId }))
                      }
                    />
                  )}
                </div>
              ))}
            </div>
          )}

          <button className={styles.addButton} type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? 'Creando...' : 'Crear'}
          </button>
        </form>
      )}

      {usersQuery.isLoading && <p>Cargando usuarios...</p>}
      {usersQuery.isError && <p>No se pudieron cargar los usuarios.</p>}

      {usersQuery.data && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Correo</th>
              <th>Rol</th>
              <th>Cedula</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {usersQuery.data.map(({ user, role }) => (
              <UserRow key={user.id} user={user} role={role} />
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
