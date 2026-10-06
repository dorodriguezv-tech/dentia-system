import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from './api'
import styles from './BillingSettingsPage.module.css'

export function BillingSettingsPage() {
  const queryClient = useQueryClient()
  const settingsQuery = useQuery({ queryKey: ['billing-settings'], queryFn: api.getBillingSettings })

  const updateMutation = useMutation({
    mutationFn: (enabled: boolean) => api.updateBillingSettings(enabled),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['billing-settings'] }),
  })

  if (settingsQuery.isLoading) return <p>Cargando configuracion de cobranza...</p>
  if (!settingsQuery.data) return <p>No se pudo cargar la configuracion de cobranza.</p>

  const enabled = settingsQuery.data.billing_enabled

  return (
    <section className={styles.page}>
      <h1>Cobranza</h1>
      <div className={styles.card}>
        <label className={styles.toggleRow}>
          <input
            type="checkbox"
            checked={enabled}
            disabled={updateMutation.isPending}
            onChange={(e) => updateMutation.mutate(e.target.checked)}
          />
          <span>Cobranza activa en esta sucursal</span>
        </label>
        <p className={styles.helpText}>
          Desactivala si esta clinica no cobra de verdad (por ejemplo, una clinica universitaria de
          practica): se oculta la pestaña "Cuenta" de los pacientes y no se pueden registrar pagos
          nuevos. Los procedimientos realizados siguen generando su cargo sugerido como registro
          clinico, pero nadie puede cobrarlo mientras este desactivada.
        </p>
      </div>
    </section>
  )
}
