import { expect, test, type Page } from '@playwright/test'

/**
 * CLAUDE.md Fase 12: rendimiento (p95 de 2 s o menos en pantallas habituales).
 *
 * Corre contra `npm run dev` (Vite sin minificar, sin build de produccion -- ver
 * e2e/playwright.config.ts, el mismo servidor que usan full-flow.spec.ts y
 * accessibility.spec.ts), asi que es una cota superior pesimista, no un benchmark
 * de produccion: un build de produccion (`npm run build` + servido detras de un
 * proxy) deberia ser igual o mas rapido. Sirve para detectar una regresion grande
 * (p.ej. una consulta N+1 nueva, un bundle que se disparo de tamano), no para medir
 * el presupuesto exacto de produccion.
 */

const PASSWORD = 'Dentia2025!'
const SAMPLES = 5
const P95_BUDGET_MS = 2000

async function login(page: Page, email: string): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('Correo').fill(email)
  await page.getByLabel('Contrasena').fill(PASSWORD)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByRole('button', { name: 'Salir' })).toBeVisible()
}

function p95(samplesMs: number[]): number {
  const sorted = [...samplesMs].sort((a, b) => a - b)
  const index = Math.ceil(0.95 * sorted.length) - 1
  return sorted[Math.max(0, index)]
}

async function measureMs(action: () => Promise<void>): Promise<number> {
  const start = Date.now()
  await action()
  return Date.now() - start
}

function assertP95WithinBudget(screenName: string, samples: number[]): void {
  const value = p95(samples)
  expect(value, `${screenName}: muestras = [${samples.join(', ')}] ms, p95 = ${value} ms`).toBeLessThanOrEqual(
    P95_BUDGET_MS,
  )
}

test.describe('rendimiento (pantallas habituales, p95 <= 2 s)', () => {
  test('carga inicial de la pantalla de login', async ({ page }) => {
    const samples: number[] = []
    for (let i = 0; i < SAMPLES; i++) {
      samples.push(
        await measureMs(async () => {
          await page.goto('/login')
          await expect(page.getByRole('button', { name: 'Entrar' })).toBeVisible()
        }),
      )
    }
    assertP95WithinBudget('login', samples)
  })

  test('tablero de inicio tras autenticarse', async ({ page }) => {
    const samples: number[] = []
    for (let i = 0; i < SAMPLES; i++) {
      await page.goto('/login')
      samples.push(
        await measureMs(async () => {
          await page.getByLabel('Correo').fill('odontologo@dentalcare-demo.mx')
          await page.getByLabel('Contrasena').fill(PASSWORD)
          await page.getByRole('button', { name: 'Entrar' }).click()
          await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
        }),
      )
      await page.getByRole('button', { name: 'Salir' }).click()
    }
    assertP95WithinBudget('tablero de inicio', samples)
  })

  test('navegacion entre pantallas ya autenticado (listado de pacientes, agenda, reportes)', async ({ page }) => {
    await login(page, 'odontologo@dentalcare-demo.mx')

    const screens: Array<{ name: string; go: () => Promise<void> }> = [
      {
        name: 'Pacientes',
        go: async () => {
          await page.getByRole('link', { name: 'Pacientes' }).click()
          await expect(page.getByRole('heading', { name: 'Pacientes', exact: true })).toBeVisible()
        },
      },
      {
        name: 'Agenda',
        go: async () => {
          await page.getByRole('link', { name: 'Agenda' }).click()
          await expect(page.getByRole('heading', { name: 'Agenda' })).toBeVisible()
        },
      },
      {
        name: 'Inicio',
        go: async () => {
          await page.getByRole('link', { name: 'Inicio' }).click()
          await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
        },
      },
    ]

    for (const screen of screens) {
      const samples: number[] = []
      for (let i = 0; i < SAMPLES; i++) {
        samples.push(await measureMs(screen.go))
      }
      assertP95WithinBudget(screen.name, samples)
    }
  })

  test('ficha de un paciente (resumen, expediente, odontograma)', async ({ page }) => {
    await login(page, 'odontologo@dentalcare-demo.mx')
    await page.getByRole('link', { name: 'Pacientes' }).click()
    await expect(page.getByRole('heading', { name: 'Pacientes', exact: true })).toBeVisible()

    const abrirExpediente = async (): Promise<void> => {
      await page
        .getByRole('button', { name: /Abrir expediente de/ })
        .first()
        .click()
      await expect(page.getByRole('button', { name: 'Expediente', exact: true })).toBeVisible()
    }

    const volverAlListado = async (): Promise<void> => {
      await page.getByRole('link', { name: 'Pacientes' }).click()
      await expect(page.getByRole('heading', { name: 'Pacientes', exact: true })).toBeVisible()
    }

    const resumenSamples: number[] = []
    for (let i = 0; i < SAMPLES; i++) {
      resumenSamples.push(await measureMs(abrirExpediente))
      await volverAlListado()
    }
    assertP95WithinBudget('Resumen del paciente', resumenSamples)

    // Expediente y odontograma se miden sobre la misma ficha ya abierta, alternando
    // con la pestana "Resumen" para que cada muestra vuelva a montar el componente
    // (como pasaria navegando de verdad entre pestanas, no solo la primera vez).
    await abrirExpediente()

    for (const [tabName, label] of [
      ['Expediente', 'Expediente'],
      ['Odontograma', 'Odontograma'],
    ] as const) {
      const samples: number[] = []
      for (let i = 0; i < SAMPLES; i++) {
        samples.push(
          await measureMs(async () => {
            await page.getByRole('button', { name: label, exact: true }).click()
          }),
        )
        await page.getByRole('button', { name: 'Resumen', exact: true }).click()
      }
      assertP95WithinBudget(tabName, samples)
    }
  })
})
