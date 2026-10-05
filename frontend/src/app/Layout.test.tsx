import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { Layout } from './Layout'

describe('Layout', () => {
  it('muestra la marca y el titulo del encabezado', () => {
    const router = createMemoryRouter(
      [{ path: '/', element: <Layout />, children: [{ index: true, element: <div /> }] }],
      { initialEntries: ['/'] },
    )

    render(<RouterProvider router={router} />)

    expect(screen.getByText('DentalCare')).toBeInTheDocument()
    expect(screen.getByText('Sistema Clinico Dental')).toBeInTheDocument()
  })
})
