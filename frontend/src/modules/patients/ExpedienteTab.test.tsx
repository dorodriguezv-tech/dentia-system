import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../auth/store'
import { ExpedienteTab } from './ExpedienteTab'

vi.mock('../encounters/api')
vi.mock('../records/api')
vi.mock('../diagnosis/api')
vi.mock('../catalogs/api')
vi.mock('../endodonticHistory/api')
vi.mock('./api')
import * as catalogsApi from '../catalogs/api'
import * as diagnosisApi from '../diagnosis/api'
import * as encountersApi from '../encounters/api'
import * as endoApi from '../endodonticHistory/api'
import * as recordsApi from '../records/api'
import type {
  PersonalNonPathologicalHistoryOut,
  PersonalPathologicalHistoryOut,
  SystemsReviewEntryOut,
} from '../records/types'
import * as patientsApi from './api'

function renderExpediente() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <ExpedienteTab patientId="pat-1" />
    </QueryClientProvider>,
  )
}

describe('ExpedienteTab', () => {
  beforeEach(() => {
    useAuthStore.setState({
      clinics: [
        {
          clinic: { id: 'clinic-1', name: 'Sucursal Centro' },
          role: { code: 'odontologo', name: 'Odontologo' },
        },
      ],
      activeClinicId: 'clinic-1',
    })

    vi.mocked(recordsApi.listAllergies).mockReset().mockResolvedValue([])
    vi.mocked(recordsApi.listMedications).mockReset().mockResolvedValue([])
    vi.mocked(recordsApi.listVitalSigns).mockReset().mockResolvedValue([])
    vi.mocked(diagnosisApi.listDiagnoses).mockReset().mockResolvedValue([])
    vi.mocked(recordsApi.createAllergy).mockReset()

    // Fase A (rediseno del expediente, docs/clinica): Historia Clinica General.
    vi.mocked(recordsApi.listFamilyHistory).mockReset().mockResolvedValue([])
    vi.mocked(recordsApi.createFamilyHistory).mockReset()
    vi.mocked(recordsApi.annulFamilyHistory).mockReset()
    vi.mocked(recordsApi.listPathologicalHistory).mockReset().mockResolvedValue([])
    vi.mocked(recordsApi.createPathologicalHistory).mockReset()
    vi.mocked(recordsApi.annulPathologicalHistory).mockReset()
    vi.mocked(recordsApi.listNonPathologicalHistory).mockReset().mockResolvedValue([])
    vi.mocked(recordsApi.createNonPathologicalHistory).mockReset()
    vi.mocked(recordsApi.annulNonPathologicalHistory).mockReset()
    vi.mocked(recordsApi.listSystemsReview).mockReset().mockResolvedValue([])
    vi.mocked(recordsApi.createSystemsReview).mockReset()
    vi.mocked(recordsApi.annulSystemsReview).mockReset()
    vi.mocked(recordsApi.getGeneralHistoryPdfBlobUrl).mockReset()

    // Fase F (rediseno del expediente, docs/clinica): Historia Clinica de
    // Endodoncia -- la sub-pestana ya no es un placeholder "Proximamente".
    vi.mocked(endoApi.listInterrogations).mockReset().mockResolvedValue([])
    vi.mocked(endoApi.listPulpSensitivityTests).mockReset().mockResolvedValue([])
    vi.mocked(endoApi.listPeriodontalTests).mockReset().mockResolvedValue([])
    vi.mocked(endoApi.listRadiographicInterpretations).mockReset().mockResolvedValue([])
    vi.mocked(endoApi.listDiagnosisTreatments).mockReset().mockResolvedValue([])
    vi.mocked(endoApi.listToothDiagnosisCodes).mockReset().mockResolvedValue([])
    vi.mocked(endoApi.listWorkingLengths).mockReset().mockResolvedValue([])
    vi.mocked(endoApi.getEndodonticHistoryPdfBlobUrl).mockReset()

    vi.mocked(catalogsApi.listCatalogItems).mockReset().mockResolvedValue([])

    vi.mocked(patientsApi.getPatient).mockReset().mockResolvedValue({
      id: 'pat-1',
      expediente_number: '000001',
      first_name: 'Juan',
      last_name_paternal: 'Perez',
      last_name_maternal: null,
      full_name: 'Juan Perez',
      date_of_birth: '1990-01-01',
      sex: 'M',
      phone: '5550001111',
      email: null,
      address: null,
      status: 'activo',
      has_photo: false,
      default_resource_id: null,
      primary_provider_id: null,
      birth_place: null,
      blood_type: null,
      education_level: null,
      can_read_write: null,
      religion: null,
      ethnic_group: null,
      race: null,
      occupation: null,
      marital_status: null,
    })
  })

  it('A3/A4: sin atenciones, el selector ofrece iniciar una y el boton de Agregar '
    + 'alergia funciona en dos clics', async () => {
    vi.mocked(encountersApi.listPatientEncounters).mockReset().mockResolvedValue([])
    vi.mocked(encountersApi.createEncounter).mockReset().mockResolvedValue({
      id: 'enc-nueva',
      patient_id: 'pat-1',
      professional_id: 'prof-1',
      appointment_id: null,
      chief_complaint: null,
      started_at: new Date().toISOString(),
      ended_at: null,
    })
    vi.mocked(recordsApi.createAllergy).mockResolvedValue({
      id: 'allergy-1',
      encounter_id: 'enc-nueva',
      substance: 'Penicilina',
      reaction: null,
      severity: 'leve',
      is_active: true,
      created_at: new Date().toISOString(),
    })

    renderExpediente()

    const selects = await screen.findAllByLabelText('Atencion')
    // Correccion Fase A (punto 2): el selector de atencion ya solo vive en Signos
    // vitales y Diagnosticos -- las demas secciones (p.ej. Alergias) comparten la
    // misma atencion activa en silencio, sin su propio selector.
    const vitalSignsSelect = selects[0] as HTMLSelectElement
    expect(
      Array.from(vitalSignsSelect.options).some((o) =>
        o.textContent?.includes('Iniciar atencion nueva'),
      ),
    ).toBe(true)

    // Clic 1: iniciar la atencion desde el selector de Signos vitales.
    await userEvent.selectOptions(
      vitalSignsSelect,
      within(vitalSignsSelect).getByText('+ Iniciar atencion nueva'),
    )
    await waitFor(() => expect(encountersApi.createEncounter).toHaveBeenCalledWith({ patient_id: 'pat-1' }))

    await userEvent.type(screen.getByPlaceholderText('Sustancia'), 'Penicilina')

    const addAllergyButton = screen.getByRole('button', { name: 'Agregar alergia' })
    await waitFor(() => expect(addAllergyButton).not.toBeDisabled())

    // Clic 2: Agregar alergia.
    await userEvent.click(addAllergyButton)
    await waitFor(() =>
      expect(recordsApi.createAllergy).toHaveBeenCalledWith('pat-1', {
        encounter_id: 'enc-nueva',
        substance: 'Penicilina',
        reaction: null,
        severity: 'leve',
      }),
    )
  })

  it('A3: si ya hay una atencion de hoy, se preselecciona sola', async () => {
    const todayIso = new Date().toISOString()
    vi.mocked(encountersApi.listPatientEncounters).mockReset().mockResolvedValue([
      {
        id: 'enc-hoy',
        patient_id: 'pat-1',
        professional_id: 'prof-1',
        appointment_id: null,
        chief_complaint: 'Dolor',
        started_at: todayIso,
        ended_at: null,
      },
    ])

    renderExpediente()

    const selects = await screen.findAllByLabelText('Atencion')
    await waitFor(() => expect((selects[0] as HTMLSelectElement).value).toBe('enc-hoy'))
  })

  it('A3: si la carga de atenciones falla, se muestra el error (no un selector vacio en silencio)', async () => {
    vi.mocked(encountersApi.listPatientEncounters).mockReset().mockRejectedValue(new Error('500'))

    renderExpediente()

    expect(
      await screen.findAllByText('No se pudieron cargar las atenciones del paciente.'),
    ).not.toHaveLength(0)
  })

  function mockTodaysEncounter() {
    vi.mocked(encountersApi.listPatientEncounters).mockReset().mockResolvedValue([
      {
        id: 'enc-hoy',
        patient_id: 'pat-1',
        professional_id: 'prof-1',
        appointment_id: null,
        chief_complaint: 'Dolor',
        started_at: new Date().toISOString(),
        ended_at: null,
      },
    ])
  }

  function catalogItem(
    catalogType: string,
    code: string,
    name: string,
    extra: Record<string, unknown> = {},
  ) {
    return {
      id: `${catalogType}-${code}`,
      catalog_type: catalogType,
      code,
      name,
      is_active: true,
      sort_order: 0,
      extra,
      updated_at: new Date().toISOString(),
    }
  }

  // Correcciones Fase A: factories para entradas ya guardadas, usadas en las
  // pruebas de vista detallada y del bug de reproductor masculino/femenino.
  function pathologicalEntry(
    overrides: Partial<PersonalPathologicalHistoryOut> = {},
  ): PersonalPathologicalHistoryOut {
    return {
      id: 'path-x',
      encounter_id: 'enc-hoy',
      dolor_masticar: false,
      sensibilidad_frio: false,
      sensibilidad_calor: false,
      sensibilidad_dulce: false,
      sensibilidad_localizacion: null,
      sangrado_encias: 'nunca',
      dolor_cepillado: false,
      aftas_ulceras: false,
      perdida_piezas: false,
      perdida_piezas_causa: null,
      anestesia_previa: false,
      extracciones: false,
      extracciones_texto: null,
      complicaciones_operatorias: false,
      complicaciones_operatorias_texto: null,
      traumatismo_dental: false,
      traumatismo_dental_texto: null,
      infecciones_dentales: false,
      infecciones_dentales_texto: null,
      estres: false,
      estres_texto: null,
      hospitalizacion_emergencia: false,
      hospitalizacion_emergencia_texto: null,
      infecciones_frecuentes: false,
      infecciones_frecuentes_zona: null,
      tiempo_evolucion: null,
      diseases: {},
      is_active: true,
      origin: 'MANUAL',
      created_at: new Date().toISOString(),
      ...overrides,
    }
  }

  function nonPathologicalEntry(
    overrides: Partial<PersonalNonPathologicalHistoryOut> = {},
  ): PersonalNonPathologicalHistoryOut {
    return {
      id: 'nonpath-x',
      encounter_id: 'enc-hoy',
      comidas_dia: null,
      calidad_alimentacion: null,
      agua_litros_dia: null,
      trastornos_sueno: false,
      trastornos_sueno_texto: null,
      cepillados_dia: null,
      hilo_dental: false,
      enjuague_bucal: false,
      deportes: false,
      deportes_cual: null,
      derechohabiencia: null,
      estado_civil: null,
      medicamentos_suplementos: false,
      medicamentos_controlados: false,
      medicamentos_texto: null,
      servicios_basicos: {},
      adicciones: {},
      is_active: true,
      origin: 'MANUAL',
      created_at: new Date().toISOString(),
      ...overrides,
    }
  }

  function systemsReviewEntry(
    overrides: Partial<SystemsReviewEntryOut> = {},
  ): SystemsReviewEntryOut {
    return {
      id: 'sr-x',
      encounter_id: 'enc-hoy',
      hematologico: {},
      cardiovascular: {},
      neurologico: {},
      endocrino: {},
      respiratorio: {},
      genitourinario: {},
      reproductor_masculino: {},
      reproductor_femenino: {},
      is_active: true,
      origin: 'MANUAL',
      created_at: new Date().toISOString(),
      ...overrides,
    }
  }

  describe('Fase A: Historia Clinica General (sub-pestanas nuevas)', () => {
    it('Fase F: la sub-pestana de Endodoncia muestra sus secciones (ya no es un placeholder)', async () => {
      mockTodaysEncounter()
      renderExpediente()

      await userEvent.click(
        screen.getByRole('button', { name: 'Historia Clínica de Endodoncia' }),
      )
      expect(screen.getByText('Interrogatorio')).toBeInTheDocument()
      expect(screen.getByText('Pruebas de sensibilidad pulpar')).toBeInTheDocument()
      expect(
        screen.getByText('Odontograma de diagnóstico y evolución (18 códigos)'),
      ).toBeInTheDocument()
    })

    it('autollena los Datos generales desde el Patient', async () => {
      mockTodaysEncounter()
      renderExpediente()

      expect(await screen.findByText('Juan Perez')).toBeInTheDocument()
      expect(screen.getByText('5550001111')).toBeInTheDocument()
    })

    it('captura un antecedente heredofamiliar (parentesco + condicion del catalogo)', async () => {
      mockTodaysEncounter()
      vi.mocked(catalogsApi.listCatalogItems).mockImplementation(async (catalogType) => {
        if (catalogType === 'family_relationship') {
          return [catalogItem('family_relationship', 'padre', 'Padre')]
        }
        if (catalogType === 'family_condition') {
          return [catalogItem('family_condition', 'diabetes_mellitus', 'Diabetes mellitus')]
        }
        return []
      })
      vi.mocked(recordsApi.createFamilyHistory).mockResolvedValue({
        id: 'fam-1',
        encounter_id: 'enc-hoy',
        relationship_code: 'padre',
        status: 'en_vida',
        conditions: { diabetes_mellitus: true },
        is_active: true,
        origin: 'MANUAL',
        created_at: new Date().toISOString(),
      })

      renderExpediente()

      const relationshipSelect = await screen.findByLabelText('Parentesco')
      await screen.findByRole('option', { name: 'Padre' })
      await userEvent.selectOptions(relationshipSelect, 'padre')
      await userEvent.click(screen.getByRole('checkbox', { name: 'Diabetes mellitus' }))
      await userEvent.click(
        screen.getByRole('button', { name: 'Agregar antecedente heredofamiliar' }),
      )

      await waitFor(() =>
        expect(recordsApi.createFamilyHistory).toHaveBeenCalledWith('pat-1', {
          encounter_id: 'enc-hoy',
          relationship_code: 'padre',
          status: 'en_vida',
          conditions: { diabetes_mellitus: true },
        }),
      )
    })

    it('captura un antecedente personal patologico (booleano + enfermedad del catalogo)', async () => {
      mockTodaysEncounter()
      vi.mocked(catalogsApi.listCatalogItems).mockImplementation(async (catalogType) => {
        if (catalogType === 'pathological_condition') {
          return [catalogItem('pathological_condition', 'diabetes', 'Diabetes')]
        }
        return []
      })
      vi.mocked(recordsApi.createPathologicalHistory).mockResolvedValue({
        id: 'path-1',
        encounter_id: 'enc-hoy',
      } as never)

      renderExpediente()

      await userEvent.click(await screen.findByRole('checkbox', { name: 'Dolor al masticar' }))
      await userEvent.click(screen.getByRole('checkbox', { name: 'Diabetes' }))
      await userEvent.click(
        screen.getByRole('button', { name: 'Agregar antecedente patológico' }),
      )

      await waitFor(() =>
        expect(recordsApi.createPathologicalHistory).toHaveBeenCalledWith(
          'pat-1',
          expect.objectContaining({
            encounter_id: 'enc-hoy',
            dolor_masticar: true,
            diseases: { diabetes: { present: true } },
          }),
        ),
      )
    })

    it('captura un antecedente personal no patologico (servicio basico)', async () => {
      mockTodaysEncounter()
      vi.mocked(recordsApi.createNonPathologicalHistory).mockResolvedValue({
        id: 'nonpath-1',
      } as never)

      renderExpediente()

      await userEvent.click(await screen.findByRole('checkbox', { name: 'Agua' }))
      await userEvent.click(
        screen.getByRole('button', { name: 'Agregar antecedente no patológico' }),
      )

      await waitFor(() =>
        expect(recordsApi.createNonPathologicalHistory).toHaveBeenCalledWith(
          'pat-1',
          expect.objectContaining({
            encounter_id: 'enc-hoy',
            servicios_basicos: { agua: { has: true } },
          }),
        ),
      )
    })

    it('captura el interrogatorio por aparatos y sistemas (hallazgo del catalogo)', async () => {
      mockTodaysEncounter()
      vi.mocked(catalogsApi.listCatalogItems).mockImplementation(async (catalogType) => {
        if (catalogType === 'systems_review_finding') {
          return [catalogItem('systems_review_finding', 'anemia', 'Anemia', { system: 'hematologico' })]
        }
        return []
      })
      vi.mocked(recordsApi.createSystemsReview).mockResolvedValue({ id: 'sr-1' } as never)

      renderExpediente()

      await userEvent.click(await screen.findByRole('checkbox', { name: 'Anemia' }))
      await userEvent.click(
        screen.getByRole('button', { name: 'Agregar interrogatorio por aparatos y sistemas' }),
      )

      await waitFor(() =>
        expect(recordsApi.createSystemsReview).toHaveBeenCalledWith(
          'pat-1',
          expect.objectContaining({
            encounter_id: 'enc-hoy',
            hematologico: { anemia: { present: true } },
          }),
        ),
      )
    })

    it('captura talla y peso en signos vitales y calcula el IMC en vivo', async () => {
      mockTodaysEncounter()
      vi.mocked(recordsApi.createVitalSigns).mockResolvedValue({ id: 'vs-1' } as never)

      renderExpediente()

      await userEvent.type(await screen.findByPlaceholderText('Talla (m)'), '1.70')
      await userEvent.type(screen.getByPlaceholderText('Peso (kg)'), '70')

      expect(await screen.findByText('IMC calculado: 24.2')).toBeInTheDocument()

      await userEvent.click(screen.getByRole('button', { name: 'Agregar signos vitales' }))

      await waitFor(() =>
        expect(recordsApi.createVitalSigns).toHaveBeenCalledWith(
          'pat-1',
          expect.objectContaining({
            encounter_id: 'enc-hoy',
            height_m: 1.7,
            weight_kg: 70,
          }),
        ),
      )
    })
  })

  describe('Correcciones Fase A (ronda de ajustes sobre el expediente)', () => {
    it('punto 1: ya no existe el formulario viejo de "Antecedentes" (HistorySection)', async () => {
      mockTodaysEncounter()
      renderExpediente()

      await screen.findByText('Juan Perez')
      expect(screen.queryByText('Antecedentes')).not.toBeInTheDocument()
      expect(screen.queryByLabelText('Categoria del antecedente')).not.toBeInTheDocument()
    })

    it('punto 2: Alergias ya no tiene su propio selector de atencion', async () => {
      mockTodaysEncounter()
      renderExpediente()

      await screen.findByText('Juan Perez')
      // Solo Signos vitales y Diagnosticos conservan el selector de atencion.
      expect(await screen.findAllByLabelText('Atencion')).toHaveLength(2)
    })

    it('punto 3: "Ninguna" es mutuamente excluyente con el checklist de Enfermedades', async () => {
      mockTodaysEncounter()
      vi.mocked(catalogsApi.listCatalogItems).mockImplementation(async (catalogType) => {
        if (catalogType === 'pathological_condition') {
          return [catalogItem('pathological_condition', 'diabetes', 'Diabetes')]
        }
        return []
      })
      renderExpediente()

      // Espera a que cargue el catalogo (Diabetes) antes de listar los checkbox
      // "Ninguna" -- tambien hay uno en Adicciones (NonPathologicalHistorySection),
      // que no depende del catalogo y aparece de inmediato. El checklist de
      // Enfermedades (Pathological) se renderiza antes en el DOM.
      const diabetes = await screen.findByRole('checkbox', { name: 'Diabetes' })
      const ningunaEnfermedades = screen.getAllByRole('checkbox', { name: 'Ninguna' })[0]

      await userEvent.click(ningunaEnfermedades)
      expect(ningunaEnfermedades).toBeChecked()

      await userEvent.click(diabetes)
      expect(ningunaEnfermedades).not.toBeChecked()
      expect(diabetes).toBeChecked()
    })

    it('punto 4: estado civil "Otro" envia el texto libre tecleado', async () => {
      mockTodaysEncounter()
      vi.mocked(recordsApi.createNonPathologicalHistory).mockResolvedValue(
        nonPathologicalEntry(),
      )

      renderExpediente()

      await userEvent.selectOptions(
        await screen.findByLabelText('Estado civil (no patológico)'),
        'otro',
      )
      await userEvent.type(
        screen.getByLabelText('Estado civil: cual otro'),
        'Separado de hecho',
      )
      await userEvent.click(
        screen.getByRole('button', { name: 'Agregar antecedente no patológico' }),
      )

      await waitFor(() =>
        expect(recordsApi.createNonPathologicalHistory).toHaveBeenCalledWith(
          'pat-1',
          expect.objectContaining({ estado_civil: 'Separado de hecho' }),
        ),
      )
    })

    it('punto 5: "Comidas al dia"/"Cepillados al dia" llevan step=1 -- un valor decimal '
      + 'queda invalido (stepMismatch) y el navegador bloquea el envio antes de llegar '
      + 'al backend, en vez de disparar el 422 "datos de entrada invalidos"', async () => {
      mockTodaysEncounter()
      vi.mocked(recordsApi.createNonPathologicalHistory).mockResolvedValue(
        nonPathologicalEntry(),
      )

      renderExpediente()

      const comidasInput = (await screen.findByPlaceholderText(
        'Comidas al día',
      )) as HTMLInputElement
      const cepilladosInput = screen.getByPlaceholderText('Cepillados al día') as HTMLInputElement
      expect(comidasInput).toHaveAttribute('step', '1')
      expect(cepilladosInput).toHaveAttribute('step', '1')

      await userEvent.type(comidasInput, '2.5')
      expect(comidasInput.validity.stepMismatch).toBe(true)

      await userEvent.click(
        screen.getByRole('button', { name: 'Agregar antecedente no patológico' }),
      )

      // La constraint-validation nativa del formulario bloquea el submit -- la
      // mutacion nunca llega a dispararse con un valor no entero.
      expect(recordsApi.createNonPathologicalHistory).not.toHaveBeenCalled()
    })

    it('punto 5: "Comidas al dia" con un entero valido si envia (regresion: la '
      + 'correccion no bloquea el flujo normal)', async () => {
      mockTodaysEncounter()
      vi.mocked(recordsApi.createNonPathologicalHistory).mockResolvedValue(
        nonPathologicalEntry(),
      )

      renderExpediente()

      await userEvent.type(await screen.findByPlaceholderText('Comidas al día'), '5')
      await userEvent.click(
        screen.getByRole('button', { name: 'Agregar antecedente no patológico' }),
      )

      await waitFor(() =>
        expect(recordsApi.createNonPathologicalHistory).toHaveBeenCalledWith(
          'pat-1',
          expect.objectContaining({ comidas_dia: 5 }),
        ),
      )
    })

    it('punto 6/7: la vista guardada de Interrogatorio muestra reproductor masculino/femenino '
      + '(bug confirmado: antes no aparecian)', async () => {
      mockTodaysEncounter()
      vi.mocked(recordsApi.listSystemsReview).mockResolvedValue([
        systemsReviewEntry({
          reproductor_masculino: { examen_prostata: true },
          reproductor_femenino: { menarca: '12 años' },
        }),
      ])

      renderExpediente()

      // "Examen de prostata"/"Menarca" tambien son la etiqueta del campo en el
      // formulario de captura (abierto en la misma seccion) -- se busca
      // especificamente el <dt> de la vista detallada de la entrada guardada.
      // Espera a que la entrada guardada (asincrona) este en pantalla antes de
      // revisar las etiquetas -- si no, "Examen de prostata" ya hace match con
      // la etiqueta del formulario (siempre presente de inmediato) y la
      // asercion de abajo se evaluaria antes de tiempo.
      await screen.findByText('12 años')

      const prostataMatches = screen.getAllByText('Examen de próstata')
      expect(prostataMatches.some((el) => el.tagName === 'DT')).toBe(true)
      const menarcaMatches = screen.getAllByText('Menarca')
      expect(menarcaMatches.some((el) => el.tagName === 'DT')).toBe(true)
    })

    it('punto 6: la vista guardada de Patologicos muestra todos los campos capturados, '
      + 'no solo sangrado de encias y enfermedades', async () => {
      mockTodaysEncounter()
      vi.mocked(recordsApi.listPathologicalHistory).mockResolvedValue([
        pathologicalEntry({ dolor_masticar: true, estres: true, estres_texto: 'Examenes' }),
      ])

      renderExpediente()

      // Espera a que la entrada guardada (asincrona) este en pantalla antes de
      // revisar las etiquetas duplicadas (formulario vs. vista detallada).
      await screen.findByText('Examenes')

      const dolorMatches = screen.getAllByText('Dolor al masticar')
      expect(dolorMatches.some((el) => el.tagName === 'DT')).toBe(true)
      const estresMatches = screen.getAllByText('Estrés')
      expect(estresMatches.some((el) => el.tagName === 'DT')).toBe(true)
    })

    it('punto 9: el indice de glucosa es obligatorio solo si hay diabetes activa', async () => {
      mockTodaysEncounter()
      vi.mocked(recordsApi.listPathologicalHistory).mockResolvedValue([
        pathologicalEntry({ diseases: { diabetes: { present: true } } }),
      ])

      renderExpediente()

      const glucoseInput = await screen.findByPlaceholderText('Indice de glucosa')
      await waitFor(() => expect(glucoseInput).toBeRequired())
      expect(
        screen.getByText('Paciente con diabetes: registra el índice de glucosa.'),
      ).toBeInTheDocument()
    })

    it('punto 9: el indice de glucosa sigue siendo opcional sin diabetes activa', async () => {
      mockTodaysEncounter()
      vi.mocked(recordsApi.listPathologicalHistory).mockResolvedValue([])

      renderExpediente()

      const glucoseInput = await screen.findByPlaceholderText('Indice de glucosa')
      expect(glucoseInput).not.toBeRequired()
    })

    it('punto 10: "Faltan datos" aparece cuando las 6 secciones sin picker propio '
      + 'tienen cero entradas activas (el mock por defecto de beforeEach)', async () => {
      mockTodaysEncounter()
      renderExpediente()

      await screen.findByText('Juan Perez')
      // Heredofamiliares, Patologicos, No patologicos, Interrogatorio, Alergias y
      // Medicamentos -- las 6 secciones del punto 10, todas sin datos por defecto.
      expect(await screen.findAllByText('Faltan datos')).toHaveLength(6)
      // Signos vitales y Diagnosticos nunca llevan el indicador.
      expect(
        screen.getByText('Signos vitales y exploración física').textContent,
      ).not.toContain('Faltan datos')
      expect(screen.getByText('Diagnosticos').textContent).not.toContain('Faltan datos')
    })

    it('punto 10: el indicador desaparece en Alergias en cuanto hay una entrada activa', async () => {
      mockTodaysEncounter()
      vi.mocked(recordsApi.listAllergies).mockResolvedValue([
        {
          id: 'allergy-1',
          encounter_id: 'enc-hoy',
          substance: 'Penicilina',
          reaction: null,
          severity: 'leve',
          is_active: true,
          created_at: new Date().toISOString(),
        },
      ])

      renderExpediente()

      await screen.findByText('Penicilina', { exact: false })
      // Las otras 5 secciones (sin la de Alergias) siguen sin datos.
      expect(await screen.findAllByText('Faltan datos')).toHaveLength(5)
    })

    it('punto 11: Heredofamiliares, Alergias y Medicamentos muestran la fecha de captura', async () => {
      mockTodaysEncounter()
      const now = new Date().toISOString()
      vi.mocked(catalogsApi.listCatalogItems).mockImplementation(async (catalogType) => {
        if (catalogType === 'family_relationship') {
          return [catalogItem('family_relationship', 'padre', 'Padre')]
        }
        return []
      })
      vi.mocked(recordsApi.listFamilyHistory).mockResolvedValue([
        {
          id: 'fam-1',
          encounter_id: 'enc-hoy',
          relationship_code: 'padre',
          status: 'en_vida',
          conditions: {},
          is_active: true,
          origin: 'MANUAL',
          created_at: now,
        },
      ])
      vi.mocked(recordsApi.listAllergies).mockResolvedValue([
        {
          id: 'allergy-1',
          encounter_id: 'enc-hoy',
          substance: 'Penicilina',
          reaction: null,
          severity: 'leve',
          is_active: true,
          created_at: now,
        },
      ])
      vi.mocked(recordsApi.listMedications).mockResolvedValue([
        {
          id: 'med-1',
          encounter_id: 'enc-hoy',
          name: 'Ibuprofeno',
          dose: null,
          frequency: null,
          is_active: true,
          created_at: now,
        },
      ])

      renderExpediente()

      const expectedDate = new Date(now).toLocaleString('es-MX')
      await waitFor(() =>
        expect(screen.getAllByText(expectedDate, { exact: false }).length).toBeGreaterThanOrEqual(3),
      )
    })
  })
})
