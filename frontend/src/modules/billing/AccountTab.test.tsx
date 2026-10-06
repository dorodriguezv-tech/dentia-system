import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AccountTab } from './AccountTab'
import * as api from './api'
import type { ChargeOut, PaymentOut } from './types'

vi.mock('./api')

const pendingCharge: ChargeOut = {
  id: 'charge-1',
  patient_id: 'pat-1',
  procedure_performed_id: 'perf-1',
  amount: '500.00',
  description: 'Resina oclusal (05/10/2026)',
  is_active: true,
  cancel_reason: null,
  computed_status: 'PENDIENTE',
  applied_amount: '0.00',
  balance: '500.00',
}

const payment: PaymentOut = {
  id: 'payment-1',
  patient_id: 'pat-1',
  method: 'efectivo',
  amount: '200.00',
  received_at: '2026-10-05T12:00:00Z',
  reference: null,
  notes: null,
  is_active: true,
  cancel_reason: null,
  allocated_amount: '200.00',
  unallocated_amount: '0.00',
  allocations: [{ id: 'alloc-1', charge_id: 'charge-1', amount_applied: '200.00' }],
}

function renderTab(canWrite = true) {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <AccountTab patientId="pat-1" canWrite={canWrite} />
    </QueryClientProvider>,
  )
}

describe('AccountTab', () => {
  beforeEach(() => {
    vi.mocked(api.getBillingSettings).mockReset().mockResolvedValue({ billing_enabled: true })
    vi.mocked(api.listCharges).mockReset().mockResolvedValue([pendingCharge])
    vi.mocked(api.listPayments).mockReset().mockResolvedValue([payment])
    vi.mocked(api.getBillingSummary).mockReset().mockResolvedValue({
      total_charged: '500.00',
      total_paid: '200.00',
      total_credit: '0.00',
      balance_due: '300.00',
    })
    vi.mocked(api.createPayment).mockReset()
    vi.mocked(api.cancelCharge).mockReset()
    vi.mocked(api.cancelPayment).mockReset()
  })

  it('muestra el resumen, los cargos y los pagos', async () => {
    renderTab()
    expect(await screen.findByText('$300.00')).toBeInTheDocument()
    expect(screen.getAllByText(/Resina oclusal/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Efectivo/).length).toBeGreaterThan(0)
  })

  it('registrar un pago con una aplicacion llama a la API correctamente', async () => {
    vi.mocked(api.createPayment).mockResolvedValue(payment)
    renderTab()

    await screen.findAllByText(/Resina oclusal/)
    await userEvent.type(screen.getByPlaceholderText('Monto recibido'), '200')
    await userEvent.type(screen.getByPlaceholderText('0.00'), '200')
    await userEvent.click(screen.getByRole('button', { name: 'Registrar pago' }))

    await waitFor(() =>
      expect(api.createPayment).toHaveBeenCalledWith('pat-1', {
        method: 'efectivo',
        amount: '200',
        reference: null,
        notes: null,
        allocations: [{ charge_id: 'charge-1', amount: '200' }],
      }),
    )
  })

  it('oculta el formulario de nuevo pago sin permiso de escritura', async () => {
    renderTab(false)
    await screen.findByText(/Resina oclusal/)
    expect(screen.queryByRole('button', { name: 'Registrar pago' })).not.toBeInTheDocument()
  })

  it('muestra un aviso cuando la cobranza esta desactivada', async () => {
    vi.mocked(api.getBillingSettings).mockResolvedValue({ billing_enabled: false })
    renderTab()
    expect(await screen.findByText(/cobranza esta desactivada/)).toBeInTheDocument()
    expect(screen.queryByText(/Resina oclusal/)).not.toBeInTheDocument()
  })
})
