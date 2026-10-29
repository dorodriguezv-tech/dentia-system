import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NewPatientPage } from './NewPatientPage'

vi.mock('./api')
vi.mock('../agenda/api')
import * as agendaApi from '../agenda/api'
import * as api from './api'

function renderWizard(initialPath = '/pacientes/nuevo') {
  const queryClient = new QueryClient()
  const router = createMemoryRouter(
    [
      { path: '/pacientes/nuevo', element: <NewPatientPage /> },
      { path: '/pacientes/:id', element: <div>Ficha del paciente</div> },
      { path: '/pacientes', element: <div>Listado de pacientes</div> },
    ],
    { initialEntries: [initialPath] },
  )
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

async function fillRequiredFields() {
  await userEvent.type(screen.getByLabelText('Nombre(s)'), 'Jose')
  await userEvent.type(screen.getByLabelText('Apellido paterno'), 'Perez')
  const dob = screen.getByLabelText('Fecha de nacimiento')
  await userEvent.type(dob, '1990-05-20')
}

describe('NewPatientPage', () => {
  beforeEach(() => {
    vi.mocked(api.checkDuplicates).mockReset()
    vi.mocked(api.createPatient).mockReset()
    vi.mocked(api.createContact).mockReset()
    vi.mocked(agendaApi.listProviders).mockReset().mockResolvedValue([])
    vi.mocked(agendaApi.listResources).mockReset().mockResolvedValue([])
  })

  it('prellena nombre y telefono cuando Dentia abre el alta rapida (13.4)', async () => {
    renderWizard('/pacientes/nuevo?first_name=Pedro&last_name_paternal=Sanchez&phone=5551234567')

    expect(screen.getByLabelText('Nombre(s)')).toHaveValue('Pedro')
    expect(screen.getByLabelText('Apellido paterno')).toHaveValue('Sanchez')
    expect(screen.getByLabelText('Telefono')).toHaveValue('5551234567')
  })

  it('exige confirmar cuando hay posibles duplicados antes de poder crear', async () => {
    vi.mocked(api.checkDuplicates).mockResolvedValue([
      {
        id: 'p1',
        expediente_number: '000001',
        full_name: 'Jose Perez Gomez',
        date_of_birth: '1990-05-20',
        phone: null,
        similarity: 0.9,
      },
    ])

    renderWizard()
    await fillRequiredFields()
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))

    expect(await screen.findByText('2. Posibles duplicados', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('Jose Perez Gomez', { exact: false })).toBeInTheDocument()
    expect(screen.queryByText('Crear paciente')).not.toBeInTheDocument()

    await userEvent.click(
      screen.getByRole('button', { name: 'Ninguno es el mismo paciente, continuar' }),
    )

    expect(await screen.findByRole('button', { name: 'Crear paciente' })).toBeInTheDocument()
  })

  it('salta directo a contactos cuando no hay duplicados', async () => {
    vi.mocked(api.checkDuplicates).mockResolvedValue([])

    renderWizard()
    await fillRequiredFields()
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))

    expect(await screen.findByRole('button', { name: 'Crear paciente' })).toBeInTheDocument()
  })

  it('crea el paciente y navega a su ficha', async () => {
    vi.mocked(api.checkDuplicates).mockResolvedValue([])
    vi.mocked(api.createPatient).mockResolvedValue({
      id: 'new-id',
      expediente_number: '000002',
      first_name: 'Jose',
      last_name_paternal: 'Perez',
      last_name_maternal: null,
      full_name: 'Jose Perez',
      date_of_birth: '1990-05-20',
      sex: null,
      phone: null,
      email: null,
      address: null,
      status: 'activo',
      has_photo: false,
      default_resource_id: null,
      primary_provider_id: null,
    })

    renderWizard()
    await fillRequiredFields()
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Crear paciente' }))

    await waitFor(() => expect(screen.getByText('Ficha del paciente')).toBeInTheDocument())
    expect(api.createPatient).toHaveBeenCalledWith(
      expect.objectContaining({ first_name: 'Jose', last_name_paternal: 'Perez' }),
    )
  })

  it('permite elegir un gabinete y un profesional tratante por defecto desde el alta (B3)', async () => {
    vi.mocked(agendaApi.listProviders).mockResolvedValue([
      { id: 'prov-1', user_id: 'u1', full_name: 'Dra. Gomez', color: '#2bb3a3', is_active: true, default_resource_id: null },
    ])
    vi.mocked(agendaApi.listResources).mockResolvedValue([
      { id: 'res-1', name: 'Gabinete 1', is_active: true },
    ])
    vi.mocked(api.checkDuplicates).mockResolvedValue([])
    vi.mocked(api.createPatient).mockResolvedValue({
      id: 'new-id',
      expediente_number: '000002',
      first_name: 'Jose',
      last_name_paternal: 'Perez',
      last_name_maternal: null,
      full_name: 'Jose Perez',
      date_of_birth: '1990-05-20',
      sex: null,
      phone: null,
      email: null,
      address: null,
      status: 'activo',
      has_photo: false,
      default_resource_id: 'res-1',
      primary_provider_id: 'prov-1',
    })

    renderWizard()
    await fillRequiredFields()
    await userEvent.selectOptions(
      await screen.findByLabelText('Profesional tratante (opcional)'),
      'prov-1',
    )
    await userEvent.selectOptions(screen.getByLabelText('Gabinete por defecto (opcional)'), 'res-1')
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Crear paciente' }))

    await waitFor(() =>
      expect(api.createPatient).toHaveBeenCalledWith(
        expect.objectContaining({
          primary_provider_id: 'prov-1',
          default_resource_id: 'res-1',
        }),
      ),
    )
  })

  it('captura los datos adicionales de la Historia Clínica General (Fase A)', async () => {
    vi.mocked(api.checkDuplicates).mockResolvedValue([])
    vi.mocked(api.createPatient).mockResolvedValue({
      id: 'new-id',
      expediente_number: '000002',
      first_name: 'Jose',
      last_name_paternal: 'Perez',
      last_name_maternal: null,
      full_name: 'Jose Perez',
      date_of_birth: '1990-05-20',
      sex: null,
      phone: null,
      email: null,
      address: null,
      status: 'activo',
      has_photo: false,
      default_resource_id: null,
      primary_provider_id: null,
    })

    renderWizard()
    await fillRequiredFields()
    await userEvent.type(screen.getByLabelText('Lugar de nacimiento'), 'Ciudad de Mexico')
    await userEvent.type(screen.getByLabelText('Tipo sanguíneo'), 'O+')
    await userEvent.selectOptions(screen.getByLabelText('Sabe leer y escribir'), 'true')
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Crear paciente' }))

    await waitFor(() =>
      expect(api.createPatient).toHaveBeenCalledWith(
        expect.objectContaining({
          birth_place: 'Ciudad de Mexico',
          blood_type: 'O+',
          can_read_write: true,
        }),
      ),
    )
  })

  it('muestra la vista previa de tipo de paciente segun la fecha de nacimiento y ayuda de telefono/correo opcionales para pediatricos', async () => {
    renderWizard()
    await userEvent.type(screen.getByLabelText('Nombre(s)'), 'Jose')
    await userEvent.type(screen.getByLabelText('Apellido paterno'), 'Perez')
    const dob = screen.getByLabelText('Fecha de nacimiento')

    await userEvent.type(dob, '1990-05-20')
    expect(screen.getByText('Calcular automáticamente (Adulto)')).toBeInTheDocument()
    expect(screen.queryByText(/Opcional para pacientes pediátricos/)).not.toBeInTheDocument()

    await userEvent.clear(dob)
    const recentDob = new Date()
    recentDob.setFullYear(recentDob.getFullYear() - 5)
    await userEvent.type(dob, recentDob.toISOString().slice(0, 10))

    expect(screen.getByText('Calcular automáticamente (Pediátrico)')).toBeInTheDocument()
    expect(screen.getAllByText(/Opcional para pacientes pediátricos/).length).toBeGreaterThan(0)
  })

  it('envia patient_type null cuando se deja "Calcular automaticamente"', async () => {
    vi.mocked(api.checkDuplicates).mockResolvedValue([])
    vi.mocked(api.createPatient).mockResolvedValue({
      id: 'new-id',
      expediente_number: '000002',
      first_name: 'Jose',
      last_name_paternal: 'Perez',
      last_name_maternal: null,
      full_name: 'Jose Perez',
      date_of_birth: '1990-05-20',
      sex: null,
      phone: null,
      email: null,
      address: null,
      status: 'activo',
      has_photo: false,
      default_resource_id: null,
      primary_provider_id: null,
    })

    renderWizard()
    await fillRequiredFields()
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Crear paciente' }))

    await waitFor(() =>
      expect(api.createPatient).toHaveBeenCalledWith(
        expect.objectContaining({ patient_type: null }),
      ),
    )
  })

  it('respeta el tipo de paciente elegido a mano, sin importar la fecha de nacimiento', async () => {
    vi.mocked(api.checkDuplicates).mockResolvedValue([])
    vi.mocked(api.createPatient).mockResolvedValue({
      id: 'new-id',
      expediente_number: '000002',
      first_name: 'Jose',
      last_name_paternal: 'Perez',
      last_name_maternal: null,
      full_name: 'Jose Perez',
      date_of_birth: '1990-05-20',
      sex: null,
      patient_type: 'pediatrico',
      phone: null,
      email: null,
      address: null,
      status: 'activo',
      has_photo: false,
      default_resource_id: null,
      primary_provider_id: null,
    })

    renderWizard()
    await fillRequiredFields()
    await userEvent.selectOptions(screen.getByLabelText('Tipo de paciente'), 'pediatrico')
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    // Pediatrico: el paso de contactos ahora exige un tutor con nombre y telefono
    // antes de poder crear el paciente (ver pruebas dedicadas mas abajo).
    await screen.findByRole('button', { name: 'Crear paciente' })
    await userEvent.type(screen.getByLabelText('Nombre'), 'Mama de Jose')
    await userEvent.type(screen.getByLabelText('Telefono'), '5551112222')
    await userEvent.click(screen.getByRole('button', { name: 'Agregar contacto' }))
    await userEvent.click(screen.getByRole('button', { name: 'Crear paciente' }))

    await waitFor(() =>
      expect(api.createPatient).toHaveBeenCalledWith(
        expect.objectContaining({ patient_type: 'pediatrico' }),
      ),
    )
  })

  it('oculta Ocupacion y Estado civil del paciente cuando es pediatrico', async () => {
    renderWizard()
    await userEvent.type(screen.getByLabelText('Nombre(s)'), 'Jose')
    await userEvent.type(screen.getByLabelText('Apellido paterno'), 'Perez')
    const dob = screen.getByLabelText('Fecha de nacimiento')
    const recentDob = new Date()
    recentDob.setFullYear(recentDob.getFullYear() - 5)
    await userEvent.type(dob, recentDob.toISOString().slice(0, 10))

    expect(screen.queryByLabelText('Ocupación')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Estado civil')).not.toBeInTheDocument()
  })

  it('no oculta Ocupacion ni Estado civil para un paciente adulto', async () => {
    renderWizard()
    await fillRequiredFields()

    expect(screen.getByLabelText('Ocupación')).toBeInTheDocument()
    expect(screen.getByLabelText('Estado civil')).toBeInTheDocument()
  })

  it('exige un contacto tutor con nombre y telefono antes de crear un paciente pediatrico', async () => {
    vi.mocked(api.checkDuplicates).mockResolvedValue([])

    renderWizard()
    await userEvent.type(screen.getByLabelText('Nombre(s)'), 'Jose')
    await userEvent.type(screen.getByLabelText('Apellido paterno'), 'Perez')
    const dob = screen.getByLabelText('Fecha de nacimiento')
    const recentDob = new Date()
    recentDob.setFullYear(recentDob.getFullYear() - 5)
    await userEvent.type(dob, recentDob.toISOString().slice(0, 10))
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))

    const createButton = await screen.findByRole('button', { name: 'Crear paciente' })
    expect(createButton).toBeDisabled()
    expect(
      screen.getByText('Agrega al menos un contacto responsable (tutor/pariente) con nombre y teléfono.'),
    ).toBeInTheDocument()

    // El tipo de contacto ya viene preseleccionado como "Tutor o responsable".
    expect(screen.getByLabelText('Tipo')).toHaveValue('guardian')

    await userEvent.type(screen.getByLabelText('Nombre'), 'Mama de Jose')
    await userEvent.type(screen.getByLabelText('Telefono'), '5551112222')
    await userEvent.click(screen.getByRole('button', { name: 'Agregar contacto' }))

    expect(createButton).not.toBeDisabled()
    expect(
      screen.queryByText('Agrega al menos un contacto responsable (tutor/pariente) con nombre y teléfono.'),
    ).not.toBeInTheDocument()
  })

  it('crea el paciente pediatrico con la ocupacion del tutor capturada en Contactos', async () => {
    vi.mocked(api.checkDuplicates).mockResolvedValue([])
    vi.mocked(api.createPatient).mockResolvedValue({
      id: 'new-id',
      expediente_number: '000003',
      first_name: 'Jose',
      last_name_paternal: 'Perez',
      last_name_maternal: null,
      full_name: 'Jose Perez',
      date_of_birth: '2021-01-01',
      sex: null,
      patient_type: 'pediatrico',
      phone: null,
      email: null,
      address: null,
      status: 'activo',
      has_photo: false,
      default_resource_id: null,
      primary_provider_id: null,
    })

    renderWizard()
    await userEvent.type(screen.getByLabelText('Nombre(s)'), 'Jose')
    await userEvent.type(screen.getByLabelText('Apellido paterno'), 'Perez')
    await userEvent.selectOptions(screen.getByLabelText('Tipo de paciente'), 'pediatrico')
    const dob = screen.getByLabelText('Fecha de nacimiento')
    await userEvent.type(dob, '2021-01-01')
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))

    await screen.findByRole('button', { name: 'Crear paciente' })
    await userEvent.type(screen.getByLabelText('Nombre'), 'Mama de Jose')
    await userEvent.type(screen.getByLabelText('Telefono'), '5551112222')
    await userEvent.type(screen.getByLabelText('Ocupación'), 'Enfermera')
    await userEvent.click(screen.getByRole('button', { name: 'Agregar contacto' }))
    await userEvent.click(screen.getByRole('button', { name: 'Crear paciente' }))

    await waitFor(() =>
      expect(api.createContact).toHaveBeenCalledWith(
        'new-id',
        expect.objectContaining({
          role: 'guardian',
          full_name: 'Mama de Jose',
          phone: '5551112222',
          occupation: 'Enfermera',
        }),
      ),
    )
    expect(api.createPatient).toHaveBeenCalledWith(
      expect.objectContaining({ occupation: null, marital_status: null }),
    )
  })
})
