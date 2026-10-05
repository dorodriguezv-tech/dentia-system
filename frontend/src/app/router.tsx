import { createBrowserRouter } from 'react-router-dom'
import { ClinicSelectPage } from '../modules/auth/ClinicSelectPage'
import { RequireAuth, RequireClinic, RequireRole } from '../modules/auth/guards'
import { LoginPage } from '../modules/auth/LoginPage'
import { MfaSetupPage } from '../modules/auth/MfaSetupPage'
import { UsersPage } from '../modules/users/UsersPage'
import { HomePage } from './HomePage'
import { Layout } from './Layout'

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      { path: '/configuracion/mfa', element: <MfaSetupPage /> },
      { path: '/seleccionar-sucursal', element: <ClinicSelectPage /> },
      {
        element: <RequireClinic />,
        children: [
          {
            path: '/',
            element: <Layout />,
            children: [
              { index: true, element: <HomePage /> },
              {
                element: <RequireRole roles={['admin_clinica', 'superadmin']} />,
                children: [{ path: 'usuarios', element: <UsersPage /> }],
              },
            ],
          },
        ],
      },
    ],
  },
])
