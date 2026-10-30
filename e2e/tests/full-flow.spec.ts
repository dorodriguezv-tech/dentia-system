import { expect, test, type Page } from '@playwright/test'

/**
 * CLAUDE.md Fase 12: flujo completo Paciente -> Cita -> Atencion -> Dictado IA
 * (con AI_FAKE_MODE, ver backend/app/ai/ollama_client.py) -> aceptar propuestas ->
 * Odontograma -> Diagnostico -> Plan -> Consentimiento -> Pago -> Seguimiento.
 *
 * Usa tres roles sembrados por `python -m app.seed` (recepcion, odontologo, caja),
 * ninguno exige MFA (solo admin_clinica la exige, CLAUDE.md sec. 5) -- asi el E2E
 * no depende de un secreto TOTP. Cada rol solo puede hacer lo que CLAUDE.md sec. 5
 * le permite (docs/MATRIZ_PERMISOS.md): recepcion da de alta al paciente y agenda
 * la cita (patients.write/agenda.write), el odontologo hace la atencion clinica
 * completa (records/odontogram/diagnosis/treatment/documents/ai), y caja registra
 * el pago (billing.write) -- un solo rol no puede recorrer todo el flujo, es RBAC
 * real, no una limitacion del test.
 *
 * Corre contra la base de datos de desarrollo (no una base aislada de E2E todavia,
 * ver docs/PENDIENTES_CLINICOS.md): cada corrida crea un paciente nuevo con un
 * sufijo de tiempo para no chocar con corridas anteriores.
 */

const PASSWORD = 'Dentia2025!'
const RUN_ID = Date.now().toString().slice(-8)
const PATIENT_FIRST_NAME = 'E2E'
const PATIENT_LAST_NAME = `Playwright${RUN_ID}`

// Dia/mes/hora derivados del timestamp de la corrida: sembrar siempre el mismo
// slot fijo choca con el appointment que dejo una corrida anterior (mismo
// profesional, mismo horario) -- sobre todo en desarrollo, corriendo la
// suite muchas veces seguidas el mismo dia real. Con >9000 combinaciones
// posibles (28 dias x 24 meses x 14 horas) dos corridas casi nunca coinciden.
const RUN_SEED = Number(RUN_ID) || Date.now()
const CITA_DAY = 1 + (RUN_SEED % 28)
const CITA_MONTHS_AHEAD = 6 + (Math.floor(RUN_SEED / 28) % 24)
const CITA_HOUR = 7 + (Math.floor(RUN_SEED / (28 * 24)) % 14)
const SEGUIMIENTO_DAY = CITA_DAY === 28 ? 1 : CITA_DAY + 1
const SEGUIMIENTO_MONTHS_AHEAD = CITA_MONTHS_AHEAD + 1
const SEGUIMIENTO_HOUR = CITA_HOUR === 20 ? 7 : CITA_HOUR + 1

async function login(page: Page, email: string): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('Correo').fill(email)
  await page.getByLabel('Contrasena').fill(PASSWORD)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByRole('button', { name: 'Salir' })).toBeVisible()
}

async function logout(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Salir' }).click()
  await expect(page).toHaveURL(/\/login$/)
}

/**
 * Agenda un slot varios meses en el futuro (navegando por la vista de mes, mucho
 * mas rapido que avanzar dia por dia) para no chocar con las citas que ya siembra
 * `app.seed` (siempre "manana" o "la semana que viene" relativas a cuando se
 * corrio el seed). `monthsAhead` distinto entre llamadas evita que dos citas de la
 * misma corrida (o de corridas repetidas en desarrollo) caigan en el mismo
 * horario del mismo profesional.
 */
async function openFutureDay(page: Page, monthsAhead: number, day: number): Promise<void> {
  await page.getByRole('button', { name: 'Mes' }).click()
  for (let i = 0; i < monthsAhead; i++) {
    await page.getByRole('button', { name: 'Siguiente' }).click()
  }
  const dayPattern = new RegExp(`^${day}(\\+\\d+)?$`)
  await page.getByRole('button', { name: dayPattern }).first().click()
}

async function openFutureDaySlot(
  page: Page,
  monthsAhead: number,
  day: number,
  hour: number,
): Promise<void> {
  await openFutureDay(page, monthsAhead, day)
  await page.getByRole('button', { name: new RegExp(`, ${String(hour).padStart(2, '0')}:00$`) }).click()
}

