# Arquitectura técnica

## 1. Vista general
```
 Navegador (React/TS)  ──HTTPS──►  FastAPI (monolito modular)  ──►  PostgreSQL 16
   │  micrófono (MediaRecorder)          │                             
   │                                     ├──► storage/ (imágenes, PDF, logos)
   └──── audio webm/opus ───────────────►├──► faster-whisper (voz→texto, local)
                                         └──► Ollama :11434 (texto→acciones JSON, local)
```
Todo corre en el servidor o equipo de la clínica. Ningún dato clínico sale a internet.

## 2. Módulos backend (`backend/app/modules/`)
| Paquete | Entidades principales |
|---|---|
| `iam` | Organization, Clinic (sucursal), User, Role, Permission, UserClinic, Session, MfaSecret |
| `branding` | ClinicBranding (nombre, logo, paleta) |
| `patients` | Patient, PatientContact, Guardian, PatientStatus |
| `records` | MedicalHistory, Allergy, Medication, RiskFactor, ClinicalAlert, VitalSigns |
| `encounters` | Encounter, ClinicalNote (+ ClinicalNoteVersion) |
| `odontogram` | ToothCatalog, SurfaceCatalog, FindingCatalog, ToothFinding (evento), OdontogramSnapshot |
| `agenda` | Provider, Resource (gabinete), Appointment, AppointmentStatusHistory |
| `diagnosis` | DiagnosisCatalog, Diagnosis |
| `treatment` | ProcedureCatalog, PriceList, TreatmentPlan, TreatmentPhase, ProcedurePlanned, ProcedurePerformed, PlanAcceptance |
| `documents` | DocumentTemplate (versionada), Document, Consent, SignatureEvidence |
| `imaging` | ImageStudy, Image (metadatos + pieza/procedimiento) |
| `billing` | Charge, Payment, PaymentAllocation, Receipt, CashSession |
| `reports` | Vistas/consultas de solo lectura |
| `ai` | AiSession, AiTranscript, AiSuggestion, AiSettings |
| `audit` | AuditEvent |

## 3. Modelo de datos clave

### ToothFinding (odontograma por eventos)
| Campo | Tipo | Nota |
|---|---|---|
| id | uuid | |
| patient_id, encounter_id | uuid | encounter obligatorio |
| tooth_fdi | smallint | 11–48, 51–85, validado |
| surface | enum nullable | O, M, D, V, L, P, I; null = pieza completa |
| finding_code | fk FindingCatalog | caries, restauración, ausente, endodoncia, corona, prótesis, implante, extracción indicada, sellador, fractura, sano… |
| kind | enum | EXISTING (hallazgo) / PLANNED / PERFORMED |
| material | text nullable | resina, amalgama, zirconia… |
| supersedes_id | uuid nullable | evento anterior que reemplaza |
| is_current | bool | índice único parcial por (patient, tooth, surface, kind) where is_current |
| origin | enum | MANUAL / AI_ASSISTED |
| created_by, created_at | | |

El estado vigente se calcula con `is_current`; el historial completo se consulta con todos los eventos ordenados.

### ClinicalNote
`id, encounter_id, status (DRAFT/FINAL/CORRECTED/CANCELLED), soap_s, soap_o, soap_a, soap_p, free_text, version, previous_version_id, finalized_at, finalized_by, correction_reason, content_hash`

### AiSuggestion
`id, ai_session_id, patient_id, encounter_id, action_type, payload (jsonb), confidence, status (PENDING/ACCEPTED/EDITED/REJECTED/EXPIRED), applied_entity_type, applied_entity_id, model_name, model_digest, transcript_excerpt, decided_by, decided_at`

### AuditEvent
`event_id, timestamp, actor_user_id, clinic_id, action (CREATE/READ/UPDATE/CLOSE/EXPORT/SIGN/DENY/AI_SUGGEST/AI_APPLY), resource_type, resource_id, patient_id, result, ip, user_agent, before_hash, after_hash, reason, metadata jsonb`

Solo se permiten INSERT: se revoca UPDATE/DELETE al usuario de la aplicación y se añade un trigger que bloquea modificaciones.

## 4. Máquinas de estado
- **Cita:** RESERVADA → CONFIRMADA → EN_SALA → EN_ATENCION → TERMINADA; desde RESERVADA o CONFIRMADA → CANCELADA | NO_SHOW | REPROGRAMADA.
- **Nota:** DRAFT → FINAL → CORRECTED (nueva versión) | CANCELLED (con motivo).
- **Plan:** BORRADOR → PRESENTADO → ACEPTADO (total o parcial) | RECHAZADO → EN_PROGRESO → TERMINADO.

## 5. API base (`/api/v1`)
| Método | Ruta | Uso |
|---|---|---|
| POST | /auth/login, /auth/refresh, /auth/mfa/verify | Autenticación |
| GET/PUT | /branding (GET público), /branding/logo | Tema y logo |
| GET/POST | /patients, /patients/search?q=, /patients/duplicates-check | Pacientes |
| GET | /patients/{id}/summary | Encabezado y alertas |
| CRUD | /patients/{id}/allergies, /medications, /history | Expediente |
| POST | /encounters, /encounters/{id}/notes | Atención y notas |
| POST | /notes/{id}/finalize, /notes/{id}/correct | Reglas de nota |
| GET | /patients/{id}/odontogram?at=fecha | Estado vigente o a una fecha |
| POST | /tooth-findings | Registrar evento |
| CRUD | /appointments; PATCH /appointments/{id}/status | Agenda |
| POST | /diagnoses, /treatment-plans, /treatment-plans/{id}/accept | Clínico |
| POST | /ai/transcribe, /ai/interpret, /ai/suggestions/{id}/accept\|reject | Asistente IA |
| GET | /ai/status | Estado de Ollama y Whisper |
| POST | /payments, /charges | Cobranza |
| GET | /audit?patient_id=&user_id=&from=&to= | Auditoría |

## 6. Frontend
- **Layout:** barra lateral (logo de la clínica), búsqueda global de pacientes y **encabezado de paciente persistente** con barra de alertas.
- **Pestañas del paciente:** Resumen | Expediente | Odontograma | Tratamientos | Imágenes | Documentos | Agenda | Cuenta.
- **Odontograma:** componente SVG propio con `<Arch>`, `<Quadrant>`, `<Tooth>` y `<Surface>` (5 zonas clicables), leyenda configurable y un control deslizante de historial por fecha.
- **Asistente de voz:** botón flotante del micrófono, presente en todas las pantallas de atención, más un panel lateral de “Propuestas del asistente”.
- Atajos de teclado: `Alt+N` nueva atención, `Alt+O` odontograma, `Alt+M` micrófono, `Esc` cancelar dictado.

## 7. Respaldo
- `pg_dump` diario cifrado, copia de `storage/` y retención configurable.
- Script `scripts/restore_test.ps1`/`.sh` que restaura en una base temporal y registra el resultado.

## 8. Estado de implementación
| Fase | Alcance | Estado |
|---|---|---|
| 0 | Base del proyecto: estructura de carpetas, FastAPI con `/api/v1/health`, Alembic (async) configurado sin migraciones aún, frontend Vite + React 18 + TS con layout base (barra lateral, encabezado, contenido), `docker-compose.yml` (PostgreSQL 16), `.vscode/`, lint/format/test configurados en ambos lados | Hecho |
| 1–12 | Ver `prompts/PROMPTS_CLAUDE_CODE.md` | Pendiente |

Los módulos de la sección 2 son el diseño objetivo; ninguno tiene modelos ni migraciones todavía
— se crean conforme avanza cada fase.
