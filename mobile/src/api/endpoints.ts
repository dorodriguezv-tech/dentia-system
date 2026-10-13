import { api } from './client';
import type {
  AiStatus,
  AiSuggestion,
  Appointment,
  AppointmentCreateInput,
  AppointmentStatus,
  AppointmentTypeCatalogItem,
  AvailableSlots,
  Branding,
  ClinicalNote,
  ClinicalNoteFields,
  ClinicMembership,
  CurrentEncounter,
  DaySchedule,
  Encounter,
  EncounterCreateInput,
  FindingKind,
  InterpretResponse,
  LoginResponse,
  Me,
  OdontogramFindingCatalogItem,
  OdontogramResponse,
  PatientCreateInput,
  PatientDetail,
  PatientListItem,
  PatientSummary,
  ProcedurePerformedSummary,
  Provider,
  RawCatalogItem,
  RawMyClinic,
  RescheduleInput,
  Surface,
  ToothFinding,
  ToothFindingHistoryEntry,
  TokenPair,
  TranscribeResponse,
  TreatmentPlanSummary,
  UserPreferences,
  UserPreferencesUpdate,
  Uuid,
  WaitlistCreateInput,
} from './types';

/**
 * Una función por endpoint, con las mismas rutas que docs/02_ARQUITECTURA.md §5.
 * Verificado contra backend/app/ generando src/api/schema.d.ts con openapi-typescript
 * y comparando cada operación y esquema (tarea 1, 2026-10-12).
 */

// ---------- Salud y marca ----------
export const getHealth = () => api<{ status: string }>('/health', { auth: false, timeoutMs: 6000 });
export const getBranding = () => api<Branding>('/branding', { auth: false });
export const brandingLogoUrl = (server: string) => `${server}/api/v1/branding/logo`;

// ---------- Autenticación ----------
export const login = (email: string, password: string) =>
  api<LoginResponse>('/auth/login', { method: 'POST', body: { email, password }, auth: false, retryOn401: false });

// Confirmado contra backend/app/modules/iam/router.py (tarea 1): mfa_token + code.
export const loginMfa = (mfa_token: string, code: string) =>
  api<TokenPair>('/auth/login/mfa', { method: 'POST', body: { mfa_token, code }, auth: false, retryOn401: false });

export const logout = (refresh_token: string) =>
  api<void>('/auth/logout', { method: 'POST', body: { refresh_token } }).catch(() => undefined);

export const getMe = () => api<Me>('/me');

// El backend manda {clinic: {...}, role: {...}, clinic_name, permissions}; la app
// solo necesita la forma plana (session.ts: hasPermission, clinics.find).
export const getMyClinics = async (): Promise<ClinicMembership[]> => {
  const raw = await api<RawMyClinic[]>('/me/clinics');
  return raw.map((m) => ({
    clinic_id: m.clinic.id,
    clinic_name: m.clinic_name,
    role: m.role.code,
    permissions: m.permissions,
  }));
};

export const getPreferences = () => api<UserPreferences>('/me/preferences');

export const updatePreferences = (patch: UserPreferencesUpdate) =>
  api<UserPreferences>('/me/preferences', { method: 'PUT', body: patch });

// ---------- Pacientes ----------
export const searchPatients = (q: string) =>
  api<PatientListItem[]>('/patients/search', { query: { q } });

export const getPatientSummary = (id: Uuid) => api<PatientSummary>(`/patients/${id}/summary`);

export const getOdontogram = (id: Uuid) => api<OdontogramResponse>(`/patients/${id}/odontogram`); // arreglo directo, sin envoltura

// M5: historial real de una pieza (fecha, autor, origen) — antes la app mostraba
// solo el hallazgo vigente filtrando el odontograma actual, no el historial.
export const getToothHistory = (patientId: Uuid, toothFdi: number) =>
  api<ToothFindingHistoryEntry[]>(`/patients/${patientId}/teeth/${toothFdi}/history`);

