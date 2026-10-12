# DENT-IA — arquitectura y estado actual (resumen para contexto de Claude)

> Extracto condensado de `docs/02_ARQUITECTURA.md` (sin el detalle fase por fase):
> módulos, modelo de datos, API y qué está hecho hoy. Para el diseño completo de
> cada fase, el código es la fuente de verdad — este archivo es solo para orientar
> una conversación sin acceso al repositorio.

## Qué es
Plataforma web (+ app móvil Android) para clínicas dentales en México. Núcleo:
expediente clínico → odontograma → tratamiento → pago, con un asistente de IA por
voz que **propone** datos (nunca escribe directo — regla 9 más abajo) usando Ollama
y Whisper 100% locales. Todo corre en el servidor de la clínica; nada clínico sale
a internet.

## Stack
Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x async + asyncpg, Alembic,
PostgreSQL 16. Frontend: React 18 + TypeScript + Vite, CSS Modules + variables CSS
(sin colores fijos fuera de `theme/`, hay un lint que lo exige). App móvil: Expo
SDK 57 + React Native 0.86 + TS estricto (`mobile/`, cliente puro de `/api/v1`, sin
lógica clínica propia). IA local: Ollama (`:11434`) + faster-whisper. Auth: JWT
corto + refresh con rotación, Argon2id, MFA TOTP. Archivos: `storage/` local vía
`StorageBackend`.

## Reglas clínicas inviolables (con pruebas unitarias cada una)
1. Nota clínica en FINAL no se modifica; corregir crea una versión nueva (CORRECTED).
2. No hay borrado físico de registros clínicos — solo anulación con motivo y auditoría.
3. Lo planificado ≠ lo realizado: `ProcedurePlanned`/`ProcedurePerformed` separadas.
4. Un presupuesto aceptado no es un pago; un pago no cambia el estado clínico.
5. Una pieza puede tener muchos hallazgos históricos, solo uno **vigente** por pieza+superficie.
6. Todo hallazgo/diagnóstico/procedimiento lleva fecha, autor y `encounter_id`.
7. Documentos firmados no se sobrescriben; cada versión nueva tiene su propio hash SHA-256.
8. Alertas críticas (alergias, medicamentos de riesgo) se muestran **antes** de recetar/cerrar nota/procedimiento.
9. **La IA nunca escribe directo.** Crea `AiSuggestion` PENDING; solo aceptar/editar humano la aplica.
10. Todo lo que viene de la IA queda `origin = AI_ASSISTED` con modelo, versión y fecha.

RBAC: superadmin, admin_clinica, odontologo, especialista, asistente, recepcion,
caja — más ABAC por sucursal (`X-Clinic-Id`). El superadmin **no** tiene acceso
automático a contenido clínico. Matriz completa de permisos por rol:
`docs/MATRIZ_PERMISOS.md` (súbelo junto con este archivo).

## Módulos backend (`backend/app/modules/`)
| Paquete | Entidades principales |
|---|---|
| `iam` | Organization, Clinic, User, Role, Permission, UserClinic, RefreshToken |
| `branding` | ClinicBranding (nombre, logo, paleta — marca DENT-IA, ver abajo) |
| `patients` | Patient, PatientContact, PatientStatus |
| `records` | MedicalHistory, Allergy, Medication, VitalSigns |
| `encounters` | Encounter, ClinicalNote (+ versión) |
| `odontogram` | ToothFinding (evento), catálogos de piezas/superficies/hallazgos |
| `agenda` | Provider, Resource (gabinete), Appointment, ReminderTask |
| `diagnosis` | DiagnosisCatalog, Diagnosis |
| `treatment` | ProcedureCatalog, TreatmentPlan, TreatmentPhase, ProcedurePlanned/Performed |
| `documents` | DocumentTemplate (versionada), Consent |
| `imaging` | Image |
| `billing` | Charge, Payment, PaymentAllocation, CashSession |
| `reports` | solo lectura, sin tablas propias |
| `audit` | AuditEvent (solo INSERT, trigger bloquea UPDATE/DELETE) |
| `catalogs` | ClinicCatalogItem (catálogos administrables por sucursal: tipos de cita, hallazgos, diagnósticos, etc.) |

`app/ai/` (asistente de IA por dictado) y `app/voice/` (asistente conversacional
"Dentia") son paquetes de nivel superior, no viven en `modules/`.

## Modelo de datos — lo no obvio
- **ToothFinding**: eventos, no un estado mutable. `is_current` + índice único parcial
  por (paciente, pieza, superficie, tipo) marca el vigente; el historial son todos los
  eventos. `kind`: EXISTING / PLANNED / PERFORMED.
- **AiSuggestion**: una fila por *acción*, no por dictado completo. `batch_id` agrupa
  las de una misma llamada a `/ai/interpret`. No tiene `confidence` ni expira sola.
- **Charge**: su `status` guardado ya no se usa — el estado de cobro se calcula en
  caliente contra `PaymentAllocation` (regla 4, nunca se guarda un "pagado").
- **Consent**: se crea ya firmado (capturar firma + generar PDF es un solo acto);
  después solo se anula, nunca se edita ni se regenera el PDF.
