import { api } from './client';
import type {
  AiStatus,
  AiSuggestion,
  Appointment,
  AppointmentStatus,
  Branding,
  ClinicMembership,
  Encounter,
  InterpretResponse,
  LoginResponse,
  Me,
  OdontogramResponse,
  PatientListItem,
  PatientSummary,
  RawMyClinic,
  Surface,
  TokenPair,
  TranscribeResponse,
  Uuid,
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

// ---------- Pacientes ----------
export const searchPatients = (q: string) =>
  api<PatientListItem[]>('/patients/search', { query: { q } });

export const getPatientSummary = (id: Uuid) => api<PatientSummary>(`/patients/${id}/summary`);

export const getOdontogram = (id: Uuid) => api<OdontogramResponse>(`/patients/${id}/odontogram`); // arreglo directo, sin envoltura

export const createToothFinding = (input: {
  patient_id: Uuid;
  encounter_id: Uuid;
  tooth_fdi: number;
  surface: Surface | null;
  finding_code: string;
  kind?: 'EXISTING';
  material?: string | null;
}) => api('/tooth-findings', { method: 'POST', body: { kind: 'EXISTING', ...input } });

export const getPatientEncounters = (id: Uuid) => api<Encounter[]>(`/patients/${id}/encounters`);

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
