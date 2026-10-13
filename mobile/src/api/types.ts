/**
 * Tipos de la API de DENT-IA (FastAPI, /api/v1) que usa la app móvil.
 *
 * Escritos a mano a partir de docs/02_ARQUITECTURA.md. La fuente de verdad es el
 * backend: en desarrollo genera los tipos exactos con
 *   npx openapi-typescript http://<servidor>:8001/openapi.json -o src/api/schema.d.ts
 * y reemplaza aquí lo que no coincida (CLAUDE.md, tarea 1).
 */

export type Uuid = string;

// ---------- Autenticación (Fase 1) ----------
export interface LoginResponse {
  access_token?: string;
  refresh_token?: string;
  token_type?: string;
  /** El backend pide el segundo paso TOTP */
  mfa_required?: boolean;
  /** Token temporal para /auth/login/mfa */
  mfa_token?: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export interface Me {
  id: Uuid;
  email: string;
  full_name: string;
  mfa_setup_required?: boolean;
}

/** Forma "plana" que usa la app (session.ts, hasPermission). `getMyClinics()`
 * la arma a partir de `RawMyClinic`, la forma real que manda el backend. */
export interface ClinicMembership {
  clinic_id: Uuid;
  clinic_name: string;
  role: string;
  permissions: string[];
}

/** Forma real de GET /me/clinics (backend/app/modules/iam/schemas.py MyClinicOut). */
export interface RawMyClinic {
  clinic: { id: Uuid; name: string; address?: string | null; phone?: string | null; timezone: string };
  role: { code: string; name: string };
  clinic_name: string;
  permissions: string[];
}

/** GET/PUT /me/preferences (B7, docs/06_APP_MOVIL_V1_1_PARIDAD.md sec. 4): la
 * misma preferencia viaja entre web, tablet y teléfono. */
export type PreferenceTheme = 'system' | 'light' | 'dark';

export interface UserPreferences {
  language: string;
  theme: PreferenceTheme;
  dentia_enabled: boolean;
  voice_id: string | null;
  speech_rate: number;
  speech_volume: number;
  lock_timeout_minutes: number;
}

export type UserPreferencesUpdate = Partial<UserPreferences>;

// ---------- Marca (Fase 2) ----------
export interface ColorPalette {
  primary: string;
  secondary: string;
  accent: string;
  bg: string;
  surface: string;
  border: string;
  text: string;
  text_muted: string;
  success: string;
  warning: string;
  danger: string;
}

export interface Branding {
  display_name: string;
  subtitle?: string | null;
  preset?: string;
  colors: ColorPalette;
  dark_mode?: boolean;
  logo_url?: string | null;
  favicon_url?: string | null;
}

// ---------- Pacientes (Fase 3) ----------
export type PatientStatus = 'activo' | 'inactivo' | 'referido' | 'fallecido' | 'bloqueado';

export interface PatientListItem {
  id: Uuid;
  expediente_number: string;
  full_name: string;
  date_of_birth: string;
  phone: string | null;
  status: PatientStatus;
}

/** El backend solo manda texto (p. ej. "Alergia a penicilina"); no hay severidad
 * ni tipo estructurados todavia en ningun endpoint (/summary ni /patients/{id}/alerts). */
export type ClinicalAlert = string;

export interface PatientSummary {
  id: Uuid;
  expediente_number: string;
  full_name: string;
  age: number;
  status: PatientStatus;
  has_photo: boolean;
  alerts: ClinicalAlert[];
}

// ---------- Odontograma (Fase 5) ----------
export type Surface = 'O' | 'M' | 'D' | 'V' | 'L' | 'P' | 'I';
export type FindingKind = 'EXISTING' | 'PLANNED' | 'PERFORMED';

export interface ToothFinding {
  id: Uuid;
  encounter_id: Uuid;
  tooth_fdi: number;
  surface: Surface | null;
  finding_code: string;
  kind: FindingKind;
  material?: string | null;
  is_current?: boolean;
  origin: 'MANUAL' | 'AI_ASSISTED';
  created_at: string;
}

/** GET /patients/{id}/odontogram responde el arreglo directo, sin envoltura. */
export type OdontogramResponse = ToothFinding[];

// ---------- Agenda (Fase 6) ----------
export type AppointmentStatus =
  | 'RESERVADA'
  | 'CONFIRMADA'
  | 'EN_SALA'
  | 'EN_ATENCION'
  | 'TERMINADA'
  | 'CANCELADA'
  | 'NO_SHOW'
  | 'REPROGRAMADA';

export interface Appointment {
  id: Uuid;
  patient_id: Uuid;
  patient_full_name: string;
  provider_id: Uuid;
  provider_full_name: string;
  starts_at: string;
  ends_at: string;
  status: AppointmentStatus;
  appointment_type?: string | null;
  notes?: string | null;
}

export interface Encounter {
  id: Uuid;
  patient_id: Uuid;
  started_at: string;
  chief_complaint?: string | null;
}

// ---------- IA (Fase 8) ----------
export interface TranscribeResponse {
  text: string;
}

export interface AiSuggestion {
  id: Uuid;
  batch_id: Uuid;
  action_type: string;
  payload: Record<string, unknown>;
  status: 'PENDING' | 'ACCEPTED' | 'REJECTED';
  transcript_excerpt?: string | null;
}

export interface UnrecognizedOut {
  text: string;
  reason: string;
}

export interface InterpretResponse {
  suggestions: AiSuggestion[];
  unrecognized: UnrecognizedOut[];
}

export interface AiStatus {
  ai_enabled: boolean;
  ollama_reachable: boolean;
  ollama_model: string;
  ollama_digest: string | null;
  whisper_model: string;
  whisper_device: string;
}

// ---------- Errores ----------
export interface ApiErrorBody {
  detail?: string | { code?: string; message?: string } | unknown;
  code?: string;
}
