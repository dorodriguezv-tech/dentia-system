import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

/**
 * CLAUDE.md Fase 12: revision de accesibilidad (teclado, contraste, etiquetas).
 * axe-core audita automaticamente contraste WCAG, etiquetas de formulario, roles
 * ARIA y estructura de encabezados en las pantallas mas usadas; no sustituye una
 * revision manual con lector de pantalla, pero atrapa la mayoria de violaciones
 * objetivas sin tener que listarlas a mano pantalla por pantalla.
 */

const PASSWORD = 'Dentia2025!'

async function login(page: Page, email: string): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('Correo').fill(email)
  await page.getByLabel('Contrasena').fill(PASSWORD)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByRole('button', { name: 'Salir' })).toBeVisible()
}

async function expectNoSeriousViolations(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze()
  const serious = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  expect(serious, JSON.stringify(serious, null, 2)).toEqual([])
}

test.describe('accesibilidad (axe-core, WCAG 2 A/AA)', () => {
  test('pantalla de login', async ({ page }) => {
    await page.goto('/login')
    await expectNoSeriousViolations(page)
  })

  test('tablero de inicio (odontologo)', async ({ page }) => {
    await login(page, 'odontologo@dentalcare-demo.mx')
    await expectNoSeriousViolations(page)
  })

  test('listado de pacientes', async ({ page }) => {
    await login(page, 'odontologo@dentalcare-demo.mx')
    await page.getByRole('link', { name: 'Pacientes' }).click()
    await expectNoSeriousViolations(page)
  })

  test('agenda', async ({ page }) => {
    await login(page, 'odontologo@dentalcare-demo.mx')
    await page.getByRole('link', { name: 'Agenda' }).click()
    await expect(page.getByRole('heading', { name: 'Agenda' })).toBeVisible()
    await expectNoSeriousViolations(page)
  })

  test('ficha de un paciente (resumen, expediente, odontograma)', async ({ page }) => {
    await login(page, 'odontologo@dentalcare-demo.mx')
    await page.getByRole('link', { name: 'Pacientes' }).click()
    await page
      .getByRole('button', { name: /Abrir expediente de/ })
      .first()
      .click()
    await expect(page.getByRole('button', { name: 'Expediente', exact: true })).toBeVisible()
    await expectNoSeriousViolations(page)

    await page.getByRole('button', { name: 'Expediente', exact: true }).click()
    await expectNoSeriousViolations(page)

    await page.getByRole('button', { name: 'Odontograma' }).click()
    await expectNoSeriousViolations(page)
  })

  test('reportes (admin_clinica requiere MFA, se usa caja)', async ({ page }) => {
    await login(page, 'caja@dentalcare-demo.mx')
    await page.getByRole('link', { name: 'Reportes', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Reportes' })).toBeVisible()
    await expectNoSeriousViolations(page)
  })
})
