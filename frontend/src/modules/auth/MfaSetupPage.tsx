import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiRequestError } from '../../api/client'
import styles from './AuthForm.module.css'
import * as api from './api'
import { useAuthStore } from './store'
import { postLoginRedirect } from './navigation'

export function MfaSetupPage() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const clinics = useAuthStore((s) => s.clinics)
  const refreshUser = useAuthStore((s) => s.refreshUser)

  const [secret, setSecret] = useState<string | null>(null)
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!user?.mfa_setup_required) {
      navigate(postLoginRedirect(user, clinics), { replace: true })
      return
    }
    api.setupMfa().then((res) => setSecret(res.secret))
  }, [user, clinics, navigate])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await api.enableMfa(code)
      await refreshUser()
      navigate(postLoginRedirect(useAuthStore.getState().user, clinics), { replace: true })
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Codigo invalido')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <p className={styles.brand}>Configura la verificacion en dos pasos</p>
        <p className={styles.hint}>
          Tu rol exige MFA. Agrega esta clave en una app como Google Authenticator o Authy y despues
          captura el codigo de 6 digitos para activarla.
        </p>

        {secret && <div className={styles.secret}>{secret}</div>}
        {error && <div className={styles.error}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label htmlFor="code">Codigo de verificacion</label>
            <input
              id="code"
              inputMode="numeric"
              pattern="[0-9]{6}"
              maxLength={6}
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
          </div>
          <button className={styles.submit} type="submit" disabled={loading || !secret}>
            {loading ? 'Activando...' : 'Activar'}
          </button>
        </form>
      </div>
    </div>
  )
}
