import { createBrowserRouter } from 'react-router-dom'
import { AgendaPage } from '../modules/agenda/AgendaPage'
import { AiSettingsPage } from '../modules/ai/AiSettingsPage'
import { AppearancePage } from '../modules/branding/AppearancePage'
import { ClinicSelectPage } from '../modules/auth/ClinicSelectPage'
import { BillingSettingsPage } from '../modules/billing/BillingSettingsPage'
import { CashSessionPage } from '../modules/billing/CashSessionPage'
import { CatalogsPage } from '../modules/catalogs/CatalogsPage'
import { RequireAuth, RequireClinic, RequireRole } from '../modules/auth/guards'
import { LoginPage } from '../modules/auth/LoginPage'
import { MfaSetupPage } from '../modules/auth/MfaSetupPage'
import { AtencionPage } from '../modules/encounters/AtencionPage'
import { HelpPage } from '../modules/help/HelpPage'
import { NewPatientPage } from '../modules/patients/NewPatientPage'
import { PatientDetailPage } from '../modules/patients/PatientDetailPage'
import { PatientsListPage } from '../modules/patients/PatientsListPage'
import { ReportsPage } from '../modules/reports/ReportsPage'
import { UsersPage } from '../modules/users/UsersPage'
import { WorkingHoursPage } from '../modules/agenda/WorkingHoursPage'
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
              { path: 'agenda', element: <AgendaPage /> },
              { path: 'pacientes', element: <PatientsListPage /> },
              { path: 'pacientes/:id', element: <PatientDetailPage /> },
              { path: 'ayuda', element: <HelpPage /> },
              {
                element: (
                  <RequireRole roles={['admin_clinica', 'recepcion', 'odontologo', 'superadmin']} />
                ),
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
              {
                element: <RequireRole roles={['admin_clinica']} />,
                children: [
                  { path: 'configuracion/asistente-ia', element: <AiSettingsPage /> },
                  { path: 'configuracion/cobranza', element: <BillingSettingsPage /> },
                  { path: 'configuracion/catalogos', element: <CatalogsPage /> },
                  { path: 'configuracion/horarios', element: <WorkingHoursPage /> },
                ],
              },
              {
                element: <RequireRole roles={['admin_clinica', 'caja']} />,
                children: [{ path: 'caja', element: <CashSessionPage /> }],
              },
              {
                element: <RequireRole roles={['admin_clinica', 'caja', 'superadmin']} />,
                children: [{ path: 'reportes', element: <ReportsPage /> }],
              },
            ],
          },
        ],
      },
    ],
  },
])
