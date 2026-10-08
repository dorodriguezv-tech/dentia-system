import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as agendaApi from '../agenda/api'
import type { ResourceOut } from '../agenda/types'
import * as authApi from '../auth/api'
import { useAuthStore } from '../auth/store'
import * as catalogsApi from './api'
import { CatalogsPage } from './CatalogsPage'
import type { CatalogImportSummary, CatalogItemOut } from './types'
import * as treatmentApi from '../treatment/api'
import type { ProcedureCatalogOut } from '../treatment/types'

vi.mock('./api')
vi.mock('../treatment/api')
vi.mock('../agenda/api')
vi.mock('../auth/api')

function renderPage() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <CatalogsPage />
    </QueryClientProvider>,
  )
}

const appointmentTypes: CatalogItemOut[] = [
  {
    id: 'c1',
    catalog_type: 'appointment_type',
    code: 'valoracion',
    name: 'Valoracion',
    is_active: true,
    sort_order: 0,
    extra: { default_minutes: 30 },
    updated_at: '2026-10-01T00:00:00Z',
  },
  {
    id: 'c2',
    catalog_type: 'appointment_type',
    code: 'limpieza_vieja',
    name: 'Limpieza (obsoleta)',
    is_active: false,
    sort_order: 1,
    extra: {},
    updated_at: '2026-10-01T00:00:00Z',
  },
]

const procedures: ProcedureCatalogOut[] = [
  { id: 'p1', code: 'resina', name: 'Resina', default_price: '500.00', is_active: true },
]

const resources: ResourceOut[] = [
  { id: 'res-1', name: 'Gabinete 1', is_active: true },
  { id: 'res-2', name: 'Gabinete viejo', is_active: false },
]

