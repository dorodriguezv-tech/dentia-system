import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiRequestError } from '../../api/client'
import { BrandStripe, ClinicLogo, PoweredByDentia } from '../../components/brand/Brand'
import { useThemeStore } from '../../theme/store'
import styles from './AuthForm.module.css'
import * as api from './api'
import { isMfaRequired } from './types'
import { useAuthStore } from './store'
import { postLoginRedirect } from './navigation'
import { Turnstile } from './Turnstile'

export function LoginPage() {
  const navigate = useNavigate()
  const applySession = useAuthStore((s) => s.applySession)
  const branding = useThemeStore((s) => s.branding)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mfaToken, setMfaToken] = useState<string | null>(null)
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null)

  async function afterLogin() {
    const user = useAuthStore.getState().user
    const clinics = useAuthStore.getState().clinics
    navigate(postLoginRedirect(user, clinics))
  }

  async function handleCredentialsSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const result = await api.login(email, password, turnstileToken)
      if (isMfaRequired(result)) {
        setMfaToken(result.mfa_token)
      } else {
        await applySession(result)
        await afterLogin()
      }
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'No se pudo iniciar sesion')
    } finally {
      setLoading(false)
    }
  }

  async function handleMfaSubmit(event: FormEvent) {
    event.preventDefault()
    if (!mfaToken) return
    setError(null)
    setLoading(true)
    try {
      const tokens = await api.loginMfa(mfaToken, code)
      await applySession(tokens)
      await afterLogin()
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Codigo invalido')
    } finally {
      setLoading(false)
    }
  }

  const hasCustomLogo = branding?.has_custom_logo ?? false

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <BrandStripe />
        <div className={styles.cardBody}>
          <div className={styles.brandLogoWrap}>
            <ClinicLogo
              logoUrl={branding?.logo_url ?? null}
              hasCustomLogo={hasCustomLogo}
              clinicName={branding?.display_name ?? 'DENT-IA'}
              width={240}
            />
          </div>
          {/* Nombre de la clinica, siempre visible: el logo generico de DENT-IA no
              lo menciona, y aunque haya logo propio normalmente tampoco trae texto. */}
          {branding?.display_name && (
            <>
              <p className={styles.brand}>{branding.display_name}</p>
              {branding.subtitle && <p className={styles.hint}>{branding.subtitle}</p>}
            </>
          )}

          {error && <div className={styles.error}>{error}</div>}

          {mfaToken === null ? (
          <form onSubmit={handleCredentialsSubmit}>
            <div className={styles.field}>
              <label htmlFor="email">Correo</label>
              <input
                id="email"
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="password">Contrasena</label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <Turnstile onToken={setTurnstileToken} />
            <button className={styles.submit} type="submit" disabled={loading}>
              {loading ? 'Entrando...' : 'Entrar'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleMfaSubmit}>
            <p className={styles.hint}>Captura el codigo de tu aplicacion de autenticacion.</p>
            <div className={styles.field}>
              <label htmlFor="code">Codigo de verificacion</label>
              <input
                id="code"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                required
                autoFocus
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </div>
            <button className={styles.submit} type="submit" disabled={loading}>
              {loading ? 'Verificando...' : 'Verificar'}
            </button>
          </form>
          )}
          {hasCustomLogo && <PoweredByDentia />}
        </div>
      </div>
    </div>
  )
}
