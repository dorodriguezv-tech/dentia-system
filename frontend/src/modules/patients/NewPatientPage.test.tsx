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
})