export const createToothFinding = (input: {
  patient_id: Uuid;
  encounter_id: Uuid;
  tooth_fdi: number;
  surface: Surface | null;
  finding_code: string;
  kind?: FindingKind;
  material?: string | null;
}) => api<ToothFinding>('/tooth-findings', { method: 'POST', body: { kind: 'EXISTING', ...input } });

// M5 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3): "Anular" un hallazgo vigente con
// motivo obligatorio (B12) -- nunca se borra (regla 2 de CLAUDE.md).
export const annulToothFinding = (findingId: Uuid, reason: string) =>
  api<ToothFinding>(`/tooth-findings/${findingId}/annul`, { method: 'POST', body: { reason } });

// Catálogo real de la sucursal (antes: una lista fija en MAYÚSCULA en el teléfono
// que el backend siempre rechazaba — ver FINDING_COLORS en theme.tsx).
export const listOdontogramFindings = async (): Promise<OdontogramFindingCatalogItem[]> => {
  const raw = await api<RawCatalogItem[]>('/catalogs/odontogram_finding');
  return raw
    .filter((i) => i.is_active)
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((i) => ({ code: i.code, name: i.name, requiresSurface: !!i.extra?.requires_surface }));
};

export const getPatientEncounters = (id: Uuid) => api<Encounter[]>(`/patients/${id}/encounters`);

export const getPatient = (id: Uuid) => api<PatientDetail>(`/patients/${id}`);

// M3: "Crear paciente rápido" desde Nueva cita (requiere patients.write).
export const createPatientQuick = (input: PatientCreateInput) =>
  api<PatientDetail>('/patients', { method: 'POST', body: input });

// Fotografías clínicas (Fase 9). encounter_id es obligatorio para el backend
// (regla 6: todo hallazgo/imagen va ligado a una atención).
export async function uploadPatientImages(
  patientId: Uuid,
  files: { uri: string; name: string; mimeType: string }[],
  meta: { study_type: string; encounter_id: Uuid; tooth_fdi?: number; notes?: string },
) {
  const form = new FormData();
  for (const f of files) {
    // React Native acepta este objeto como archivo en FormData
    form.append('files', { uri: f.uri, name: f.name, type: f.mimeType } as unknown as Blob);
  }
  form.append('study_type', meta.study_type);
  form.append('encounter_id', meta.encounter_id);
  if (meta.tooth_fdi) form.append('tooth_fdi', String(meta.tooth_fdi));
  if (meta.notes) form.append('notes', meta.notes);
  return api(`/patients/${patientId}/images`, { method: 'POST', form, timeoutMs: 120_000 });
}

// ---------- Agenda ----------
export const listAppointments = (starts_from: string, starts_to: string, provider_id?: Uuid) =>
  api<Appointment[]>('/appointments', { query: { starts_from, starts_to, provider_id } });

export const setAppointmentStatus = (id: Uuid, status: AppointmentStatus, reason?: string) =>
  api<Appointment>(`/appointments/${id}/status`, { method: 'PATCH', body: { status, reason } });

export const startEncounter = (appointmentId: Uuid) =>
  api<Encounter>(`/appointments/${appointmentId}/start-encounter`, { method: 'POST' });

// M4 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3, R2): iniciar atención sin cita
// (urgencia) y recuperar la consulta abierta (B10).
export const createEncounter = (input: EncounterCreateInput) =>
  api<Encounter>('/encounters', { method: 'POST', body: input });

export const getCurrentEncounter = () => api<CurrentEncounter | null>('/encounters/current');

export const getEncounter = (id: Uuid) => api<Encounter>(`/encounters/${id}`);

export const listTreatmentPlans = (patientId: Uuid) =>
  api<TreatmentPlanSummary[]>(`/patients/${patientId}/treatment-plans`);

export const listProceduresPerformed = (patientId: Uuid) =>
  api<ProcedurePerformedSummary[]>(`/patients/${patientId}/procedures-performed`);

// M6 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3): nota de la consulta y cierre.
export const listEncounterNotes = (encounterId: Uuid) =>
  api<ClinicalNote[]>(`/encounters/${encounterId}/notes`);

export const createNote = (encounterId: Uuid, input: ClinicalNoteFields) =>
  api<ClinicalNote>(`/encounters/${encounterId}/notes`, { method: 'POST', body: input });