describe('CatalogsPage', () => {
  beforeEach(() => {
    useAuthStore.setState({
      clinics: [
        {
          clinic: {
            id: 'clinic-1',
            name: 'Sucursal Centro',
            address: 'Calle 1',
            phone: '5555555555',
          },
          role: { code: 'admin_clinica', name: 'Administrador' },
        },
      ],
      activeClinicId: 'clinic-1',
    })
    vi.mocked(catalogsApi.listCatalogItems).mockReset().mockResolvedValue(appointmentTypes)
    vi.mocked(catalogsApi.createCatalogItem).mockReset().mockResolvedValue(appointmentTypes[0])
    vi.mocked(catalogsApi.updateCatalogItem).mockReset().mockResolvedValue({
      ...appointmentTypes[0],
      is_active: false,
    })
    vi.mocked(catalogsApi.exportCatalogItems).mockReset().mockResolvedValue(undefined)
    vi.mocked(catalogsApi.importCatalogItems)
      .mockReset()
      .mockResolvedValue({ created: 1, updated: 0, errors: [] } satisfies CatalogImportSummary)
    vi.mocked(treatmentApi.listProcedureCatalog).mockReset().mockResolvedValue(procedures)
    vi.mocked(treatmentApi.createProcedureCatalogItem).mockReset().mockResolvedValue(procedures[0])
    vi.mocked(agendaApi.listResources).mockReset().mockResolvedValue(resources)
    vi.mocked(agendaApi.createResource).mockReset().mockResolvedValue(resources[0])
    vi.mocked(agendaApi.updateResource).mockReset().mockResolvedValue({
      ...resources[0],
      name: 'Gabinete renombrado',
    })
    vi.mocked(authApi.updateCurrentClinic).mockReset().mockResolvedValue({
      id: 'clinic-1',
      name: 'Sucursal Centro',
      address: 'Calle 2',
      phone: '5555555555',
    })
    vi.mocked(authApi.getMyClinics).mockReset().mockResolvedValue([
      {
        clinic: { id: 'clinic-1', name: 'Sucursal Centro', address: 'Calle 2', phone: '5555555555' },
        role: { code: 'admin_clinica', name: 'Administrador' },
      },
    ])
  })

  it('muestra el catalogo de tipos de cita por defecto, incluyendo los inactivos', async () => {
    renderPage()
    expect(await screen.findByText('valoracion')).toBeInTheDocument()
    expect(screen.getByText('limpieza_vieja')).toBeInTheDocument()
    expect(catalogsApi.listCatalogItems).toHaveBeenCalledWith('appointment_type', true)
  })

  it('cambia de pestaña y carga el catalogo de hallazgos del odontograma', async () => {
    renderPage()
    await screen.findByText('valoracion')
    await userEvent.click(screen.getByRole('button', { name: 'Hallazgos del odontograma' }))
    expect(catalogsApi.listCatalogItems).toHaveBeenCalledWith('odontogram_finding', true)
  })

  it('agregar un elemento nuevo llama a la API con el codigo y nombre capturados', async () => {
    renderPage()
    await screen.findByText('valoracion')
    await userEvent.type(
      screen.getByPlaceholderText('Codigo interno (minusculas, sin espacios)'),
      'ortodoncia_valoracion',
    )
    await userEvent.type(screen.getByPlaceholderText('Nombre visible'), 'Valoracion ortodoncia')
    await userEvent.click(screen.getByRole('button', { name: 'Agregar' }))
    expect(catalogsApi.createCatalogItem).toHaveBeenCalledWith(
      'appointment_type',
      expect.objectContaining({ code: 'ortodoncia_valoracion', name: 'Valoracion ortodoncia' }),
    )
  })

  it('desactivar un elemento activo llama a la API con is_active en false', async () => {
    renderPage()
    await screen.findByText('valoracion')
    await userEvent.click(screen.getAllByRole('button', { name: 'Desactivar' })[0])
    expect(catalogsApi.updateCatalogItem).toHaveBeenCalledWith('appointment_type', 'c1', {
      is_active: false,
    })
  })

  it('la pestaña de procedimientos reutiliza el catalogo de procedimientos existente', async () => {
    renderPage()
    await screen.findByText('valoracion')
    await userEvent.click(screen.getByRole('button', { name: 'Procedimientos y precios' }))
    expect(await screen.findByText('resina')).toBeInTheDocument()
    expect(treatmentApi.listProcedureCatalog).toHaveBeenCalled()
  })

  it('exportar CSV llama a la API del catalogo activo', async () => {
    renderPage()
    await screen.findByText('valoracion')
    await userEvent.click(screen.getByRole('button', { name: 'Exportar CSV' }))
    expect(catalogsApi.exportCatalogItems).toHaveBeenCalledWith('appointment_type')
  })

  it('importar CSV sube el archivo elegido y muestra el resumen', async () => {
    renderPage()
    await screen.findByText('valoracion')
    const file = new File(['code,name\nx,y\n'], 'items.csv', { type: 'text/csv' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, file)

    expect(catalogsApi.importCatalogItems).toHaveBeenCalledWith('appointment_type', file)
    expect(await screen.findByText(/1 creado\(s\), 0 actualizado\(s\)/)).toBeInTheDocument()
  })

  it('la pestaña Gabinetes permite crear, renombrar y desactivar', async () => {
    renderPage()
    await screen.findByText('valoracion')
    await userEvent.click(screen.getByRole('button', { name: 'Gabinetes' }))
    expect(await screen.findByText('Gabinete 1')).toBeInTheDocument()
    expect(screen.getByText('Gabinete viejo')).toBeInTheDocument()

    await userEvent.type(screen.getByPlaceholderText('Nombre del gabinete'), 'Gabinete 3')
    await userEvent.click(screen.getByRole('button', { name: 'Agregar' }))
    expect(agendaApi.createResource).toHaveBeenCalledWith('Gabinete 3')

    await userEvent.click(screen.getAllByRole('button', { name: 'Renombrar' })[0])
    const renameInput = screen.getAllByDisplayValue('Gabinete 1')[0]
    await userEvent.clear(renameInput)
    await userEvent.type(renameInput, 'Gabinete renombrado')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    expect(agendaApi.updateResource).toHaveBeenCalledWith('res-1', { name: 'Gabinete renombrado' })

    await userEvent.click(screen.getAllByRole('button', { name: 'Desactivar' })[0])
    expect(agendaApi.updateResource).toHaveBeenCalledWith('res-1', { is_active: false })
  })

  it('la pestaña Sucursal edita los datos basicos de la sucursal activa', async () => {
    renderPage()
    await screen.findByText('valoracion')
    await userEvent.click(screen.getByRole('button', { name: 'Sucursal' }))

    const addressInput = await screen.findByPlaceholderText('Direccion')
    expect(addressInput).toHaveValue('Calle 1')
    await userEvent.clear(addressInput)
    await userEvent.type(addressInput, 'Calle 2')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(authApi.updateCurrentClinic).toHaveBeenCalledWith({
      name: 'Sucursal Centro',
      address: 'Calle 2',
      phone: '5555555555',
      timezone: 'America/Mexico_City',
    })
  })

  it('la pestaña Sucursal permite cambiar la zona horaria (bug #42)', async () => {
    renderPage()
    await screen.findByText('valoracion')
    await userEvent.click(screen.getByRole('button', { name: 'Sucursal' }))

    const timezoneInput = await screen.findByLabelText('Zona horaria')
    expect(timezoneInput).toHaveValue('America/Mexico_City')
    await userEvent.clear(timezoneInput)
    await userEvent.type(timezoneInput, 'America/Tijuana')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(authApi.updateCurrentClinic).toHaveBeenCalledWith({
      name: 'Sucursal Centro',
      address: 'Calle 1',
      phone: '5555555555',
      timezone: 'America/Tijuana',
    })
  })
})
