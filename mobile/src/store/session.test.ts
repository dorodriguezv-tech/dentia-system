import { hasPermission, useSession } from './session';

/**
 * M2 (docs/06_APP_MOVIL_V1_1_PARIDAD.md, R4): la sección "Clínica" de Ajustes se
 * oculta con `hasPermission('branding.manage') || hasPermission('ai.configure')`.
 * Estas pruebas fijan el comportamiento de `hasPermission` en el que se apoya esa
 * regla, sin tocar SecureStore (no se llama a `clear`/`setClinic`, solo `setState`).
 */
describe('hasPermission', () => {
  afterEach(() => {
    useSession.setState({ clinics: [], clinicId: null });
  });

  it('es falso sin sucursal elegida', () => {
    useSession.setState({ clinics: [], clinicId: null });
    expect(hasPermission('branding.manage')).toBe(false);
  });

  it('es verdadero solo si la sucursal activa tiene el permiso (recepción)', () => {
    useSession.setState({
      clinicId: 'clinic-1',
      clinics: [
        { clinic_id: 'clinic-1', clinic_name: 'Clínica Centro', role: 'recepcion', permissions: ['agenda.read', 'agenda.write'] },
      ],
    });
    expect(hasPermission('agenda.read')).toBe(true);
    expect(hasPermission('branding.manage')).toBe(false);
    expect(hasPermission('ai.configure')).toBe(false);
  });

  it('admin_clinica ve la sección Clínica (branding.manage)', () => {
    useSession.setState({
      clinicId: 'clinic-1',
      clinics: [
        { clinic_id: 'clinic-1', clinic_name: 'Clínica Centro', role: 'admin_clinica', permissions: ['branding.manage', 'ai.configure'] },
      ],
    });
    expect(hasPermission('branding.manage') || hasPermission('ai.configure')).toBe(true);
  });

  it('usa los permisos de la sucursal activa, no de otra a la que también pertenece', () => {
    useSession.setState({
      clinicId: 'clinic-2',
      clinics: [
        { clinic_id: 'clinic-1', clinic_name: 'Clínica Centro', role: 'admin_clinica', permissions: ['branding.manage'] },
        { clinic_id: 'clinic-2', clinic_name: 'Clínica Norte', role: 'recepcion', permissions: ['agenda.read'] },
      ],
    });
    expect(hasPermission('branding.manage')).toBe(false);
  });
});
