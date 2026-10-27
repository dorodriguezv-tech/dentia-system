import { QueryClientProvider } from '@tanstack/react-query'
import { QueryClient } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from '../../api/client'
import { ErrorToast } from '../../app/ErrorToast'
import { createGlobalMutationCache } from '../../app/globalMutationErrorHandling'
import { useAuthStore } from '../auth/store'
import { ResumenTab } from './ResumenTab'

vi.mock('../agenda/api')
vi.mock('../encounters/api')
vi.mock('./api')
import * as agendaApi from '../agenda/api'
import * as encountersApi from '../encounters/api'
import * as api from './api'

function renderResumen() {
  const queryClient = new QueryClient({ mutationCache: createGlobalMutationCache() })
  render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <ResumenTab patientId="pat-1" />
        <ErrorToast />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('ResumenTab: Iniciar atencion (A4)', () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: 'token',
      activeClinicId: 'clinic-1',
      clinics: [
        {
          clinic: { id: 'clinic-1', name: 'Sucursal Centro' },
          role: { code: 'odontologo', name: 'Odontologo' },
        },
      ],
    })

    vi.mocked(api.getPatient).mockReset().mockResolvedValue({
      id: 'pat-1',
      expediente_number: '000001',
      first_name: 'Juan',
      last_name_paternal: 'Perez',
      last_name_maternal: null,
      full_name: 'Juan Perez',
      date_of_birth: '1990-01-01',
      sex: null,
      phone: null,
      email: null,
      address: null,
      status: 'activo',
      has_photo: false,
      default_resource_id: null,
      primary_provider_id: null,
    })
    vi.mocked(api.listContacts).mockReset().mockResolvedValue([])
    vi.mocked(encountersApi.getPatientTimeline).mockReset().mockResolvedValue([])
    vi.mocked(agendaApi.listProviders).mockReset().mockResolvedValue([
      { id: 'prov-1', user_id: 'u1', full_name: 'Dra. Gomez', color: '#2bb3a3', is_active: true, default_resource_id: null },
    ])
    vi.mocked(agendaApi.listResources).mockReset().mockResolvedValue([
      { id: 'res-1', name: 'Gabinete 1', is_active: true },
    ])
  })

  it(
    'antes fallaba en silencio (try/finally sin catch); ahora el error del backend ' +
      'se ve en la pantalla y no navega',
    async () => {
      vi.mocked(encountersApi.createEncounter)
        .mockReset()
        .mockRejectedValue(
          new ApiRequestError(403, { code: 'FORBIDDEN', message: 'No tienes permiso para esto' }),
        )

      renderResumen()

      const startButton = await screen.findByRole('button', { name: 'Iniciar atencion' })
      await userEvent.click(startButton)

      expect(await screen.findByText('No tienes permiso para esto')).toBeInTheDocument()
      expect(startButton).not.toBeDisabled()
    },
  )

  it('al funcionar, navega a la atencion creada', async () => {
    vi.mocked(encountersApi.createEncounter).mockReset().mockResolvedValue({
      id: 'enc-1',
      patient_id: 'pat-1',
      professional_id: 'prof-1',
      appointment_id: null,
      chief_complaint: null,
      started_at: new Date().toISOString(),
      ended_at: null,
    })

    renderResumen()

    const startButton = await screen.findByRole('button', { name: 'Iniciar atencion' })
    await userEvent.click(startButton)

    await waitFor(() => expect(encountersApi.createEncounter).toHaveBeenCalled())
  })

  it(
    'subir una foto que falla (antes era un try/finally sin catch, el error de ' +
      '"mas de 2 MB" quedaba invisible) ahora se ve en pantalla',
    async () => {
      vi.mocked(api.uploadPatientPhoto)
        .mockReset()
        .mockRejectedValue(
          new ApiRequestError(400, {
            code: 'FILE_TOO_LARGE',
            message: 'La foto no puede pesar mas de 2 MB',
          }),
        )

      renderResumen()

      const changeButton = await screen.findByRole('button', { name: 'Cambiar foto' })
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      const file = new File(['x'], 'foto.png', { type: 'image/png' })
      await userEvent.upload(input, file)

      expect(await screen.findByText('La foto no puede pesar mas de 2 MB')).toBeInTheDocument()
      expect(changeButton).not.toBeDisabled()
    },
  )
})