export const updateNote = (noteId: Uuid, input: ClinicalNoteFields) =>
  api<ClinicalNote>(`/notes/${noteId}`, { method: 'PATCH', body: input });

export const finalizeNote = (noteId: Uuid, alertsAcknowledged: boolean) =>
  api<ClinicalNote>(`/notes/${noteId}/finalize`, { method: 'POST', body: { alerts_acknowledged: alertsAcknowledged } });

export const closeEncounter = (encounterId: Uuid, alertsAcknowledged: boolean) =>
  api<Encounter>(`/encounters/${encounterId}/close`, { method: 'POST', body: { alerts_acknowledged: alertsAcknowledged } });

// M7: "Recordar después" al cerrar sin agendar la próxima cita todavía.
export const createWaitlistEntry = (input: WaitlistCreateInput) =>
  api('/waitlist', { method: 'POST', body: input });

// M3 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3, R1): mismos endpoints que
// frontend/src/modules/agenda/api.ts.
export const listProviders = () => api<Provider[]>('/providers');

export const listAppointmentTypes = async (): Promise<AppointmentTypeCatalogItem[]> => {
  const raw = await api<RawCatalogItem[]>('/catalogs/appointment_type');
  return raw
    .filter((i) => i.is_active)
    .map((i) => ({
      code: i.code,
      name: i.name,
      default_minutes: typeof i.extra?.default_minutes === 'number' ? (i.extra.default_minutes as number) : 30,
    }));
};

export const getAvailability = (provider_id: Uuid, day: string, duration_minutes: number) =>
  api<AvailableSlots>('/appointments/availability', { query: { provider_id, day, duration_minutes } });

/** Cuadrícula de horas completas del día (disponibles y ocupadas), de acuerdo a la
 * agenda real del profesional. Reporte al probar en un teléfono real: la lista de
 * `getAvailability` solo mostraba 3 huecos sueltos en pasos de 15 minutos. */
export const getDaySchedule = (provider_id: Uuid, day: string, duration_minutes: number) =>
  api<DaySchedule>('/appointments/day-schedule', { query: { provider_id, day, duration_minutes } });

export const createAppointment = (input: AppointmentCreateInput) =>
  api<Appointment>('/appointments', { method: 'POST', body: input });

export const rescheduleAppointment = (id: Uuid, input: RescheduleInput) =>
  api<Appointment>(`/appointments/${id}/reschedule`, { method: 'POST', body: input });

// ---------- Asistente de IA ----------
export const getAiStatus = () => api<AiStatus>('/ai/status');

/**
 * Envía el audio grabado (m4a/AAC de Android) a faster-whisper.
 * Confirmado contra backend/app/ai/router.py y stt.py (tarea 1, cambio B2): el campo
 * se llama "audio" y no hay filtro de content-type (PyAV decodifica mp4/m4a sin cambios).
 */
export async function transcribe(uri: string): Promise<TranscribeResponse> {
  const form = new FormData();
  form.append('audio', { uri, name: 'dictado.m4a', type: 'audio/mp4' } as unknown as Blob);
  return api<TranscribeResponse>('/ai/transcribe', { method: 'POST', form, timeoutMs: 90_000 });
}

export const interpret = (input: { transcript: string; encounter_id: Uuid }) =>
  api<InterpretResponse>('/ai/interpret', {
    method: 'POST',
    body: input,
    timeoutMs: 130_000, // OLLAMA_TIMEOUT_S = 120 en el backend
  });

export const listSuggestions = (encounter_id: Uuid) =>
  api<AiSuggestion[]>('/ai/suggestions', { query: { encounter_id } });

export const acceptSuggestion = (id: Uuid, edits?: Record<string, unknown>) =>
  api<AiSuggestion>(`/ai/suggestions/${id}/accept`, { method: 'POST', body: { edits: edits ?? null } });

export const rejectSuggestion = (id: Uuid, reason?: string) =>
  api<AiSuggestion>(`/ai/suggestions/${id}/reject`, { method: 'POST', body: { reason } });
