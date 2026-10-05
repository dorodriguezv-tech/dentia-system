import { createBrowserRouter } from 'react-router-dom'
import { AppearancePage } from '../modules/branding/AppearancePage'
import { ClinicSelectPage } from '../modules/auth/ClinicSelectPage'
import { RequireAuth, RequireClinic, RequireRole } from '../modules/auth/guards'
import { LoginPage } from '../modules/auth/LoginPage'
import { MfaSetupPage } from '../modules/auth/MfaSetupPage'
import { AtencionPage } from '../modules/encounters/AtencionPage'
import { NewPatientPage } from '../modules/patients/NewPatientPage'
import { PatientDetailPage } from '../modules/patients/PatientDetailPage'
import { PatientsListPage } from '../modules/patients/PatientsListPage'
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
              { path: 'pacientes', element: <PatientsListPage /> },
              { path: 'pacientes/:id', element: <PatientDetailPage /> },
              {
                element: <RequireRole roles={['admin_clinica', 'recepcion', 'superadmin']} />,
                children: [{ path: 'pacientes/nuevo', element: <NewPatientPage /> }],
              },
              {
                element: <RequireRole roles={['odontologo', 'especialista']} />,
                children: [
                  { path: 'pacientes/:patientId/atencion/:encounterId', element: <AtencionPage /> },
                ],
              },
              {
                element: <RequireRole roles={['admin_clinica', 'superadmin']} />,
                children: [
                  { path: 'usuarios', element: <UsersPage /> },
                  { path: 'configuracion/apariencia', element: <AppearancePage /> },
                ],
              },
            ],
          },
        ],
      },
    ],
  },
])