describe('ResumenTab: profesional y gabinete por defecto (B3)', () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: 'token',
      activeClinicId: 'clinic-1',
      clinics: [
        {
          clinic: { id: 'clinic-1', name: 'Sucursal Centro' },
          role: { code: 'admin_clinica', name: 'Administrador' },
        },
      ],
    })

    vi.mocked(api.getPatient).mockReset().mockResolvedValue({
      id: 'pat-1',
      expediente_number: '000001',
      first_name: 'Juan',
      last_name_paternal: 'Perez',
      last_name_maternal: null,
      full_name: 'Juan Perez',
      date_of_birth: '1990-01-01',
      sex: null,
      phone: null,
      email: null,
      address: null,
      status: 'activo',
      has_photo: false,
      default_resource_id: null,
      primary_provider_id: null,
    })
    vi.mocked(api.listContacts).mockReset().mockResolvedValue([])
    vi.mocked(encountersApi.getPatientTimeline).mockReset().mockResolvedValue([])
    vi.mocked(agendaApi.listProviders).mockReset().mockResolvedValue([
      { id: 'prov-1', user_id: 'u1', full_name: 'Dra. Gomez', color: '#2bb3a3', is_active: true, default_resource_id: null },
    ])
    vi.mocked(agendaApi.listResources).mockReset().mockResolvedValue([
      { id: 'res-1', name: 'Gabinete 1', is_active: true },
    ])
    vi.mocked(api.updatePatient).mockReset()
  })

  it('exige un motivo antes de habilitar el boton de guardar', async () => {
    renderResumen()
    await screen.findByText('Dra. Gomez')
    await userEvent.selectOptions(screen.getByLabelText('Profesional tratante'), 'prov-1')
    expect(screen.getByRole('button', { name: 'Guardar asignacion' })).toBeDisabled()

    await userEvent.type(screen.getByPlaceholderText('Motivo de la asignacion'), 'Primera asignacion')
    expect(screen.getByRole('button', { name: 'Guardar asignacion' })).not.toBeDisabled()
  })

  it('guarda el profesional y el gabinete con el motivo capturado', async () => {
    vi.mocked(api.updatePatient).mockResolvedValue({
      id: 'pat-1',
      expediente_number: '000001',
      first_name: 'Juan',
      last_name_paternal: 'Perez',
      last_name_maternal: null,
      full_name: 'Juan Perez',
      date_of_birth: '1990-01-01',
      sex: null,
      phone: null,
      email: null,
      address: null,
      status: 'activo',
      has_photo: false,
      default_resource_id: 'res-1',
      primary_provider_id: 'prov-1',
    })

    renderResumen()
    await screen.findByText('Dra. Gomez')
    await userEvent.selectOptions(screen.getByLabelText('Profesional tratante'), 'prov-1')
    await userEvent.selectOptions(screen.getByLabelText('Gabinete por defecto'), 'res-1')
    await userEvent.type(screen.getByPlaceholderText('Motivo de la asignacion'), 'Primera asignacion')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar asignacion' }))

    await waitFor(() =>
      expect(api.updatePatient).toHaveBeenCalledWith('pat-1', {
        primary_provider_id: 'prov-1',
        default_resource_id: 'res-1',
        care_assignment_reason: 'Primera asignacion',
      }),
    )
  })

  it('edita los datos generales del paciente', async () => {
    vi.mocked(api.updatePatient).mockResolvedValue({
      id: 'pat-1',
      expediente_number: '000001',
      first_name: 'Juana',
      last_name_paternal: 'Perez',
      last_name_maternal: null,
      full_name: 'Juana Perez',
      date_of_birth: '1990-01-01',
      sex: 'F',
      phone: '555-0000',
      email: null,
      address: null,
      status: 'activo',
      has_photo: false,
      default_resource_id: null,
      primary_provider_id: null,
    })

    renderResumen()
    await userEvent.click(await screen.findByRole('button', { name: 'Editar datos' }))

    const firstNameInput = screen.getByPlaceholderText('Nombre(s)')
    await userEvent.clear(firstNameInput)
    await userEvent.type(firstNameInput, 'Juana')
    await userEvent.selectOptions(screen.getByLabelText('Sexo'), 'F')
    await userEvent.type(screen.getByPlaceholderText('Telefono del paciente'), '555-0000')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar datos' }))

    await waitFor(() =>
      expect(api.updatePatient).toHaveBeenCalledWith('pat-1', {
        first_name: 'Juana',
        last_name_paternal: 'Perez',
        last_name_maternal: null,
        sex: 'F',
        patient_type: null,
        phone: '555-0000',
        email: null,
        address: null,
        birth_place: null,
        blood_type: null,
        education_level: null,
        can_read_write: null,
        religion: null,
        ethnic_group: null,
        race: null,
        occupation: null,
        marital_status: null,
      }),
    )
  })

  it('permite corregir a mano el tipo de paciente y muestra ayuda de contacto opcional para pediatricos', async () => {
    vi.mocked(api.updatePatient).mockResolvedValue({
      id: 'pat-1',
      expediente_number: '000001',
      first_name: 'Juan',
      last_name_paternal: 'Perez',
      last_name_maternal: null,
      full_name: 'Juan Perez',
      date_of_birth: '1990-01-01',
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

    renderResumen()
    await userEvent.click(await screen.findByRole('button', { name: 'Editar datos' }))

    expect(screen.queryByText(/Opcional para pacientes pediátricos/)).not.toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText('Tipo de paciente'), 'pediatrico')
    expect(screen.getAllByText(/Opcional para pacientes pediátricos/).length).toBeGreaterThan(0)

    await userEvent.click(screen.getByRole('button', { name: 'Guardar datos' }))

    await waitFor(() =>
      expect(api.updatePatient).toHaveBeenCalledWith(
        'pat-1',
        expect.objectContaining({ patient_type: 'pediatrico' }),
      ),
    )
  })
})