/**
 * selectOption({ label }) de Playwright exige una coincidencia EXACTA del texto
 * completo de la opcion (no acepta RegExp) -- no sirve cuando el texto incluye
 * datos variables (fecha, precio con formato de moneda). Busca la opcion por un
 * texto parcial y selecciona por su value real.
 */
async function selectByVisibleText(select: import('@playwright/test').Locator, text: string): Promise<void> {
  const value = await select.locator('option', { hasText: text }).first().getAttribute('value')
  if (!value) throw new Error(`No se encontro una opcion con el texto "${text}"`)
  await select.selectOption(value)
}

test.describe.configure({ mode: 'serial' })

test('flujo completo: paciente, cita, atencion, IA, odontograma, diagnostico, plan, consentimiento, pago, seguimiento', async ({
  page,
}) => {
  let patientUrl = ''

  await test.step('Recepcion: crear paciente', async () => {
    await login(page, 'recepcion@dentalcare-demo.mx')
    await page.getByRole('link', { name: 'Pacientes' }).click()
    await page.getByRole('button', { name: 'Nuevo paciente' }).click()

    await page.locator('#first_name').fill(PATIENT_FIRST_NAME)
    await page.locator('#last_name_paternal').fill(PATIENT_LAST_NAME)
    await page.locator('#date_of_birth').fill('1992-04-15')
    await page.getByRole('button', { name: 'Siguiente' }).click()

    // El nombre de prueba ("E2E Playwright<timestamp>") es parecido entre corridas
    // para pg_trgm (misma mayoria de n-gramas, solo cambian los digitos finales),
    // asi que el paso de "posibles duplicados" aparece casi siempre -- se maneja
    // de forma defensiva en vez de asumir que nunca aparece. isVisible() sin esperar
    // no sirve aqui: la pantalla todavia no existe en el momento del chequeo mientras
    // /patients/duplicates-check esta en vuelo, hay que esperarla con waitFor.
    const continueButton = page.getByRole('button', { name: 'Ninguno es el mismo paciente, continuar' })
    const appeared = await continueButton
      .waitFor({ state: 'visible', timeout: 10_000 })
      .then(() => true)
      .catch(() => false)
    if (appeared) {
      await continueButton.click()
    }

    // Sin contactos: continuar directo a crear el paciente.
    await page.getByRole('button', { name: 'Crear paciente' }).click()
    await expect(page).toHaveURL(/\/pacientes\/[0-9a-f-]+$/)
    patientUrl = page.url()
    await expect(page.getByText(`${PATIENT_FIRST_NAME} ${PATIENT_LAST_NAME}`)).toBeVisible()
  })

  await test.step('Recepcion: agendar cita', async () => {
    await page.getByRole('link', { name: 'Agenda' }).click()
    await openFutureDaySlot(page, CITA_MONTHS_AHEAD, CITA_DAY, CITA_HOUR)
    await page.getByLabel('Buscar paciente por nombre').fill(PATIENT_LAST_NAME)
    await page.getByRole('button', { name: new RegExp(PATIENT_LAST_NAME) }).click()
    await page.getByRole('button', { name: 'Agendar cita', exact: true }).click()

    await expect(page.getByRole('button', { name: new RegExp(`Cita de ${PATIENT_FIRST_NAME} ${PATIENT_LAST_NAME}`) })).toBeVisible()
    await logout(page)
  })

  await test.step('Odontologo: iniciar atencion desde la cita', async () => {
    await login(page, 'odontologo@dentalcare-demo.mx')
    await page.getByRole('link', { name: 'Agenda' }).click()
    await openFutureDay(page, CITA_MONTHS_AHEAD, CITA_DAY)

    await page.getByRole('button', { name: new RegExp(`Cita de ${PATIENT_FIRST_NAME} ${PATIENT_LAST_NAME}`) }).click()
    await page.getByRole('button', { name: 'Iniciar atencion' }).click()
    await expect(page).toHaveURL(/\/atencion\//)
  })

  await test.step('Odontologo: dictado IA (AI_FAKE_MODE) y aceptar propuestas', async () => {
    await page.getByPlaceholder('Transcripcion del dictado (editable)...').fill(
      'Paciente refiere dolor en muela inferior derecha. Signos vitales normales.',
    )
    await page.getByRole('button', { name: 'Interpretar dictado' }).click()

    // El fake Ollama (backend/app/ai/ollama_client.py) siempre produce estas dos
    // acciones, sin importar el texto dictado -- deterministico para el E2E.
    await expect(page.getByText('Motivo de consulta', { exact: true })).toBeVisible()
    await expect(page.getByText('Signos vitales', { exact: true })).toBeVisible()
    // "Aceptar todo" tambien matchea con nombre no-exacto; aceptar cada propuesta
    // por separado es lo que de verdad ejerce el flujo de "aceptar propuestas".
    const acceptButtons = page.getByRole('button', { name: 'Aceptar', exact: true })
    await expect(acceptButtons).toHaveCount(2)
    await acceptButtons.first().click()
    await expect(acceptButtons).toHaveCount(1)
    await acceptButtons.first().click()
    await expect(acceptButtons).toHaveCount(0)

    await expect(page.getByRole('heading', { name: /Dolor en muela inferior derecha/ })).toBeVisible()
  })

  await test.step('Odontologo: finalizar la nota clinica', async () => {
    await page.getByRole('button', { name: 'Finalizar nota' }).click()
    await expect(page.getByText('Finalizada')).toBeVisible()
  })

  let encounterUrl = ''

  await test.step('Odontologo: registrar hallazgo en el odontograma', async () => {
    encounterUrl = page.url()
    await page.goto(patientUrl)
    await page.getByRole('button', { name: 'Odontograma' }).click()

    const tooth = page.getByLabel('Pieza 36')
    await expect(tooth).toBeVisible()
    await tooth.locator('rect').nth(4).click({ force: true })

    await expect(page.getByRole('heading', { name: 'Pieza 36', exact: true })).toBeVisible()
    await page.getByRole('combobox').selectOption({ index: 1 })
    await page.getByRole('button', { name: 'Caries' }).click()
    await page.getByRole('button', { name: 'Registrar hallazgo' }).click()
    await expect(page.getByRole('heading', { name: 'Pieza 36', exact: true })).not.toBeVisible()
  })

  await test.step('Odontologo: registrar diagnostico', async () => {
    await page.getByRole('button', { name: 'Expediente' }).click()
    const diagnosisSection = page.locator('details', { has: page.getByText('Diagnosticos', { exact: true }) })
    await diagnosisSection.getByRole('combobox').first().selectOption({ index: 1 })
    await diagnosisSection.getByPlaceholder('Descripcion del diagnostico').fill('Caries en pieza 36, superficie oclusal')
    await diagnosisSection.getByRole('button', { name: 'Agregar diagnostico' }).click()
    await expect(diagnosisSection.getByText('Caries en pieza 36, superficie oclusal')).toBeVisible()
  })

  let planTitle = ''

  await test.step('Odontologo: crear plan de tratamiento y agregar procedimiento', async () => {
    await page.getByRole('button', { name: 'Tratamientos' }).click()
    await page.getByRole('button', { name: 'Nuevo plan' }).click()

    planTitle = `Plan ${RUN_ID}`
    await page.getByRole('combobox').selectOption({ index: 1 })
    await page.getByPlaceholder('Titulo del plan').fill(planTitle)
    await page.getByRole('button', { name: 'Crear plan' }).click()

    await expect(page.getByRole('heading', { name: planTitle })).toBeVisible()
    await page.getByRole('button', { name: 'Agregar fase' }).click()
    await page.getByPlaceholder('Nombre de la fase').fill('Fase unica')
    await page.getByRole('button', { name: 'Guardar fase' }).click()

    await page.getByRole('button', { name: 'Agregar procedimiento' }).click()
    await page.getByRole('combobox').nth(0).selectOption({ index: 1 })
    await selectByVisibleText(page.getByRole('combobox').nth(1), 'Resina')
    await page.getByPlaceholder('Pieza FDI (opcional)').fill('36')
    await page.getByRole('button', { name: 'Agregar procedimiento' }).click()
    await expect(page.getByText(/Resina/)).toBeVisible()
  })

  await test.step('Odontologo: presentar, aceptar y realizar el procedimiento del plan', async () => {
    await page.getByRole('button', { name: 'Presentar al paciente' }).click()
    await page.getByRole('button', { name: 'Aceptar presupuesto' }).click()
    await page.getByRole('checkbox').check()
    await page.getByPlaceholder('Nombre de quien acepta').fill(`${PATIENT_FIRST_NAME} ${PATIENT_LAST_NAME}`)
    await page.getByRole('button', { name: 'Confirmar aceptacion' }).click()

    await page.getByRole('button', { name: 'Iniciar progreso' }).click()
    await page.getByRole('button', { name: 'Marcar como realizado' }).click()
    await page.getByRole('button', { name: 'Confirmar' }).click()
    await expect(page.getByText('realizado')).toBeVisible()
  })

  await test.step('Odontologo: ver un formato existente y firmar', async () => {
    await page.getByRole('button', { name: 'Formatos' }).click()

    // "Plantillas" reemplaza a las antiguas "Plantillas de consentimiento" +
    // "Consentimientos firmados": un solo lugar que ve el documento ya
    // resuelto y lo firma. Acotar a este <details> evita mezclar sus propios
    // controles ("Atencion", comboboxes) con los de "Otros formatos clinicos".
    const plantillas = page.locator('details', {
      has: page.getByText('Plantillas', { exact: true }),
    })

    // Las categorias empiezan cerradas; se abren con su propia flecha. La de
    // "Consentimientos informados" tiene mas de 5 formatos, asi que se lista
    // en un select alfabetico en vez de un boton por formato.
    const categoria = plantillas.locator('details', {
      has: page.getByText(/^Consentimientos informados \(\d+\)$/),
    })
    await categoria.locator('summary').click()

    await plantillas.getByLabel('Atencion').selectOption({ index: 1 })
    await categoria.getByRole('combobox').selectOption({ label: 'Toma de radiografías' })

    // Sin "exact: true", la busqueda por texto no distingue mayusculas/minusculas
    // y tambien matchea la opcion "Toma de radiografías" del select de arriba.
    await expect(plantillas.getByText('TOMA DE RADIOGRAFÍAS', { exact: true })).toBeVisible()

    await plantillas
      .getByPlaceholder('Nombre de quien firma')
      .fill(`${PATIENT_FIRST_NAME} ${PATIENT_LAST_NAME}`)

    const canvas = plantillas.getByRole('img', { name: /Area para firmar/ })
    // page.mouse usa coordenadas absolutas del viewport y, a diferencia de
    // locator.click(), no hace scroll automatico -- sin esto el canvas puede
    // quedar fuera de pantalla y el trazo nunca llega al elemento correcto.
    // Coordenadas relativas al tamano real (ahora 7x7cm, cuadrado -- antes un
    // rectangulo ancho fijo) para no depender de un tamano en px concreto.
    await canvas.scrollIntoViewIfNeeded()
    const box = (await canvas.boundingBox())!
    await page.mouse.move(box.x + box.width * 0.15, box.y + box.height * 0.15)
    await page.mouse.down()
    await page.mouse.move(box.x + box.width * 0.55, box.y + box.height * 0.45)
    await page.mouse.move(box.x + box.width * 0.85, box.y + box.height * 0.25)
    await page.mouse.up()

    await plantillas.getByRole('button', { name: 'Imprimir / Generar PDF' }).click()
    await expect(
      plantillas.getByText(`${PATIENT_FIRST_NAME} ${PATIENT_LAST_NAME}`).first(),
    ).toBeVisible()
  })

  await test.step('Odontologo: agendar cita de seguimiento', async () => {
    await page.getByRole('link', { name: 'Agenda' }).click()
    await openFutureDaySlot(page, SEGUIMIENTO_MONTHS_AHEAD, SEGUIMIENTO_DAY, SEGUIMIENTO_HOUR)
    await page.getByLabel('Buscar paciente por nombre').fill(PATIENT_LAST_NAME)
    await page.getByRole('button', { name: new RegExp(PATIENT_LAST_NAME) }).click()
    await selectByVisibleText(page.getByLabel('Tipo de cita'), 'Control de ortodoncia')
    await page.getByRole('button', { name: 'Agendar cita', exact: true }).click()

    await expect(page.getByRole('button', { name: new RegExp(`Cita de ${PATIENT_FIRST_NAME} ${PATIENT_LAST_NAME}`) })).toBeVisible()
    await logout(page)
  })

  await test.step('Caja: registrar el pago del procedimiento realizado', async () => {
    await login(page, 'caja@dentalcare-demo.mx')
    await page.goto(patientUrl)
    await page.getByRole('button', { name: 'Cuenta' }).click()

    await expect(page.getByText('Resina').first()).toBeVisible()
    await page.getByPlaceholder('Monto recibido').fill('650')
    await page.getByRole('button', { name: 'Registrar pago' }).click()

    await expect(page.getByText('PAGADO')).toBeVisible()
    await logout(page)
  })
})