- **AuditEvent**: INSERT-only de verdad, a nivel de base de datos (trigger).

## Máquinas de estado
- Cita: `RESERVADA → CONFIRMADA → EN_SALA → EN_ATENCION → TERMINADA`; desde
  RESERVADA/CONFIRMADA también `→ CANCELADA | NO_SHOW | REPROGRAMADA`.
- Nota: `DRAFT → FINAL → CORRECTED (nueva versión) | CANCELLED`.
- Plan de tratamiento: `BORRADOR → PRESENTADO → ACEPTADO | RECHAZADO → EN_PROGRESO → TERMINADO`.

## API base (`/api/v1`) — mapa rápido
Auth: `POST /auth/login`, `/login/mfa`, `/refresh`, `/logout`, `/mfa/setup|enable|disable`.
Sesión: `GET /me`, `/me/clinics` (incluye `clinic_name`/`permissions` por sucursal).
Marca: `GET/PUT /branding` (GET público), `POST/GET /branding/logo|favicon` (público).
Pacientes: `/patients`, `/search?q=`, `/duplicates-check`, `/{id}/summary`, `/{id}/alerts`,
`/{id}/contacts`, `/{id}/photo`, `/{id}/history|allergies|medications|vital-signs`.
Clínico: `/encounters`, `/patients/{id}/timeline`, `/encounters/{id}/notes`,
`/notes/{id}/finalize|correct|cancel`.
Odontograma: `GET /patients/{id}/odontogram?at=`, `POST /tooth-findings`,
`GET /patients/{id}/teeth/{fdi}/history`.
Agenda: `/providers`, `/resources`, `/appointments`, `PATCH .../status`,
`POST .../reschedule`, `POST .../start-encounter`, `/waitlist`.
Diagnóstico/tratamiento: `/patients/{id}/diagnoses`, `/procedure-catalog`,
`/patients/{id}/treatment-plans`, `/treatment-plans/{id}`, `.../pdf`.
IA: `POST /ai/transcribe`, `/ai/interpret`, `GET /ai/suggestions?encounter_id=`,
`POST /ai/suggestions/{id}/accept|reject`, `GET /ai/status`, `GET/PUT /ai/settings`.
Documentos: `/document-templates`, `/patients/{id}/consents`, `/consents/{id}/pdf|annul`.
Imágenes: `/patients/{id}/images`, `/images/{id}`, `/images/{id}/thumbnail|annul`.
Cobranza: `/charges/{id}/cancel`, `/patients/{id}/payments`, `/payments/{id}/receipt|cancel`,
`/patients/{id}/billing-summary`, `/cash-sessions/...`, `/billing/settings`.
Reportes: `/reports/patients|appointments|production|treatment-plans|ai-usage`,
`/reports/accounts-receivable`, `/reports/{reporte}/export`, `/reports/dashboard`.
Auditoría: `GET /audit?patient_id=&user_id=&from=&to=`.

Para los campos exactos de cada endpoint (hay varios nombres no obvios), ver
`02_notas_contrato_api.md` en esta misma carpeta.

## Estado de implementación (resumen)
Todo lo siguiente está **hecho** (con pruebas unitarias + integración):
base del proyecto · IAM/auditoría · marca y tema (branding) · pacientes ·
expediente/atención/notas SOAP · odontograma · agenda · diagnóstico y tratamiento
(con PDF de presupuesto) · asistente de IA por dictado (`app/ai/`) · consentimientos
e imagenología · cobranza completa (pagos, caja) · reportes y tablero por rol ·
E2E con Playwright (flujo completo, accesibilidad axe-core, rendimiento) ·
catálogos administrables por sucursal · gabinete/profesional por defecto ·
asistente conversacional "Dentia" (`app/voice/`, navegación + captura clínica +
agenda por voz + vocabulario odontológico) · app móvil DENT-IA (Expo, cliente del
mismo backend) · marca DENT-IA aplicada en backend + frontend + móvil (preset,
logo por defecto, PDFs con pie de marca).

**En curso / pendiente real** (ver `docs/PENDIENTES_CLINICOS.md` para el detalle y
el motivo de cada uno):
- Palabra de activación "Dentia" entrenada con audio real del consultorio —
  bloqueado: necesita grabaciones reales que todavía no existen.
- Esquema LLM dinámico por pantalla/rol para Dentia (diseñado, no implementado).
- Varias decisiones clínicas marcadas como "valor provisional, falta validar con
  el odontólogo" (p. ej. catálogo de diagnósticos, duración por defecto de citas).
- Multi-sucursal con marca distinta por sucursal en el login (hoy usa la más
  antigua) — solo importa si una organización real lo necesita.

## Seguridad
Secretos en `.env` (nunca en git). `JWT_SECRET` obligatorio en producción (no
arranca con el valor de ejemplo). Toda consulta por ORM o parametrizada, toda
entrada validada con Pydantic. Rate limiting en login. Seeds usan datos ficticios
(Faker es_MX) — **nunca datos reales de pacientes**. Revisión OWASP completa en
`docs/SEGURIDAD.md`.
