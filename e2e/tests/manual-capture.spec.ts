import { expect, test, type Page } from '@playwright/test'
import { mkdirSync } from 'node:fs'

/**
 * CLAUDE.md Fase 12: capturas para docs/MANUAL_USUARIO.md.
 *
 * No es una prueba de verificacion (no corre en la suite normal, ver el `test.skip`
 * de abajo): es un script reutilizable para regenerar las capturas del manual cuando
 * cambie la interfaz. Se corre a mano:
 *
 *   CAPTURE_SCREENSHOTS=1 npx playwright test tests/manual-capture.spec.ts
 *
 * Usa el paciente #000001 (el primero que crea `python -m app.seed`, con el
 * expediente/odontograma/plan de tratamiento de muestra -- ver backend/app/seed.py,
 * `patients[0]`) buscandolo por numero de expediente (Ctrl+K) en vez de por nombre,
 * porque el nombre es aleatorio (Faker).
 */

test.skip(!process.env.CAPTURE_SCREENSHOTS, 'solo para regenerar docs/MANUAL_USUARIO.md')

const PASSWORD = 'Dentia2025!'
const OUT_DIR = '../docs/manual'

test.beforeAll(() => {
  mkdirSync(OUT_DIR, { recursive: true })
})

async function login(page: Page, email: string): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('Correo').fill(email)
  await page.getByLabel('Contrasena').fill(PASSWORD)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByRole('button', { name: 'Salir' })).toBeVisible()
}

async function openSamplePatient(page: Page): Promise<void> {
  await page.keyboard.press('Control+k')
  await page.getByPlaceholder(/Buscar paciente por nombre/).fill('000001')
  await page.getByRole('button', { name: /000001/ }).first().click()
  await expect(page.getByRole('button', { name: 'Expediente', exact: true })).toBeVisible()
}

async function shoot(page: Page, name: string): Promise<void> {
  await page.screenshot({ path: `${OUT_DIR}/${name}.png` })
}

test('capturar pantallas para el manual de usuario', async ({ page }) => {
  await test.step('login', async () => {
    await page.goto('/login')
    await shoot(page, '01-login')
  })

  await test.step('tablero de inicio (odontologo)', async () => {
    await login(page, 'odontologo@dentalcare-demo.mx')
    await shoot(page, '02-tablero')
  })

  await test.step('agenda', async () => {
    await page.getByRole('link', { name: 'Agenda' }).click()
    await expect(page.getByRole('heading', { name: 'Agenda' })).toBeVisible()
    await shoot(page, '03-agenda')
    await page.getByRole('button', { name: 'Salir' }).click()
  })

  await test.step('listado de pacientes (recepcion, con boton Nuevo paciente)', async () => {
    await login(page, 'recepcion@dentalcare-demo.mx')
    await page.getByRole('link', { name: 'Pacientes' }).click()
    await expect(page.getByRole('button', { name: 'Nuevo paciente' })).toBeVisible()
    await shoot(page, '04-pacientes')
    await page.getByRole('button', { name: 'Salir' }).click()
  })

  await test.step('ficha del paciente: resumen, expediente, odontograma, tratamientos', async () => {
    await login(page, 'odontologo@dentalcare-demo.mx')
    await page.getByRole('link', { name: 'Pacientes' }).click()
    await openSamplePatient(page)
    await shoot(page, '05-paciente-resumen')

    await page.getByRole('button', { name: 'Expediente', exact: true }).click()
    await shoot(page, '06-paciente-expediente')

    await page.getByRole('button', { name: 'Odontograma' }).click()
    await shoot(page, '07-odontograma')

    await page.getByRole('button', { name: 'Tratamientos' }).click()
    await shoot(page, '08-tratamientos')

    await page.getByRole('button', { name: 'Salir' }).click()
  })

  await test.step('cuenta del paciente (caja)', async () => {
    await login(page, 'caja@dentalcare-demo.mx')
    await page.getByRole('link', { name: 'Pacientes' }).click()
    await openSamplePatient(page)
    await page.getByRole('button', { name: 'Cuenta', exact: true }).click()
    await shoot(page, '09-cuenta')

    await page.getByRole('link', { name: 'Reportes', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Reportes' })).toBeVisible()
    await shoot(page, '10-reportes')
    await page.getByRole('button', { name: 'Salir' }).click()
  })
})
