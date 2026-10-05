import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiRequestError } from '../../api/client'
import { ROLES } from '../auth/roles'
import styles from './UsersPage.module.css'
import * as api from './api'

export function UsersPage() {
  const queryClient = useQueryClient()
  const usersQuery = useQuery({ queryKey: ['users'], queryFn: api.listUsers })

  const [showForm, setShowForm] = useState(false)
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [roleCode, setRoleCode] = useState(ROLES[0].code)
  const [error, setError] = useState<string | null>(null)

  const createMutation = useMutation({
    mutationFn: api.createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setShowForm(false)
      setEmail('')
      setFullName('')
      setPassword('')
    },
    onError: (err: unknown) => {
      setError(err instanceof ApiRequestError ? err.message : 'No se pudo crear el usuario')
    },
  })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ userId, isActive }: { userId: string; isActive: boolean }) =>
      api.updateUser(userId, { is_active: isActive }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    createMutation.mutate({ email, full_name: fullName, password, role_code: roleCode })
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
            Contrasena temporal
            <input
              type="password"
              required
              minLength={8}
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
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {usersQuery.data.map(({ user, role }) => (
              <tr key={user.id} className={user.is_active ? undefined : styles.inactive}>
                <td>{user.full_name}</td>
                <td>{user.email}</td>
                <td>{role.name}</td>
                <td>{user.is_active ? 'Activo' : 'Inactivo'}</td>
                <td>
                  <button
                    className={styles.linkButton}
                    type="button"
                    onClick={() =>
                      toggleActiveMutation.mutate({ userId: user.id, isActive: !user.is_active })
                    }
                  >
                    {user.is_active ? 'Desactivar' : 'Activar'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
