import { expect, test, type Page } from '@playwright/test'

/**
 * Fase 13 ("Dentia"), resto de 13.6 "Afinacion" (docs/06... C4): "VOICE_FAKE_
 * MODE para E2E". A diferencia de las pruebas de integracion del backend
 * (que mandan fake_wake/fake_order directo por un WebSocket de prueba), esto
 * corre contra el FRONTEND real en un navegador real -- confirma que
 * useVoiceSession.ts de verdad reacciona a los mensajes del servidor (estado
 * del orbe, navegacion por ui_action) de punta a punta, no solo que el
 * backend los manda.
 *
 * window.__dentiaTestSend (ver useVoiceSession.ts) es el UNICO gancho nuevo
 * en el frontend para esto -- nunca existe fuera de VOICE_FAKE_MODE/no-
 * produccion, y VOICE_FAKE_MODE=true + cuenta regresiva/seguimiento cortos
 * vienen del webServer de playwright.config.ts, no de aqui.
 */

const PASSWORD = 'Dentia2025!'

async function login(page: Page, email: string): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('Correo').fill(email)
  await page.getByLabel('Contrasena').fill(PASSWORD)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByRole('button', { name: 'Salir' })).toBeVisible()
}

async function sendFake(page: Page, payload: Record<string, unknown>): Promise<void> {
  await page.evaluate((p) => window.__dentiaTestSend?.(p), payload)
}

test('el orbe de Dentia reacciona a la palabra de activacion y navega por voz', async ({
  page,
}) => {
  await login(page, 'odontologo@dentalcare-demo.mx')

  const orb = page.getByRole('button', { name: 'Dentia escuchando en segundo plano' })
  await expect(orb).toBeVisible()

  // No se comprueba el estado intermedio "awake" (Dentia te escucha) a
  // proposito: el servidor manda awake/speaking/listening en una rafaga casi
  // instantanea (VOICE_FAKE_MODE no sintetiza audio real) y Playwright podria
  // no alcanzar a verlo entre un sondeo del DOM y el siguiente -- flaky sin
  // aportar nada que el resto de la prueba no confirme ya.
  await sendFake(page, { type: 'fake_wake' })
  await expect(page.getByRole('status')).toHaveText('¿Sí?')

  // Vuelve a la ventana de seguimiento (sec. 2.1 del diseno) -- se puede
  // seguir hablando sin repetir "Dentia".
  await expect(page.getByRole('button', { name: 'Dentia escuchando tu orden' })).toBeVisible()

  await sendFake(page, { type: 'fake_order', text: 've a la agenda' })
  await expect(page).toHaveURL(/\/agenda$/)
  await expect(page.getByRole('status')).toHaveText('Abriendo agenda.')
})
