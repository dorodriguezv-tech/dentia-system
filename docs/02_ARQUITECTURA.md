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
| `records` | MedicalHistory, Allergy, Medication, RiskFactor, ClinicalAlert, VitalSigns, FamilyHistoryEntry, PersonalPathologicalHistory, PersonalNonPathologicalHistory, SystemsReviewEntry (Fase A) |
| `odontological_history` | OdontologicalExam, PeriodontalAnamnesis, RadiographicAnalysis, OdontogramDiagnosisDetail, ParallelometerAnalysis, RemovablePartialDentureDesign, ToothDiagnosisEntry, ToothTreatmentPlanEntry (Fase C) |
| `pediatric_history` | PediatricPerinatalHistory, PediatricOralHabits, PediatricBehaviorMaturity, PediatricOcclusion, PediatricEruptionDentition, PediatricToothAnnotation (Fase E) |
| `endodontic_history` | EndodonticInterrogation, EndodonticPulpSensitivityTest, EndodonticPeriodontalTest, EndodonticRadiographicInterpretation, EndodonticDiagnosisTreatment, EndodonticToothDiagnosisCode, EndodonticWorkingLength (Fase F) |
| `periodontogram` | PeriodontalProbingSite, PeriodontalToothMeasurement, PeriodontalIndexEntry, OcclusalContactEntry, PeriodontogramObservation (Fase G) |
| `encounters` | Encounter, ClinicalNote (+ ClinicalNoteVersion) |
| `odontogram` | ToothCatalog, SurfaceCatalog, FindingCatalog, ToothFinding (evento), OdontogramSnapshot |
| `agenda` | Provider, Resource (gabinete), Appointment, AppointmentStatusHistory |
| `diagnosis` | DiagnosisCatalog, Diagnosis |
| `treatment` | ProcedureCatalog, PriceList, TreatmentPlan, TreatmentPhase, ProcedurePlanned, ProcedurePerformed, PlanAcceptance |
| `documents` | DocumentTemplate (versionada), Consent |
| `imaging` | Image (metadatos + pieza/procedimiento) |
| `billing` | Charge, Payment, PaymentAllocation, CashSession, ClinicBillingSettings |
| `reports` | Vistas/consultas de solo lectura |
| `audit` | AuditEvent |
| `version_info` | Sin tablas propias — `GET /version-info` expone `Settings.app_version`/`environment` (solo lectura, panel de administrador) |

`app/ai/` (Fase 8) no vive en `app/modules/`: es su propio paquete de nivel superior
(`stt.py`, `dental_parser.py`, `ollama_client.py`, `actions.py`, `interpreter.py`,
`applier.py`, `service.py`, `router.py`, `models.py`, `prompts/`), tal como lo describe
CLAUDE.md sec. 3. Entidades: `AiSuggestion`, `AiClinicSettings`.

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
`id, clinic_id, patient_id, encounter_id, batch_id, action_type, payload (jsonb), status (PENDING/ACCEPTED/REJECTED), model_name, model_digest, transcript_excerpt, created_by, created_at, reviewed_by, reviewed_at, reject_reason`

Una fila por **acción**, no una fila con la lista completa del dictado: `batch_id` agrupa
las que vinieron de la misma llamada a `POST /ai/interpret` solo para mostrarlas juntas en
el panel, pero cada una se acepta/edita/rechaza por separado. No hay `confidence` ni
`EXPIRED` (el modelo de Ollama no da una puntuación de confianza utilizable, y nada expira
sugerencias automáticamente todavía — ver `docs/PENDIENTES_CLINICOS.md`). Tampoco hay
`applied_entity_type`/`applied_entity_id`: esa trazabilidad vive en el `AuditEvent
ai.suggestion_accepted` que crea `applier.py` (`entity_type`/`entity_id` de la fila que
realmente se creó).

### DocumentTemplate y Consent (Fase 9)
`DocumentTemplate`: `id, clinic_id, code, name, version, html_content, supersedes_id, is_current`
-- versionada como `ToothFinding` (regla 7): editarla crea una fila nueva con `version`
incrementada, nunca sobrescribe `html_content`.

`Consent`: `id, clinic_id, patient_id, encounter_id, template_id, procedure_planned_id?,
treatment_plan_id?, professional_id, signer_name, signer_relationship, signature_path,
pdf_path, content_hash (sha256), signed_at, is_active, annul_reason?`
-- se crea ya firmado (capturar la firma y generar el PDF es un solo acto atómico);
despues no se edita, solo se anula con motivo (regla 2). `template_id` apunta a la
versión exacta de la plantilla usada, no al código, para que un cambio de plantilla
posterior no altere retroactivamente lo que un paciente ya firmó.

### Image (Fase 9)
`id, clinic_id, patient_id, encounter_id, study_type, tooth_fdi?, procedure_planned_id?,
procedure_performed_id?, file_path, thumbnail_path?, content_type, original_filename,
notes?, is_active, annul_reason?`
-- una fila por archivo: "carga múltiple" es el endpoint aceptando varios archivos en una
peticion con los mismos metadatos, no una entidad "estudio" separada.

### Charge, Payment y PaymentAllocation (Fase 10)
`Charge` (desde la Fase 7) gana columnas de cancelacion (`is_active, cancel_reason,
cancelled_by, cancel_authorized_by, cancelled_at`, regla 2) pero su `status` original
("SUGERIDO") ya no se usa para mostrar el estado de cobro: se calcula en caliente a
partir de `PaymentAllocation` (`rules.charge_computed_status`), nunca se guarda.

`Payment`: `id, clinic_id, patient_id, cash_session_id?, method (efectivo/tarjeta/
transferencia), amount, received_at, reference?, notes?, is_active, cancel_reason?` --
puede no tener ninguna aplicacion (anticipo: credito del paciente). `PaymentAllocation`:
`id, clinic_id, payment_id, charge_id, amount_applied` -- aplica (total o parcialmente)
un pago a un cargo; si el pago se cancela, sus aplicaciones no se borran (regla 2), se
excluyen del saldo calculado porque `Payment.is_active` pasa a `False`.

`CashSession`: `id, clinic_id, opened_by, opened_at, opening_amount, status (ABIERTA/
CERRADA), closed_by?, closed_at?, closing_amount?, notes?` -- corte de caja por sesion;
la diferencia contra lo esperado (apertura + cobros en efectivo de la sesion) se calcula
en el servicio, no se guarda.

`ClinicBillingSettings`: `clinic_id (PK), billing_enabled, updated_at, updated_by` --
una fila por sucursal (mismo patron que `ClinicBranding`/`AiClinicSettings`): la
cobranza se puede desactivar por sucursal (p.ej. clinicas universitarias de practica
que no cobran de verdad) sin tocar el resto del flujo clinico.

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
| POST | /auth/login, /auth/login/mfa, /auth/refresh, /auth/logout | Autenticación (JWT + rotación de refresh) |
| POST | /auth/mfa/setup, /auth/mfa/enable, /auth/mfa/disable | MFA TOTP (obligatoria para admin_clinica) |
| GET | /me, /me/clinics | Usuario autenticado y sus sucursales (selección de sucursal) |
| GET/POST/PATCH | /users (scope por header `X-Clinic-Id`) | Gestión de usuarios de la clinica (permiso `iam.manage_users`) |
| GET/PUT | /branding (GET público) | Tema y marca de la sucursal (permiso `branding.manage`) |
| POST/GET | /branding/logo, /branding/favicon | Subir logo (sanea SVG, genera favicon) y servirlo (publico) |
| GET | /health | Estado del servicio (sin autenticacion) |
| GET/POST/PATCH | /patients, /patients/search?q=, /patients/duplicates-check, /patients/{id} | Pacientes (alta, edicion controlada, busqueda tolerante, duplicados) |
| GET | /patients/{id}/summary | Encabezado persistente (nombre, edad, alertas) |
| GET/POST/PATCH/DELETE | /patients/{id}/contacts | Tutor/responsable y contacto de emergencia |
| POST/GET | /patients/{id}/photo | Foto del paciente (permisionada, no publica) |
| CRUD | /patients/{id}/history, /allergies, /medications (+/{id}/annul); /vital-signs | Expediente clínico |
| GET | /patients/{id}/alerts | Alertas críticas derivadas (alergias/medicamentos/antecedentes) |
| POST/GET | /encounters, /encounters/{id}, /patients/{id}/encounters, /patients/{id}/timeline | Atenciones y línea de tiempo |
| POST/GET/PATCH | /encounters/{id}/notes, /notes/{id} | Nota clínica SOAP (autoguardado) |
| POST | /notes/{id}/finalize, /notes/{id}/correct, /notes/{id}/cancel | Transiciones de la nota (regla 1) |
| GET | /patients/{id}/odontogram?at=fecha | Estado vigente o a una fecha (reconstruido) |
| POST | /tooth-findings | Registrar evento (supersede al vigente de esa pieza/superficie/tipo) |
| GET | /patients/{id}/teeth/{tooth_fdi}/history | Historial completo de una pieza, con autor |
| GET/POST | /providers, /resources; /providers/{id}/working-hours, /providers/{id}/blocks | Agenda: catálogos |
| GET/POST | /appointments; PATCH /appointments/{id}/status; POST /appointments/{id}/reschedule | Citas y su máquina de estados |
| POST | /appointments/{id}/start-encounter | Crea el `Encounter` desde la cita (permiso `records.write`) |
| GET/POST | /appointments/{id}/reminders; /waitlist | Recordatorios (solo registro) y lista de espera |
| GET/POST | /patients/{id}/diagnoses; POST /patients/{id}/diagnoses/{id}/annul | Diagnósticos |
| GET/POST | /procedure-catalog | Catálogo de procedimientos y precios por sucursal |
| GET/POST | /patients/{id}/treatment-plans; GET /treatment-plans/{id} | Planes de tratamiento |
| PATCH/POST | /treatment-plans/{id}/status\|accept; /phases; /phases/{id}/items; /items/{id}/annul\|discount | Fases, ítems, aceptación y descuentos del plan |
| GET | /treatment-plans/{id}/pdf | PDF del presupuesto con el logo de la clínica |
| POST/GET | /procedures-performed; /patients/{id}/procedures-performed | Procedimientos realizados (regla 3) |
| GET | /patients/{id}/charges | Cargos, con saldo y estado calculados contra los pagos aplicados (regla 4) |
| POST | /ai/transcribe, /ai/interpret | Voz a texto y texto a propuestas de acción |
| GET | /ai/suggestions?encounter_id= | Propuestas pendientes de una atención |
| POST | /ai/suggestions/{id}/accept\|reject | Aplica (regla 9) o descarta una propuesta |
| GET | /ai/status; GET/PUT /ai/settings | Estado de Ollama/Whisper; modelo preferido por sucursal (permiso `ai.configure`) |
| GET/POST | /document-templates; /document-templates/{code}/history | Plantillas de consentimiento, versionadas (regla 7) |
| GET/POST | /patients/{id}/consents | Firmar un consentimiento (genera el PDF y el hash en el mismo acto) |
| GET | /consents/{id}/pdf | PDF firmado (lectura auditada) |
| POST | /consents/{id}/annul | Anula un consentimiento con motivo (regla 2) |
| POST/GET | /patients/{id}/images | Subir (uno o varios archivos) y listar imágenes/radiografías |
| GET | /images/{id}; /images/{id}/thumbnail | Archivo completo (lectura auditada) y miniatura |
| POST | /images/{id}/annul | Anula una imagen con motivo (regla 2) |
| POST | /charges/{id}/cancel | Cancela un cargo sin pagos aplicados, con motivo (regla 2) |
| GET/POST | /patients/{id}/payments | Pagos del paciente (con o sin aplicación a un cargo = anticipo) |
| GET | /payments/{id}/receipt | Recibo PDF con el logo de la clínica |
| POST | /payments/{id}/cancel | Cancela un pago con motivo; restaura el saldo del cargo (regla 2) |
| GET | /patients/{id}/billing-summary | Total cargado, pagado, crédito y saldo pendiente |
| POST | /cash-sessions/open\|{id}/close; GET /cash-sessions/current\|{id} | Corte de caja por sesión |
| GET/PUT | /billing/settings | Activar/desactivar la cobranza de la sucursal (permiso `billing.configure`) |
| GET | /reports/patients\|appointments\|production\|treatment-plans\|ai-usage?date_from=&date_to= | Reportes con rango de fechas (permiso `reports.read`) |
| GET | /reports/accounts-receivable | Cuentas por cobrar (fotografía actual, sin rango de fechas) |
| GET | /reports/{reporte}/export | Exporta el mismo reporte como CSV (lectura auditada, `reports.export`) |
| GET | /reports/dashboard | Tablero de inicio por rol (solo autenticación; cada sección se filtra por su propio permiso) |
| GET | /audit?patient_id=&user_id=&from=&to= | Auditoría |

### 5.1 Autenticación y autorización (Fase 1)
- **JWT:** access token (15 min) firmado HS256 + refresh token opaco (8 h) guardado hasheado
  (SHA-256) en `refresh_tokens`, con rotación: cada `/auth/refresh` revoca el anterior y emite uno
  nuevo (`replaced_by_id`).
- **MFA:** TOTP (`pyotp`). Opcional por usuario; obligatoria para `admin_clinica` — el login no se
  bloquea antes de configurarla (no hay forma de configurarla sin iniciar sesión primero), pero
  `UserOut.mfa_setup_required` se marca `true` hasta que la activa, y no se puede desactivar
  mientras el rol la exija.
- **Rate limiting del login:** 5 intentos fallidos en 15 minutos por correo (consulta sobre
  `audit_events`, sin tabla ni servicio adicional).
- **ABAC por sucursal:** el cliente envía el encabezado `X-Clinic-Id` con la sucursal activa
  (elegida tras `/me/clinics`). `require_permission("modulo.accion")` verifica
  `UserClinic(user, clinic) → Role → RolePermission → Permission.code` antes de autorizar.
- **superadmin sin acceso clínico (regla 5 de CLAUDE.md):** no es un bypass en código; el
  catálogo de permisos (`docs/MATRIZ_PERMISOS.md`) simplemente no le asigna ningún permiso
  `patients.*`, `records.*`, `odontogram.*`, etc.
- **Auditoría:** `AuditEvent` es append-only (trigger de PostgreSQL que bloquea UPDATE/DELETE).
  Un middleware registra `access_denied` en cada respuesta 403.
- **`Clinic.timezone` (agregado al corregir el bug #42 de
  `docs/PENDIENTES_CLINICOS.md`, probando la Fase 13):** nombre de zona
  horaria IANA (`America/Mexico_City` por defecto), editable por
  `admin_clinica` vía `PATCH /clinics/current` (mismo endpoint de B1 que ya
  editaba nombre/dirección/teléfono), validado contra `zoneinfo`
  (`iam/rules.py::is_valid_timezone`) — un valor inválido devuelve 422, no
  se guarda a ciegas. Lo usa `app/voice/dialogue.py` para calcular "de qué
  día" es una cita/atención (ver sec. 5.19); las columnas de agenda/
  encuentros siguen siendo `TIMESTAMPTZ` en UTC como siempre, solo cambia
  CON QUÉ zona se interpreta "hoy" y "medianoche". Requiere `tzdata` en
  Windows (fijado en `requirements.txt`: el sistema no trae la base IANA,
  a diferencia de Linux/Mac).

### 5.2 Tema y marca (Fase 2; marca DENT-IA: docs/CAMBIOS_WEB_MARCA.md W1–W7)
- **Catálogo único:** `backend/app/modules/branding/presets.py` es la fuente de verdad de los
  7 presets (`dentia` primero y por defecto, luego los 6 originales) y de los colores
  compartidos (`frontend/src/theme/presets.ts` es su copia para la UI, igual que el patrón ya
  usado con el catálogo de permisos de IAM). Un preset puede traer su propio
  `surface`/`border`/`text`/`text_muted` (el preset `dentia` lo hace); si no los trae,
  `full_palette()`/`fullPalette()` usan los compartidos. `DEFAULT_PRESET = "dentia"` es solo el
  valor por defecto para sucursales **nuevas**: no hay migración que reescriba el preset de una
  sucursal que ya eligió otro (`clinic_branding.preset` nunca tuvo `server_default` en la base,
  es un `default` de SQLAlchemy a nivel aplicación).
- **`GET /branding` es público** (lo necesita la pantalla de login antes de autenticar) y
  resuelve "la" sucursal como la más antigua (`clinics.created_at`); ver pendiente #12 en
  `docs/PENDIENTES_CLINICOS.md` para multi-sucursal. Sin branding configurado, `display_name`/
  `subtitle` son **"DENT-IA"** / **"Sistema Inteligente de Gestión Odontológica"** (ya no el
  nombre de la sucursal): es la identidad de producto por defecto hasta que el admin la
  personaliza en Configuración → Apariencia.
- **`has_custom_logo`:** `GET /branding/logo` y `/branding/favicon` ya no responden 404 — sin
  logo propio sirven `branding/default_assets/dentia-{logo,favicon}.png`. `has_custom_logo`
  (en `BrandingOut`) es la única forma de saber si el logo mostrado es el de la sucursal o el de
  DENT-IA; el frontend (`<ClinicLogo>`/`<PoweredByDentia>`, `src/components/brand/Brand.tsx`) y
  la app móvil (`src/components/Brand.tsx`) lo usan para decidir si mostrar "con tecnología
  DENT-IA" debajo del logo propio.
- **Derivación de color:** `--color-primary-hover`/`-soft` (y `-danger-soft`) nunca se guardan;
  se calculan en el cliente (`theme/colorUtils.ts`) cada vez que se aplica el tema, con la misma
  fórmula HSL que el backend (`color_utils.py`) usa para sugerir ajustes de contraste.
- **Contraste WCAG:** `PUT /branding` siempre guarda lo que mandó el admin (no lo rechaza) pero
  devuelve `contrast_warnings` con el color sugerido si texto/fondo o texto-de-boton/primario
  bajan de 4.5:1; la pantalla de Apariencia calcula lo mismo en vivo mientras se edita. El preset
  `dentia` pasa este chequeo sin advertencias (primario ≥4.5:1 contra blanco y contra su `bg`).
- **Modo oscuro:** no hay una paleta oscura dibujada a mano por preset; se usa una base neutra
  oscura fija (`DARK_OVERRIDES` en el frontend) y se conservan secondary/accent/success/warning/
  danger del preset. El primario SÍ cambia: si el preset trae `dark_primary` (opcional, el
  preset `dentia` lo trae: `#4FC3D9`) se usa ese; si no, `theme/store.ts` lo deriva con
  `suggestContrastingColor` hasta 4.5:1 contra la superficie oscura — mismo criterio que usa
  `mobile/src/theme/theme.tsx` (`DENTIA_BRAND.primaryDark`).
- **Logo:** PNG/JPG/SVG, máximo 1 MB. El SVG se sanea con `xml.etree` (quita `<script>`,
  `<foreignObject>`, `<style>`, atributos `on*` y `javascript:`) en vez de rechazarse. El favicon
  se genera con Pillow (PNG/JPG a 64×64) o reutiliza el SVG saneado. Los archivos se sirven por
  `GET /branding/logo` y `/branding/favicon`, publicos a propósito (son la imagen de marca, no
  datos clínicos) — a diferencia de `storage/` en general, que nunca se sirve como estático.
- **PDF de marca (W3):** los tres generadores (`treatment/pdf.py` presupuesto,
  `billing/pdf.py` recibo, `documents/pdf.py` consentimiento) agregan el pie "Generado con
  DENT-IA · Sistema Inteligente de Gestión Odontológica" (gris `#4F6676`, 7 pt) en cada página;
  en presupuesto/recibo es un callback de canvas de reportlab (`onFirstPage`/`onLaterPages`), en
  el consentimiento es un `@frame` estático de xhtml2pdf **fuera** de `<div>{body}</div>` (el
  contenido que se hashea) para no mezclarse con lo que el paciente/tutor firmó — aunque en la
  práctica `content_hash` se calcula sobre el PDF ya renderizado y un consentimiento firmado
  nunca se regenera (`get_consent_pdf` solo lee los bytes guardados), así que esto no afecta
  documentos ya firmados (regla 7).

### 5.3 Pacientes (Fase 3)
- **Expediente:** `clinics.next_patient_number` es un contador por sucursal (se incrementa con
  `SELECT ... FOR UPDATE` en la misma transacción del alta, sin condición de carrera) formateado
  como `000001`, `000002`, ...
- **Búsqueda tolerante a errores:** extensiones `pg_trgm` + `unaccent` de PostgreSQL. El nombre
  completo se indexa con un índice GIN sobre `immutable_unaccent(lower(full_name))`.
  `immutable_unaccent` es un envoltorio SQL propio porque `unaccent()` es `STABLE`, no
  `IMMUTABLE` (Postgres lo exige para indexar una expresión), y además debe llamar a
  `public.unaccent(...)` con el esquema explícito: al expandir la función en línea para
  `CREATE INDEX`, Postgres resuelve nombres sin usar el `search_path` de la sesión, así que
  `unaccent` a secas no se encuentra ahí aunque funcione en una consulta normal (es un
  comportamiento real de Postgres, no un error de la app — reproducible incluso por `psql` puro).
- **Detección de duplicados:** `POST /patients/duplicates-check` exige coincidencia de fecha de
  nacimiento o teléfono **además** de similitud de nombre (`pg_trgm` > 0.4); sin uno de esos dos
  datos no hay forma confiable de comparar y la búsqueda no se ejecuta. El alta en el frontend
  llama a este endpoint antes de crear y obliga a confirmar explícitamente si aparecen
  candidatos.
- **Edición controlada:** cambiar `status` por `PATCH /patients/{id}` exige `status_reason`
  (422 si falta); el cambio queda en el detalle del `AuditEvent` (`from`, `to`, `reason`).
- **Lectura auditada:** `GET /patients/{id}` crea un `AuditEvent` `patients.read` en cada
  llamada (regla de CLAUDE.md sec. 5); `GET /patients` (listado) y `/search` no, porque no
  abren la ficha de un paciente concreto.
- **Foto del paciente:** a diferencia del logo de marca, **no** es pública (dato sensible del
  expediente). `GET /patients/{id}/photo` exige `patients.read`, así que el frontend no puede
  usar un `<img src>` directo: la pide con `fetch` autenticado y la muestra como blob URL
  (`api/client.ts: apiRequestBlobUrl`).
- **`patient_type` (pediátrico/adulto), anotación editable, no un campo derivado:** columna
  nullable (`patients/models.py`, migración `9c1fdb20d7bc`). Al crear o editar un paciente, si
  `patient_type` llega `None`/ausente en el payload, `patients/service.py` lo calcula con
  `rules.calculate_patient_type(date_of_birth)` (reutiliza `calculate_age`; corte de
  `PEDIATRIC_AGE_CUTOFF_YEARS = 12`, no validado con la clínica real — ver pendiente #73 de
  `docs/PENDIENTES_CLINICOS.md`). Si se especifica explícitamente, se respeta y **no** se vuelve a
  calcular después (mismo patrón que los demás campos opcionales de `PatientUpdateRequest`: `None`
  en una edición posterior significa "no tocar", no "recalcular"). El teléfono y el correo del
  paciente son y siempre fueron opcionales en el esquema (`str | None`) — el frontend ahora lo
  deja explícito con un texto de ayuda cuando el tipo es pediátrico, en vez de que el formulario
  luzca como si fueran obligatorios por omisión.

### 5.4 Expediente, atención y notas (Fase 4)
- **Catálogos configurables (sec. 7 de CLAUDE.md):** `records/rules.py` define 6 categorías de
  antecedente (heredofamiliar, personal patológico, personal no patológico, odontológico, hábito,
  factor de riesgo), 3 niveles de severidad de alergia (leve/moderada/severa) y dos diccionarios
  palabra-clave → etiqueta (`CONDITION_ALERT_KEYWORDS`, `MEDICATION_ALERT_KEYWORDS`) usados para
  derivar alertas a partir de antecedentes y medicamentos en texto libre. Los catálogos no están
  validados clínicamente todavía; ver pendiente en `docs/PENDIENTES_CLINICOS.md`.
- **Anulación, no borrado (regla 2):** `MedicalHistory`, `Allergy` y `Medication` usan
  `_AnnullableMixin` (`is_active`, `annul_reason`, `annulled_by`, `annulled_at`); `VitalSigns` es
  un registro de solo-append (sin anulación, es una medición puntual, no una afirmación clínica
  que se pueda "retractar"). Todos exigen `encounter_id` (no hay antecedente/alergia/medicamento
  sin un contexto de atención, regla 6).
- **Alertas clínicas derivadas, no almacenadas (regla 8):** `records.service.get_patient_alerts`
  no es una tabla; se recalcula en cada llamada a partir de alergias activas (siempre alertan, con
  su severidad), y coincidencias de palabra clave (sin acentos, sin mayúsculas) contra medicamentos
  y antecedentes activos. La reutiliza tanto `GET /patients/{id}/summary` (barra de alertas del
  encabezado) como `GET /patients/{id}/alerts` (modal de confirmación antes de finalizar una nota).
- **Máquina de estados de la nota clínica (regla 1):** `encounters/rules.py` define las
  transiciones válidas DRAFT→{FINAL,CANCELLED}, FINAL→{CORRECTED,CANCELLED}; CORRECTED y CANCELLED
  son terminales. `is_editable` solo permite PATCH en DRAFT (403 `NOTE_NOT_EDITABLE` en cualquier
  otro estado — probado explícitamente con una prueba de integración dedicada). `correct_note` no
  modifica la nota FINAL: la marca CORRECTED y crea una fila nueva DRAFT con
  `version = anterior + 1`, `previous_version_id` apuntando a la vieja y `correction_reason` en la
  nueva fila (el motivo describe la corrección, no el estado anterior). `finalize_note` calcula
  `content_hash` (SHA-256 de los 5 campos SOAP/texto libre, regla 7) y exige
  `alerts_acknowledged: true` en el body (400 `ALERTS_NOT_ACKNOWLEDGED` con el detalle de alertas si
  el paciente tiene alguna activa y no se confirmó) — la validación vive en el backend, no solo en
  la UI.
- **`Encounter.appointment_id`:** columna nullable sin FK todavía; la tabla `appointments` llega en
  la Fase 6 (Agenda). Se deja preparada para no requerir una migración de columna después.
- **Dos bugs de raíz corregidos durante esta fase** (no específicos de un endpoint, afectaban a
  cualquier módulo futuro con el mismo patrón):
  1. *Autogenerate destructivo:* el modelo `Patient` nunca declaraba `uq_patient_expediente_per_clinic`
     (solo existía en la migración de la Fase 3) ni podía declarar el índice trigram (depende de la
     función `immutable_unaccent`, no expresable en el ORM). Alembic autogenerate los marcaba para
     `DROP` en cada migración nueva. Se añadió el `UniqueConstraint` al modelo (con comentario
     explicando que el índice trigram seguirá marcándose y debe limpiarse a mano) y se verificó con
     un ciclo upgrade→downgrade→upgrade que ambos sobreviven.
  2. *`MissingGreenlet` en cualquier columna con `onupdate=func.now()`:* SQLAlchemy async marca esas
     columnas como "expiradas" tras un `UPDATE`; `Pydantic.model_validate(orm_obj)` fuera de una
     sesión async dispara un lazy-load síncrono y revienta. Se corrigió una sola vez y para siempre
     con `Base.__mapper_args__ = {"eager_defaults": True}` en `core/db.py` (usa `RETURNING` para
     traer los valores generados por el servidor en el mismo `flush`), en vez de parchear cada
     schema que expusiera `updated_at`.
- **Frontend:** `PatientDetailPage` es ahora un shell con dos pestañas — `ResumenTab` (datos
  generales, foto, cambio de estado, contactos, línea de tiempo clínica con botón "Iniciar
  atención") y `ExpedienteTab` (secciones colapsables de antecedentes/alergias/medicamentos/signos
  vitales, cada una con su propio selector de atención para asociar el registro nuevo). La pantalla
  de atención (`AtencionPage`, ruta `/pacientes/:patientId/atencion/:encounterId`, protegida a
  `odontologo`/`especialista`) edita el SOAP de la nota activa con autoguardado cada 10 s mientras
  está en DRAFT, bloquea la finalización con un modal si hay alertas activas sin confirmar, y ofrece
  Corregir/Cancelar con motivo obligatorio; las versiones anteriores de la nota se listan de solo
  lectura debajo.

### 5.5 Odontograma (Fase 5; figura anatómica y paleta reconciliadas en la Fase B)
- **Catálogos configurables (sec. 7):** `odontogram/rules.py` genera las 32 piezas FDI permanentes
  (11–48) y las 20 temporales (51–85) por fórmula (no a mano); calcula las 5 superficies clicables
  de cada pieza (P solo en piezas superiores, L en inferiores; I solo en anteriores —incisivos y
  canino—, O en posteriores). `odontogram/finding_catalog.py` trae los 13 hallazgos por defecto
  (sano, caries, restauración, corona, endodoncia, ausente, extracción indicada, implante, prótesis
  fija, sellador, fractura, movilidad, biopelícula/tártaro dental) con color y símbolo.
- **Paleta reconciliada con la leyenda oficial (Fase B, cierra el pendiente #3 de
  `docs/PENDIENTES_CLINICOS.md`):** los formatos de `docs/clinica` ("ODONTOGRAMA DE DIAGNÓSTICO",
  presente en ambos PDF de referencia) traen una leyenda fija de 4 colores: rojo = caries, azul =
  prótesis y restauraciones, negro = dientes ausentes o restos radiculares, verde = biopelícula y
  tártaro dental. Para que el catálogo coincidiera se cambió `ausente` de gris (`#8C8C8C`) a negro
  (`#1A1A1A`, no `#000` puro para no leerse como "color sin definir") y se agregó el hallazgo nuevo
  `biopelicula_tartaro` (verde `#6AB04C`, el mismo que antes tenía `sellador`); `sellador` se
  reasignó a magenta (`#A8407D`) para no competir visualmente con la leyenda oficial.
  `restauracion`/`protesis_fija` (misma familia de azules) y `caries`/`extraccion_indicada` (mismo
  rojo) ya coincidían y no se tocaron. El resto de hallazgos no cambia de color. Mismo patrón que
  cualquier otro cambio de catálogo (sec. 7): hay que tocar 5 lugares de forma consistente —
  `app/seed.py::CATALOG_SEEDS`, una migración nueva de backfill para clínicas ya existentes
  (`9b1f4c7a0e2d`, nunca se edita una migración vieja ya corrida — regla general de este proyecto),
  `odontogram/finding_catalog.py`, `frontend/src/modules/odontogram/findingCatalog.ts` y las
  variables `--color-finding-*` de `frontend/src/theme/tokens.css`.
- **`ToothFinding` como eventos, nunca sobrescritos (regla 5):** cada hallazgo nuevo para la misma
  `(paciente, pieza, superficie, tipo)` marca `is_current=False` en el anterior y guarda
  `supersedes_id` apuntando a él; el historial completo nunca se borra. Un índice único parcial en
  Postgres (`ux_tooth_findings_current`) impide tener dos hallazgos vigentes a la vez para la misma
  clave — usa `COALESCE(surface, '')` para que "toda la pieza" (superficie `NULL`, p.ej. una pieza
  ausente) cuente como un valor concreto, porque Postgres no trata dos `NULL` como iguales en un
  índice único por defecto (mismo patrón que `immutable_unaccent` en la Fase 3: una función SQL en
  la expresión del índice).
- **`EXISTING` / `PLANNED` / `PERFORMED` son cadenas independientes:** la clave de unicidad incluye
  el tipo, así que un hallazgo `PLANNED` (Fase 7, plan de tratamiento) y uno `EXISTING` para la
  misma pieza/superficie coexisten sin pisarse — el planificado no se confunde con lo ya existente
  (precedente de la regla 3). Esta fase solo crea `EXISTING` desde la UI; `PLANNED`/`PERFORMED`
  quedan listos en el modelo para cuando Fase 7 los produzca.
- **`GET /patients/{id}/odontogram?at=YYYY-MM-DD` reconstruye el estado histórico:** trae todos los
  eventos con `created_at <= at` ordenados ascendente y, por cada `(pieza, superficie, tipo)`, se
  queda con el más reciente — sin esto, `is_current` por sí solo no alcanza para "cómo se veía la
  pieza hace 3 meses", porque un hallazgo pudo haber sido reemplazado desde entonces. Sin `at`, usa
  el camino rápido de filtrar por `is_current=True`.
- **Un hallazgo de "toda la pieza" reemplaza, no combina, la vista de esa pieza:** si existe un
  evento vigente con `surface=NULL` (p.ej. ausente, implante), el frontend dibuja un solo recuadro
  para toda la pieza en vez de las 5 zonas; los hallazgos por superficie que pudieran seguir
  vigentes para esa misma pieza no se anulan automáticamente al registrar el de toda la pieza (no
  hay cascada) — coexisten en la base aunque la UI solo muestre uno. Ver pendiente #15.
- **Frontend — SVG propio sin librerías de terceros:** `Tooth.tsx` sigue dibujando exactamente los
  mismos 5 `<rect>` clicables de siempre, en el mismo orden del DOM y con las mismas coordenadas
  (arriba=V, abajo=P/L según si la pieza es superior o inferior, centro=O/I según sea posterior o
  anterior, izquierda/derecha=M/D según el lado de la arcada) — eso no cambió en la Fase B, solo
  cómo se dibujan alrededor. El color de cada hallazgo se aplica vía
  `fill="var(--color-finding-<codigo>)"` (variables en `theme/tokens.css`, semánticas y fijas como
  `--color-danger`, no derivadas de la marca de la clínica) — nunca un `#hex` literal en el
  componente (CLAUDE.md sec. 6). `kind="PLANNED"` se dibuja con `stroke-dasharray` (contorno
  discontinuo).
  **Silueta anatómica corona+raíz (Fase B):** antes un cuadrado abstracto de 44×44; ahora un
  `viewBox` de 44×66 con una raíz decorativa (no clicable, siempre `<path>`, nunca `<rect>` — así
  `querySelectorAll('rect')` en las pruebas sigue viendo exactamente los 5 de antes) que se afina
  hacia la encía: arriba de la corona en piezas superiores, abajo en inferiores (`toothVisualType`/
  geometría en `toothRules.ts`/`toothShapes.ts`). El grupo de los 5 `<rect>` se encoge horizontalmente
  (`crownScaleX`, centrado, sin tocar sus coordenadas ni su orden) según el tipo de pieza —
  `toothVisualType(toothFdi)`: anterior (incisivos+canino, corona angosta, 1 raíz), premolar (corona
  media, 1 raíz; en piezas temporales esas posiciones son molar, no existe premolar temporal), molar
  (corona completa, borde con 4 cúspides decorativas tipo "trébol" como en la vista oclusal del PDF
  de referencia; 2 raíces si es inferior, 3 si es superior —incluye una palatina central más corta—).
  No es una réplica anatómica literal de las 3 franjas del PDF (corona/oclusal/raíz apiladas): se
  combinó, a propósito, el mapa de superficies de siempre (vista "desde arriba") con un contorno y
  una raíz de estilo frontal — ese nivel de detalle real (franjas separadas, sondeo por sitio)
  quedó para el periodontograma, Fase G (backend completo, ver sección 5.26; el dibujo
  interactivo de 32 piezas × 6 sitios es un slice de frontend aparte), fuera de este encargo.
  `Arch.tsx`/`Odontograma.tsx` arman las arcadas superior/inferior y las vistas permanente/
  temporal/mixta (en mixta, la fila de temporales se dibuja sobre la de permanentes, pendiente #10).
  Elegir una pieza/superficie abre `FindingQuickMenu` (selector de atención + catálogo de hallazgos
  en botones de ≥44 px) y `ToothHistoryPanel` (historial completo de esa pieza, con autor). El
  control de fecha (`<input type="date">`) cambia `at` y pone la vista en solo lectura con un aviso.
  `Odontograma.tsx` también muestra la leyenda oficial de 4 colores tal como aparece literal en los
  PDF de referencia, además de la leyenda detallada por código de hallazgo que ya existía.

### 5.6 Agenda (Fase 6)
- **`Provider` distinto de `User`:** la identidad agendable (color del calendario, activo/inactivo)
  es una entidad propia del módulo `agenda`, enlazada 1 a 1 con un `User` de `iam` — así el módulo
  de agenda no depende del catálogo de roles para saber quién es agendable, y puede traer sus
  propios datos (color) sin tocar `iam`.
- **Máquina de estados de la cita (docs/02 sec. 4):** `agenda/rules.py` permite
  RESERVADA/CONFIRMADA → EN_SALA → EN_ATENCION → TERMINADA, pero también el salto directo
  RESERVADA/CONFIRMADA → EN_ATENCION (botón "Iniciar atención": EN_SALA es un paso opcional de sala
  de espera, no obligatorio). CANCELADA y NO_SHOW exigen motivo (422 `REASON_REQUIRED` si falta,
  mismo patrón que la anulación de registros clínicos). Cada transición queda en
  `AppointmentStatusHistory` (tabla propia, no solo `AuditEvent`).
- **Reprogramar nunca edita la cita vieja (regla 5, mismo espíritu que `ToothFinding`):**
  `POST /appointments/{id}/reschedule` marca la cita original como `REPROGRAMADA` (estado terminal)
  y crea una fila nueva en `RESERVADA` con `rescheduled_from_id` apuntando a la original — el
  horario viejo queda libre (ya no cuenta para la validación de traslapes) y el historial completo
  de reprogramaciones se conserva. El arrastrar-y-soltar del calendario en el frontend llama a este
  mismo endpoint, nunca a un PATCH directo de horario.
- **Traslapes en dos capas:** el servicio valida antes de insertar (`APPOINTMENT_CONFLICT`, 409) y,
  como respaldo ante una condición de carrera, dos restricciones `EXCLUDE` de Postgres
  (`ux_appointments_no_overlap_provider`/`_resource`) rechazan el `INSERT`/`UPDATE` aunque la
  validación de Python se saltara. Requieren la extensión `btree_gist` (permite mezclar `provider_id
  WITH =` con `tstzrange(...) WITH &&` en el mismo índice GiST, algo que Postgres no soporta para
  tipos no-rango sin ella) y un rango semiabierto `'[)'` para que una cita que termina justo cuando
  otra empieza no cuente como traslape. No son expresables en el ORM de SQLAlchemy: se agregan por
  SQL crudo en la migración, con el mismo patrón de comentario que `immutable_unaccent` (Fase 3) y
  el índice parcial de `tooth_findings` (Fase 5) para que un autogenerate futuro no intente tocarlas.
- **Horario laboral y bloqueos son informativos, no bloqueantes:** `ProviderWorkingHours` y
  `ProviderBlock` existen y se usan para avisar (`warnings` no bloqueantes en la respuesta de crear/
  reprogramar una cita, mismo patrón que los avisos de contraste WCAG de la Fase 2) si la cita cae
  fuera de horario o sobre un bloqueo, pero no impiden agendarla — decisión operativa pendiente de
  validar con la clínica (ver `docs/PENDIENTES_CLINICOS.md`).
- **Catálogo provisional de tipos de cita:** `APPOINTMENT_TYPES` en `agenda/rules.py` solo sirve
  para sugerir una duración por defecto (consulta 30 min, endodoncia 90 min, etc.); se unificará con
  el catálogo real de procedimientos y precios de la Fase 7.
- **Recordatorios idempotentes, sin envío real:** cada cita creada registra un `ReminderTask`
  (`kind="24h_antes"`) con una restricción única `(appointment_id, kind)`; por ahora solo se
  registran (`GET /appointments/{id}/reminders`), el envío real queda fuera de alcance de esta fase.
- **"Iniciar atención" exige `records.write`, no `agenda.write`:** aunque vive en el router de
  agenda, `POST /appointments/{id}/start-encounter` crea un `Encounter` (dato clínico), así que usa
  el mismo permiso que `POST /encounters` directo (Fase 4) — una recepcionista con `agenda.write`
  puede agendar y reprogramar, pero no iniciar la atención clínica.
- **Frontend — calendario propio sin librerías de terceros:** `CalendarGrid.tsx` dibuja un grid de
  franjas de 30 min (7:00–21:00) con los bloques de cita posicionados en `position: absolute` según
  su hora de inicio/duración; el arrastre usa la API nativa de HTML5 Drag and Drop
  (`draggable`/`onDragStart`/`onDrop`), sin biblioteca de calendario. `MonthGrid.tsx` es una vista
  mensual de solo resumen (un punto de color por cita) que navega al día al hacer clic. Los colores
  por estado usan `var(--color-status-*)` (nuevas en `theme/tokens.css`, semánticas y fijas como las
  de hallazgos del odontograma), nunca un `#hex` fijo en el componente. `AgendaPage.tsx` alterna
  vista día/semana/mes y agrupación por profesional o por gabinete.

### 5.7 Diagnóstico y tratamiento (Fase 7)
- **`diagnosis.read`/`treatment.read` no existían:** la Fase 1 sembró `diagnosis.write`,
  `treatment.write` y `treatment.accept_budget` anticipando esta fase, pero sin un permiso de solo
  lectura — un vacío real del catálogo original (`docs/MATRIZ_PERMISOS.md` no tenía filas para
  verlos). Se agregó con una migración incremental (`e4823992f9d7`) que solo inserta los dos
  permisos y sus asignaciones de rol, sin recrear el catálogo completo de la Fase 1.
  `treatment.read` también se le dio a `admin_clinica` (supervisa presupuestos sin poder crearlos).
- **`Diagnosis` reutiliza las reglas del odontograma para pieza/superficie:** `tooth_fdi`/`surface`
  son opcionales, pero si se da una pieza se valida con las mismas funciones de
  `odontogram/rules.py` (import cruzado entre módulos, mismo patrón que `agenda` reutilizando
  `encounters.service`). El texto siempre es libre; `code` es solo un atajo opcional al catálogo.
- **`ProcedureCatalog` vive en la BD, no en un catálogo Python:** a diferencia de los catálogos de
  fases anteriores (diagnósticos, hallazgos del odontograma, tipos de cita), el precio de un
  procedimiento varía por sucursal y debe poder editarse sin desplegar código — mismo criterio que
  ya se aplicó a `clinic_branding` en la Fase 2.
- **`ProcedurePlanned` y `ProcedurePerformed` son tablas separadas (regla 3):** realizar un
  procedimiento nunca actualiza la fila planificada ni le cambia un "estado" — crea una fila nueva
  en `procedures_performed`, opcionalmente enlazada por `planned_id`. Lo planificado queda igual
  para siempre en el historial del presupuesto, se haya realizado o no.
- **Reflejo en el odontograma, reusando la Fase 5 sin tocarla:** crear un `ProcedurePlanned` con
  pieza + `finding_code` llama a `odontogram_service.create_finding(kind="PLANNED", ...)`. Al
  registrar el `ProcedurePerformed` correspondiente, el servicio crea dos eventos más —
  `PERFORMED` (bitácora de que se hizo) y `EXISTING` (el estado real de la pieza cambió: ahora
  tiene esa restauración/corona/etc., y por el índice único parcial de la Fase 5 esto reemplaza
  automáticamente cualquier `EXISTING` previo de esa pieza/superficie) — y retira (`is_current =
  False`, sin fila nueva) el evento `PLANNED` que lo originó con `odontogram_service.retire_planned`
  (función nueva en el servicio de la Fase 5, no reescribe nada de ese módulo).
- **Un hallazgo de "toda la pieza" sigue tapando visualmente a los de superficie (pendiente #15 de
  Fase 5):** si el plan reflejó una corona `PLANNED` para la pieza completa, el odontograma muestra
  esa corona en vez de la endodoncia `EXISTING` que ya tiene esa misma pieza en una superficie —
  ambos hallazgos siguen vigentes en la base y aparecen en el historial de la pieza, solo cambia
  cuál se dibuja primero.
- **`Charge` es un modulo `billing` deliberadamente minimo (regla 4):** registrar un
  `ProcedurePerformed` genera un `Charge` con `status="SUGERIDO"` — nunca un pago, que no existe
  todavia como concepto. Es el mismo patron que `Encounter.appointment_id` en la Fase 4
  (declarar ahora lo minimo que una fase futura va a necesitar): la Fase 10 construye `Payment` y
  el resto de la cobranza sobre esta misma tabla, sin migrarla.
- **Aceptación total o parcial, por ítem:** `TreatmentPlan.accept` recibe la lista de
  `ProcedurePlanned.id` que el paciente acepta; cada ítem activo se marca `accepted = True/False` y
  el plan guarda `acceptance_type` ("TOTAL" si se marcaron todos los ítems activos, "PARCIAL" si
  no) junto con `accepted_by_name` (quien acepta es el paciente o su tutor, no hay portal ni firma
  electrónica todavía, así que el nombre se captura tal cual se dicta) y `accepted_at`.
- **PDF del presupuesto con el logo de la clínica:** `treatment/pdf.py` es una función pura
  (sin acceso a BD, se prueba sin fixtures) construida con `reportlab` — la única dependencia nueva
  de esta fase, sin stubs de tipos (`pyproject.toml` la ignora en mypy igual que cualquier librería
  sin `py.typed`). Reutiliza `branding_service.read_logo`/`get_branding` tal cual (Fase 2); si el
  logo es SVG (que branding sí acepta), reportlab no puede dibujarlo como raster y el PDF se genera
  igual, solo sin logo. El PDF exige el mismo token y `X-Clinic-Id` que el resto de la API, así que
  el frontend lo pide con `apiRequestBlobUrl` (igual que la foto del paciente, Fase 3) y abre la
  pestaña **antes** de esperar la respuesta (`window.open('', '_blank')` inmediato, luego
  `location.href` cuando llega el blob) para no perder el gesto del usuario y que el bloqueador de
  ventanas emergentes no lo descarte.
- **Bug de raíz corregido en `AccessDeniedAuditMiddleware` (no específico de esta fase):** guardaba
  la ruta completa de la petición en `AuditEvent.entity_id` (`String(100)`), que revienta en
  cualquier endpoint con dos segmentos UUID anidados — el primero en pisar el límite fue
  `POST /treatment-plans/{id}/phases/{id}/items` al probar un 403. `entity_id` es semánticamente el
  id de una entidad, no una URL; la ruta ahora va dentro de `details` (JSONB, sin límite de
  tamaño), junto con el método HTTP.
- **Frontend:** `ExpedienteTab` gana una quinta sección colapsable, "Diagnósticos", con el mismo
  patrón de catálogo-rápido-más-texto-libre que ya usan antecedentes y alergias. La pestaña nueva
  "Tratamientos" (no una sección de Expediente: tiene su propio flujo de estados y acciones) lista
  los planes del paciente y, al abrir uno, muestra fases con sus totales, el formulario de aceptar/
  rechazar con checkboxes por ítem, descuentos, "marcar como realizado" por ítem aceptado
  (comparando contra `GET /patients/{id}/procedures-performed` para no duplicar el registro) y el
  botón de descargar PDF.

### 5.8 Agente de IA por voz (Fase 8)
- **`origin` se extiende a todo lo que la IA puede crear (regla 10):** `ToothFinding` ya
  tenía esta columna desde la Fase 5 (anticipándola); esta fase agrega la misma columna
  (`String(15)`, default `"MANUAL"`) a `Allergy`, `Medication`, `MedicalHistory`,
  `VitalSigns`, `Diagnosis`, `ProcedurePlanned` y `ProcedurePerformed`, con el mismo tuple
  `ORIGINS = ("MANUAL", "AI_ASSISTED")` duplicado en cada `rules.py` (mismo patrón que
  `_AnnullableMixin`). Cada `create_*` de esos servicios gana un parámetro `origin: str =
  "MANUAL"` opcional, así que ningún llamador existente cambia. `set_chief_complaint`
  (un campo de `Encounter`, no una fila nueva) y `append_note` (texto agregado a una nota
  DRAFT ya existente) no tienen dónde guardar un origen propio; para esos dos, la
  trazabilidad de que vinieron de la IA vive solo en el `AuditEvent ai.suggestion_accepted`
  — ver pendiente en `docs/PENDIENTES_CLINICOS.md`.
- **Una fila de `AiSuggestion` por acción, nunca un lote:** `POST /ai/interpret` valida
  cada acción del JSON de Ollama por separado y crea una fila `PENDING` por cada una que
  pasa validación (`batch_id` compartido solo para agruparlas en el panel). Esto es lo que
  permite aceptar/editar/rechazar cada propuesta de un mismo dictado de forma independiente,
  tal como pide el panel "Propuestas del asistente" de docs/03.
- **Validación en dos capas, porque un `JSON Schema` no puede expresar todo:** `actions.py`
  define las 11 acciones como una unión discriminada por `"type"` (Pydantic) que se manda a
  Ollama como `format` en `/api/chat` — esto ya obliga la forma del JSON. Pero `procedure_code`
  no puede ser un `Literal` (es una tabla `procedure_catalog` por sucursal, no un catálogo
  fijo), así que `interpreter.py` valida cada acción aceptada por Pydantic otra vez contra
  los catálogos reales de la clínica (`_validate_against_real_catalogs`: pieza/superficie
  con `odontogram/rules.py`, `procedure_code` contra `treatment_service.list_procedure_catalog`).
  Lo que no pasa cualquiera de las dos capas va a `unrecognized`, nunca se descarta en
  silencio.
- **Acciones prohibidas se descartan por `"type"`, no solo por el esquema:** aunque el
  esquema que recibe Ollama ya excluye finalizar/firmar notas, borrar, recetar y cobrar
  (regla 9), `interpreter.py` igual revisa cada `"type"` crudo contra
  `rules.PROHIBITED_ACTION_TYPES` antes de intentar validarlo — por si el modelo alucina un
  tipo fuera del esquema declarado — y deja un `AuditEvent ai.prohibited_action_discarded`.
- **`applier.py` llama al servicio de dominio normal, nunca SQL directo:** aceptar una
  sugerencia arma el `*CreateRequest` del módulo correspondiente con `origin="AI_ASSISTED"`
  y llama al mismo `service.create_*` que usa un formulario manual — ninguna ruta de la IA
  escribe en una tabla clínica por su cuenta (prueba de integración dedicada que lo verifica
  explícitamente). `add_planned_procedure` necesita un plan y una fase donde vivir que el
  dictado no especifica: se reutiliza un plan `BORRADOR` de esa atención si ya existe, o se
  crea uno nuevo con una sola fase "General" (`_get_or_create_draft_plan_and_phase`) — ver
  pendiente. `append_note` reutiliza o crea la nota `DRAFT` de la atención y llama a
  `encounters_service.update_note` (respeta la regla 1: nunca toca una nota `FINAL`).
  `schedule_followup` es "solo propuesta" (docs/03 sec. 4): aceptarla no crea una cita real
  (la IA no tiene profesional/gabinete/horario para elegir), solo marca la sugerencia como
  revisada — ver pendiente.
- **Dos bugs de raíz encontrados probando contra Ollama real (no contra el `FakeOllama` de
  las pruebas automatizadas):**
  1. *Bucle de repetición infinito:* con `temperature=0` (exigido por docs/03 para que el
     mismo dictado siempre produzca el mismo resultado) y decodificación forzada por una
     gramática tan grande como la unión de 11 acciones, `qwen2.5:7b` a veces quedaba
     repitiendo el mismo objeto válido-pero-inútil sin parar — visto en vivo: más de 2700
     tokens generados antes de que el servidor de Ollama cortara la petición a los 2
     minutos. Se agregó `repeat_penalty=1.3` (penaliza tokens recientes, sigue siendo
     determinista) más `num_predict=800` como red de seguridad, para que un bucle que la
     penalización no alcance a romper termine en un error rápido en vez de agotar
     `OLLAMA_TIMEOUT_S` completo.
  2. *`add_vital_signs` como "salida gratis":* es la única de las 11 acciones con todos sus
     campos opcionales, así que un objeto con todo en `null` es válido para la gramática sin
     que el modelo tenga que extraer ningún dato real del dictado — y en pruebas reales el
     modelo lo usaba como salida de mínimo esfuerzo para dictados que no tenían nada que ver
     con signos vitales. Se agregó un `model_validator` a `AddVitalSignsAction` que exige al
     menos un valor no nulo; lo que antes se aceptaba como una sugerencia vacía ahora se
     rechaza en el servidor y el texto cae en `unrecognized` para revisión humana.
  3. `OLLAMA_TIMEOUT_S` subió de 60 a 120 (en `.env.example` y el default de `Settings`):
     con el prompt completo (catálogos reales + ejemplos few-shot) un modelo local de 7B a
     veces tarda más de 60 s incluso sin entrar en el bucle del punto 1.
  Con ambos fixes, el pipeline completo (transcripción real con faster-whisper, llamada
  real a Ollama, parseo, validación de catálogos, creación de `AiSuggestion`) corre de
  extremo a extremo sin errores; la **precisión** del modelo para elegir la acción correcta
  sigue siendo limitada con este modelo de 7B local — exactamente lo que `python -m app.ai.eval`
  existe para medir, y exactamente el caso para el que existe el flujo de aceptar/editar/
  rechazar (regla 9): una propuesta equivocada nunca se guarda sola, el odontólogo la
  rechaza o la corrige.
- **`dental_parser.py` resuelve números hablados a FDI antes de llamar a Ollama:** cubre
  dígitos ("36"), palabras compuestas ("treinta y seis"), irregulares (teens: "dieciocho";
  veintes: "veinticuatro") y dos unidades seguidas leídas como dígitos ("tres seis" = 36),
  con las palabras gatillo "pieza"/"diente"/"órgano dentario" o el artículo "la"/"el". El
  resultado (`build_hints`) se manda como pista en el prompt; es además la pieza con
  pruebas unitarias exhaustivas (28 casos, números 11 a 85 en varias formas) porque es
  determinista y no depende de Ollama.
- **`eval.py` + `tests/ai/corpus.jsonl` (50 dictados):** `python -m app.ai.eval` llama al
  Ollama real configurado (no el `FakeOllama` de pytest) con el mismo `system_es.md` que usa
  la app, y reporta precisión por tipo de acción y por pieza/superficie reconocida — la
  forma de medir mejoras futuras de prompt o de modelo sin depender de lectura manual.
- **`faster-whisper` necesitó dos ajustes de entorno, no de código, para funcionar en esta
  máquina Windows:** `av` (dependencia de `faster-whisper` para decodificar audio) no tiene
  límite superior fijado, así que `pip` instaló la versión más nueva (19.x), cuya
  `av.open()` ya no acepta el parámetro `metadata_errors` que usa `faster_whisper.audio
  .decode_audio` — se fijó `av==13.1.0`, la más reciente que aún lo acepta y tiene wheel
  para Windows/cp313. Descargar el modelo de Hugging Face además fallaba con
  `CERTIFICATE_VERIFY_FAILED` porque esta red usa un proxy con inspección TLS cuyo
  certificado raíz Python no conocía (aunque `curl`/el navegador sí, via el almacén de
  Windows) — `pip-system-certs` resuelve esto haciendo que Python confíe en el mismo
  almacén de certificados que ya usa el sistema, sin desactivar la verificación.
- **Frontend:** `AiAssistant` vive dentro de `AtencionPage` (no una pestaña del paciente:
  el dictado es de una atención concreta), gated por `canUseAi`. Botón de micrófono con
  `MediaRecorder` en fragmentos de 5 s, transcripción editable, "Interpretar dictado" y un
  panel de propuestas agrupadas por destino (Expediente/Odontograma/Diagnóstico/Plan/
  Agenda) con badge "IA" y Aceptar/Editar/Rechazar por tarjeta — "Editar" genera un
  formulario genérico a partir de los campos primitivos del `payload`, sin un formulario
  a medida por cada una de las 11 acciones. Si Ollama no responde (503), se ofrece
  "Insertar como texto en la nota": en vez de una llamada aparte a la API que dejaría
  desincronizado el estado local de `NoteEditor` (su `useState` solo lee `note` al montar),
  `AtencionPage` le pasa el texto como prop (`insertText`) y `NoteEditor` lo agrega a
  `free_text` con su propio `updateField` — reutiliza el mecanismo de autoguardado/dirty ya
  existente de la Fase 4 en vez de bypasearlo. Configuración → Asistente IA (gated por
  `ai.configure`, solo `admin_clinica`) muestra el estado de Ollama/Whisper, el selector de
  modelo instalado y una prueba de micrófono; la opción de guardar audio se muestra
  deshabilitada (se cambia por `.env`, no desde la UI).

### 5.9 Consentimientos e imagenología (Fase 9)
- **`DocumentTemplate` versionada igual que `ToothFinding` (regla 7):** editar una
  plantilla nunca sobrescribe `html_content` -- crea una fila nueva con `version`
  incrementada y `supersedes_id` apuntando a la anterior, marcando `is_current=False` en
  la vieja. `Consent.template_id` guarda el id de la version exacta usada al firmar, no el
  codigo, para que editar la plantilla despues no altere retroactivamente lo que un
  paciente ya firmo.
- **Las plantillas son HTML de verdad, con una sustitucion deliberadamente simple:**
  `render_template` solo reemplaza rutas conocidas (`{{paciente.nombre}}`,
  `{{procedimiento.nombre}}`, `{{plan.titulo}}`, `{{clinica.nombre}}`, `{{fecha}}`,
  `{{profesional.nombre}}`) con un regex, sin condicionales ni expresiones -- a proposito,
  para que una plantilla editable por la clinica (permiso `documents.write`) no pueda
  ejecutar nada mas que texto. Cada valor se escapa con `html.escape` antes de insertarse.
- **xhtml2pdf en vez de reportlab/platypus armado a mano (a diferencia del presupuesto de
  la Fase 7):** la plantilla ya es HTML real, asi que se necesita un renderizador de HTML
  a PDF en vez de construir el documento con Table/Paragraph. Trajo consigo una version
  mas nueva de `reportlab` de la que fijaba la Fase 7 (las pruebas de `treatment/pdf.py`
  siguen pasando igual).
- **Firmar un consentimiento es un solo acto atomico (regla 7):** no hay un estado
  "borrador" -- `POST /patients/{id}/consents` recibe la firma ya capturada (PNG en
  base64 desde el `<canvas>`), renderiza la plantilla con las variables reales, genera el
  PDF con xhtml2pdf, calcula su SHA-256 y guarda ambos (PNG y PDF) via `StorageBackend`.
  Despues de creado, un `Consent` no se edita: corregir un dato significa anularlo (regla
  2, con motivo) y capturar uno nuevo, nunca sobrescribir el PDF ya firmado.
- **"Ligado a procedimiento o plan" es a lo sumo uno de los dos:** `ConsentCreateRequest`
  valida con un `model_validator` que no vengan `procedure_planned_id` y
  `treatment_plan_id` juntos. El frontend solo expone vincular a un plan completo (no a un
  item individual) para mantener el formulario simple -- el backend ya soporta ambos.
- **`Image` es una fila por archivo, no una entidad "estudio":** "carga multiple" (docs/09)
  es `POST /patients/{id}/images` aceptando varios `UploadFile` con los mismos metadatos
  (tipo de estudio, pieza opcional) en una sola peticion, no un agrupador propio. Solo
  JPG/PNG generan miniatura (Pillow, 320x320, mismo patron que el favicon de marca de la
  Fase 2); un PDF se guarda igual pero sin miniatura -- el frontend muestra un marcador
  generico en su lugar.
- **Lectura auditada, a diferencia del resto de la API:** ningun otro modulo audita un GET
  (solo escrituras). Esta fase si audita la lectura del PDF de un consentimiento
  (`documents.consent_read`) y de una imagen en resolucion completa
  (`imaging.image_viewed`) -- miniaturas no se auditan, para no saturar la bitacora en una
  galeria con muchas imagenes.
- **`StorageBackend` reutilizado tal cual (Fase 0):** las claves ya eran no-adivinables
  (`uuid4().hex`) desde que se creo, asi que no hizo falta ningun cambio para cumplir ese
  requisito de docs/09 -- firmas, PDFs e imagenes solo agregan sus propios `subdir`
  (`documents/{clinic}/{patient}`, `imaging/{clinic}/{patient}[/thumbnails]`).
- **Frontend:** `SignaturePad` dibuja con eventos de puntero (unifica mouse y touch) sobre
  un `<canvas>`, sin libreria externa, y exporta un PNG en base64 al soltar el trazo. El
  color del trazo se resuelve en tiempo de ejecucion con
  `getComputedStyle(...).getPropertyValue('--color-text')` porque un `<canvas>` no entiende
  `var(--color-...)` directamente (CLAUDE.md sec. 6 se sigue cumpliendo: el valor viene del
  tema, no esta fijo en el codigo). El visor de imagenes usa `transform: scale()` para el
  zoom y `filter: brightness()/contrast()` para brillo/contraste -- ambos puramente en el
  frontend, sin reprocesar el archivo en el servidor. Dos pestañas nuevas en el paciente,
  "Consentimientos" e "Imágenes", junto a Tratamientos.

### 5.10 Cobranza (Fase 10)
- **El saldo y el estado de un cargo se calculan, nunca se guardan (regla 4):**
  `Charge.status` ("SUGERIDO", de la Fase 7) queda como una etiqueta histórica de origen;
  lo que el frontend muestra (`PENDIENTE`/`PARCIAL`/`PAGADO`/`CANCELADO`) sale de sumar
  las `PaymentAllocation` activas aplicadas a ese cargo en el momento de la consulta
  (`rules.charge_computed_status`). Igual que el odontograma reconstruye el estado de una
  pieza a partir de sus eventos en vez de guardar un campo "estado actual" editable, aquí
  la "verdad" del saldo vive en los pagos de verdad, no en una bandera que alguien podría
  olvidar actualizar.
- **Un pago puede no aplicarse a ningún cargo (anticipo):** `PaymentCreateRequest.allocations`
  es opcional; lo que no se asigna a un cargo queda como crédito del paciente
  (`unallocated_amount`), visible en el resumen de cuenta y usable para aplicarlo despues.
  La suma de aplicaciones de un pago no puede superar su monto (validado con un
  `model_validator`), ni la suma de aplicaciones de un cargo puede superar su saldo
  pendiente (validado contra `PaymentAllocation` reales, no contra el monto original).
- **Cancelar, no borrar (regla 2), con una restricción adicional para los cargos:** un
  `Charge` con pagos aplicados no se puede cancelar directamente (`CHARGE_HAS_PAYMENTS`) --
  hay que cancelar esos pagos primero, para que el saldo que un cargo cancelado implica
  ("nada que cobrar") nunca contradiga pagos todavía activos. Cancelar un `Payment` no
  borra sus `PaymentAllocation`: quedan en la base para el historial, pero se excluyen del
  cálculo de saldo porque la consulta solo suma aplicaciones de pagos con `is_active=True`
  -- el cargo recupera su saldo automáticamente, sin tocar sus propias filas.
- **Corte de caja agrupa pagos por sesión, no solo efectivo:** al crear un `Payment`, si hay
  una `CashSession` en estado `ABIERTA` para la sucursal, el pago se liga a ella
  automáticamente (`cash_session_id`), sin importar el método -- el resumen de cierre
  reporta totales por método, pero el "efectivo esperado" (para contar físicamente) solo
  suma el monto inicial más los cobros en efectivo de la sesión.
- **Cobranza opcional por sucursal (`ClinicBillingSettings.billing_enabled`):** pensado
  para instalaciones donde no se cobra de verdad (p.ej. una clínica universitaria de
  práctica). Desactivarla bloquea `POST /patients/{id}/payments` (`403 BILLING_DISABLED`)
  y oculta la pestaña "Cuenta" en el frontend, pero **no** impide que
  `treatment.register_performed` siga generando su `Charge` sugerido: ese cargo es un
  registro clínico de lo que costaría el procedimiento, no un cobro real, así que no hay
  razón clínica para suprimirlo solo porque la sucursal no cobra (ver
  `docs/PENDIENTES_CLINICOS.md`). `GET /billing/settings` solo exige `billing.read` (no
  `billing.configure`) porque cualquiera que vea cargos/pagos también necesita saber si la
  cobranza está activa para decidir si mostrar esa pestaña; solo cambiarla (`PUT`) exige
  `billing.configure`, un permiso nuevo (incremental, mismo patrón que
  `diagnosis.read`/`treatment.read` en la Fase 7) asignado solo a `admin_clinica`.
- **Recibo con reportlab, no xhtml2pdf:** a diferencia del consentimiento (Fase 9, que
  renderiza una plantilla HTML real), un recibo es un documento estructurado fijo -- se
  arma con `reportlab`/`platypus` igual que el presupuesto de la Fase 7, reutilizando el
  logo de la clínica (`branding_service.read_logo`).
- **Frontend:** pestaña "Cuenta" nueva en el paciente (resumen, cargos, pagos, formulario
  de nuevo pago con aplicación opcional a cargos pendientes), oculta si `billing_enabled`
  es falso. Pantalla "Caja" (`/caja`, fuera del paciente: una sesión de caja es de la
  sucursal, no de un paciente) para abrir/cerrar sesión con los totales por método y la
  diferencia contra lo esperado. Configuración → Cobranza (`admin_clinica`) con el
  interruptor de activar/desactivar.

### 5.11 Reportes y tablero (Fase 11)
- `reports` no agrega tablas: cada reporte es una consulta (`service.py`) armada
  sobre modelos de otros módulos ya existentes (`patients`, `agenda`, `treatment`,
  `billing`, `app/ai`). Seis reportes: pacientes nuevos/activos, citas por estado
  y tasa de no-show (excluye `REPROGRAMADA` del denominador — una cita
  reprogramada no es un resultado real, se "convierte" en una nueva), producción
  por profesional (suma de `Charge.amount` de cargos activos, agrupada por
  `ProcedurePerformed.professional_id`), planes de tratamiento aceptados y
  pendientes, cuentas por cobrar y uso del asistente de IA (sugerencias por
  estado y tipo de acción).
- Cada reporte con rango de fechas acepta `date_from`/`date_to` opcionales (por
  defecto, últimos 30 días — catálogo configurable, ver
  docs/PENDIENTES_CLINICOS.md); **cuentas por cobrar es la excepción
  deliberada**: no recibe rango porque es una fotografía del momento (un saldo
  pendiente de hace meses sigue siendo una cuenta por cobrar hoy).
- Exportación CSV auditada (regla de seguridad, CLAUDE.md sec. 5): cada
  `GET /reports/{reporte}/export` registra un `AuditEvent` (`reports.export`,
  `entity_type="report"`) antes de responder, con el rango de fechas usado en
  `details`.
- **Tablero de inicio por rol**: `GET /reports/dashboard` es deliberadamente
  *distinto* de la pantalla "Reportes" completa en cuanto a permisos. La pantalla
  completa exige `reports.read` (solo superadmin/admin_clinica/caja, según
  docs/MATRIZ_PERMISOS.md). El tablero, en cambio, solo exige estar autenticado;
  internamente arma cada sección (pacientes, agenda de hoy, tratamientos,
  cobranza, uso de IA) únicamente si el usuario ya tiene el permiso de lectura de
  ese módulo (`patients.read`, `agenda.read`, `treatment.read`, `billing.read`,
  `ai.use`/`ai.configure`) — así cada rol ve un tablero relevante en su página de
  inicio sin ampliar el alcance de `reports.read`. La sección de cobranza además
  se omite por completo si `ClinicBillingSettings.billing_enabled` está en falso
  (clínica universitaria de práctica sin cobranza activa).
- Sin dependencia nueva: la exportación usa el módulo `csv` de la librería
  estándar de Python (filas ya tipadas con Pydantic, se listan sus campos
  declarados como encabezado) — no hace falta `pandas` ni nada equivalente para
  un CSV plano.
- Frontend: pantalla "Reportes" con selector de rango de fechas compartido,
  pestañas por reporte y botón "Exportar CSV" (descarga directa con un
  `<a download>` temporal sobre un blob, a diferencia del PDF de recibo de la
  Fase 10 que se abre en una pestaña nueva — un CSV es una descarga, no una
  vista). La página de inicio (`HomePage`) se reconstruyó como el tablero por rol
  descrito arriba, con un enlace "Ver reportes completos" visible solo para quien
  tiene `reports.read`.

### 5.12 E2E y endurecimiento (Fase 12)
- **Playwright (`e2e/`):** `full-flow.spec.ts` recorre el flujo clínico completo
  contra un backend y frontend reales (levantados por `webServer` en
  `playwright.config.ts`) — recepción da de alta al paciente y agenda la cita,
  el odontólogo abre la atención, dicta (con `AI_FAKE_MODE=true`, ver abajo),
  acepta las propuestas, registra un hallazgo en el odontograma, un diagnóstico,
  un plan de tratamiento con un procedimiento, lo presenta/acepta/realiza, crea
  una plantilla de consentimiento y la firma, agenda el seguimiento, y caja
  registra el pago — tres roles reales con sus permisos propios (RBAC real, no
  una limitación del test). `accessibility.spec.ts` audita con `@axe-core/playwright`
  (WCAG 2 A/AA) las pantallas más usadas (login, tablero, pacientes, agenda,
  ficha del paciente, reportes) y falla si hay una violación `serious`/`critical`.
  `performance.spec.ts` mide el tiempo de las pantallas habituales (carga del
  login, tablero, navegación entre pacientes/agenda/inicio, pestañas de la ficha
  de un paciente) con 5 muestras por pantalla y exige un p95 ≤ 2 s — corre contra
  `npm run dev` (Vite sin build de producción), así que es una cota pesimista,
  no el presupuesto exacto de producción.
- **`AI_FAKE_MODE`** (`backend/app/ai/ollama_client.py`, `app/core/config.py`):
  con esta bandera (solo para E2E, nunca en desarrollo normal ni en producción —
  ver `backend/.env.example`), el cliente de Ollama devuelve siempre dos
  acciones fijas (`set_chief_complaint`, `add_vital_sign`) sin red ni modelo
  real, para que Playwright ejerza el flujo de "aceptar propuestas de IA" de
  forma determinista.
- **Revisión de seguridad (OWASP Top 10):**
  - `SecurityHeadersMiddleware` (`app/core/security_headers.py`) agrega a toda
    respuesta `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` y
    `Permissions-Policy`, además de `Content-Security-Policy: default-src 'none'`
    fuera de `/docs`/`/redoc`/`/openapi.json`, y `Strict-Transport-Security`
    cuando `ENVIRONMENT=production`.
  - La documentación interactiva (Swagger/Redoc/`openapi.json`, que carga su
    bundle de un CDN y expone el esquema completo de la API) se desactiva por
    completo fuera de desarrollo (`app/core/config.py::docs_urls`).
  - `Settings` rechaza arrancar con `ENVIRONMENT=production` y el `JWT_SECRET`
    de ejemplo (`change-me`) — ya no es posible desplegar en producción firmando
    tokens con un secreto público (este mismo repositorio).
  - CORS ya era estricto desde la Fase 0 (una sola lista blanca de orígenes,
    sin comodín) y el login ya tenía *rate limiting* desde la Fase 1; esta fase
    no les agrega nada nuevo, solo los confirma.
  - `pip-audit`/`npm audit` (dependencias vulnerables): se corrigieron todas las
    CVE encontradas subiendo versiones (`fastapi`, `pyjwt`, `python-multipart`,
    `python-dotenv`, `pillow`, `black`, `pytest`/`pytest-asyncio`), salvo una:
    `xhtml2pdf==0.2.16` tiene un ReDoS conocido (CVE-2024-25885) en el parseo de
    colores CSS, sin versión corregida todavía. Riesgo aceptado y documentado en
    `docs/SEGURIDAD.md`: el HTML que llega a `xhtml2pdf` (plantillas de
    consentimiento) solo lo escribe personal autenticado con `documents.write`,
    no un paciente ni un anónimo. `npm audit` (frontend y `e2e/`) no encontró
    ninguna vulnerabilidad.
  - Secretos: `.env` sigue fuera de git (`.gitignore`), `.env.example` actualizado
    (incluye `AI_FAKE_MODE`), y no se encontraron secretos reales en el código
    (solo `DEMO_PASSWORD` en `app/seed.py`, una contraseña de datos ficticios,
    documentada como tal).
- **Accesibilidad y rendimiento:** ver `performance.spec.ts`/`accessibility.spec.ts`
  arriba. Dos ajustes de contraste WCAG corregidos en esta fase a partir de la
  auditoría automática (`axe-core`): texto en negritas sobre la cita del día en
  `tokens.css`/`CalendarGrid` y un color del preset con contraste insuficiente
  en `branding/presets.py`/`color_utils.py` (ver comentarios "Fase 12" en esos
  archivos).
- **Documentación:** `docs/SEGURIDAD.md` (detalle de la revisión de seguridad),
  `docs/MANUAL_USUARIO.md` (manual por rol, con capturas) y
  `docs/MANUAL_TECNICO.md` (instalación, variables de entorno, checklist de
  despliegue, solución de problemas), además de esta sección y el README.

### 5.13 Correcciones de errores reportados (Fase 12.1)
Siete errores reportados por el odontólogo, cada uno reproducido primero (antes de
corregirlo) y cubierto con una prueba nueva — ver `docs/06_INSTRUCCIONES_CLAUDE_CODE_CORRECCIONES_Y_FASE13.md`
Parte A para el detalle original de cada reporte.

- **A1 — profesionales nuevos no aparecían en la agenda:** causa real: crear un
  usuario (o cambiarle el rol) nunca creaba su `Provider` (entidad agendable,
  distinta de `User` desde la Fase 6). `iam.service.create_clinic_user`/
  `update_clinic_user` ahora llaman a `agenda_service.ensure_provider_for_user`/
  `set_provider_active_for_user` (paleta de color rotativa, se desactiva — nunca se
  borra — al quitar el rol clínico o desactivar al usuario); `list_providers` ahora
  filtra `is_active`. Migración de backfill para los usuarios clínicos que ya
  existían sin `Provider`.
- **A2 — la búsqueda de pacientes no encontraba coincidencias parciales:**
  `search_patients` comparaba el nombre completo contra el texto completo con
  `similarity()` (calibrado para `check_duplicates`, un umbral distinto a propósito
  — nunca se tocó), así que "perez" no encontraba "Juan Carlos Pérez López". Ahora
  compara palabra por palabra (prefijo + `similarity()` por palabra, con un umbral
  propio) — cubre apellidos en cualquier orden, prefijos parciales y un error de
  una letra — más teléfono comparado solo por dígitos. Frontend: mínimo 2
  caracteres antes de buscar.
- **A3/A4 — selector de atención vacío y botones "Agregar" sin reacción:** el
  selector de atención (expediente, planes de tratamiento, consentimientos —
  **copiado y pegado tres veces**, el mismo defecto en cada pantalla) nunca
  preseleccionaba nada ni ofrecía crear una atención si el paciente no tenía
  ninguna, y ninguna mutación mostraba el error del backend si fallaba
  (`ResumenTab`'s "Iniciar atención" ni siquiera atrapaba el error: un
  *unhandled promise rejection* real). Corrección de raíz: módulo compartido
  `frontend/src/modules/encounters/useEncounterPicker.ts` +
  `EncounterPicker.tsx` (preselecciona la atención de hoy, ofrece
  "+ Iniciar atención nueva", muestra el error de carga/creación) reemplaza las
  tres copias; y una red de seguridad global
  (`app/globalMutationErrorHandling.ts`, un `MutationCache` de TanStack Query +
  `ErrorToast.tsx`) muestra el error de **cualquier** mutación de la app que no
  maneje el suyo, para que un "Agregar" nunca vuelva a fallar en silencio.
- **A5 — "Firmar y generar PDF" no funcionaba:** mismo defecto que A3 (el
  formulario de consentimientos tenía su propia copia del selector roto); con A3
  corregido ahí también, el flujo funciona. El backend ya manejaba bien la firma
  en base64 con o sin el prefijo `data:` y ya incrustaba logo/firma como `data:`
  URI — no tenían el bug que se sospechaba.
- **A6 — las plantillas de consentimiento no funcionaban:** no había **ninguna**
  plantilla sembrada — el selector estaba vacío de origen. `app/seed.py` siembra
  un ejemplo por cada código del catálogo real (`general`, `extraccion`,
  `endodoncia`, `anestesia` — el reporte original mencionaba 5 códigos que no
  existen en el catálogo actual; se usó el catálogo real), marcados "Ejemplo —
  validar con la clínica". Migración de backfill para sucursales que ya existían
  sin plantillas. Pendiente (no se hizo, es mejora de UX, no bloqueaba el flujo):
  botones de variables y vista previa en el editor.
- **A7 — logo de la clínica:** el logo (o el nombre, sin logo — son excluyentes
  entre sí, no se muestran juntos) ahora es un enlace a inicio, con alto máximo de
  40 px y ancho automático (antes se forzaba a un cuadro fijo de 28×28, podía
  deformar un logo no cuadrado).
- **E2E del propio Playwright en puertos dedicados (8011/5185):** al verificar las
  correcciones de arriba con el E2E completo, `reuseExistingServer` reutilizaba sin
  querer un backend/frontend de desarrollo ya corriendo en los puertos normales
  (8001/5174 — típico si alguien está probando la app a mano al mismo tiempo); como
  `AI_FAKE_MODE=true` solo se le pasa al proceso que Playwright arranca él mismo, un
  backend reutilizado sin ese env intentaba usar el Ollama real y el paso de
  dictado de `full-flow.spec.ts` fallaba de forma intermitente. `e2e/playwright.config.ts`
  ahora usa puertos propios (con su propio `CORS_ORIGINS` y `VITE_API_URL`) para que
  esto no pueda volver a pasar.
- **Contraste WCAG de 4 presets de marca:** al correr `accessibility.spec.ts` con
  los puertos dedicados, la sucursal de prueba tenía activo el preset "Azul sereno",
  cuyo primario (`#3A7FC1`) no llegaba a 4.5:1 contra blanco/`--color-bg` ni como
  texto blanco sobre el botón primario — la misma clase de bug que ya se había
  corregido en "Menta clínica" (Fase 12), encontrada aquí porque "Los demás presets
  no se tocaron" (comentario real que quedó en el código de esa fase). Los otros 3
  presets sin tocar (`aqua_suave`, `lavanda_suave`, `verde_salvia`) tenían el mismo
  defecto. `backend/app/modules/branding/presets.py` y
  `frontend/src/theme/presets.ts` oscurecen el primario de los 4
  (`color_utils.suggest_contrasting_color()`, misma lógica que Menta clínica);
  migración de backfill para sucursales que ya habían guardado alguno de esos 4
  presets (el color se copia a `clinic_branding.colors` al guardarse, no es una
  referencia viva al catálogo); prueba nueva que valida los 6 presets del catálogo
  contra WCAG AA, no solo los que ya fallaron una vez.

### 5.14 Catálogos administrables por sucursal (Fase 12.2, Parte B — B1)
Seis catálogos que antes vivían fijos en código (`agenda/rules.py`,
`odontogram/finding_catalog.py`, `diagnosis/rules.py`, `records/rules.py`) —
tipos de cita, hallazgos del odontograma, diagnósticos, categorías de
antecedentes y las dos listas de palabras clave de alerta (condiciones y
medicamentos) — ahora viven en una sola tabla genérica `clinic_catalog_items`
(`catalog_type` + `code`/`name`/`is_active`/`sort_order`/`extra` JSONB), con
CRUD por sucursal. Un administrador ya puede crear un tipo de cita nuevo y
usarlo de inmediato al agendar, o desactivar un hallazgo (deja de aparecer en
el menú rápido del odontograma — los registros históricos que ya lo usan lo
siguen mostrando, porque `ToothFinding` guarda el código, no una referencia
viva al catálogo).

- **Por qué una sola tabla y no seis:** los seis catálogos comparten la misma
  forma (código + nombre + activo/inactivo + orden) y solo difieren en qué
  campos extra necesitan (p. ej. `default_minutes`/`color` en tipos de cita,
  `requires_surface` en hallazgos) — esos campos extra viven en `extra` (JSONB)
  en vez de columnas propias. Es una decisión de alcance: una tabla con seis
  routers/servicios idénticos salvo el nombre habría sido más código sin más
  capacidad real.
- **Qué se quedó fuera a propósito:** procedimientos (`treatment.ProcedureCatalog`,
  ya existía desde la Fase 7, se integró a la misma pantalla pero sin tocar su
  tabla) y métodos de pago (demasiado acoplados a lógica de cobranza con
  `Literal` para moverlos en esta fase).
- **Permiso nuevo `catalogs.manage`** (solo `admin_clinica` — el superadmin
  sigue sin acceso a datos clínicos, regla de seguridad 5 de CLAUDE.md, y la
  mayoría de estos catálogos lo son). `GET /catalogs/{tipo}` acepta además
  cualquiera de los permisos de lectura normales del catálogo correspondiente
  (`agenda.read`, `odontogram.read`, `diagnosis.read`, `records.read`) para que
  un odontólogo pueda seguir leyendo el catálogo al usarlo (p. ej. el menú
  rápido de hallazgos) sin necesitar `catalogs.manage`; sin ese permiso, el
  parámetro `include_inactive` se ignora en silencio (nunca ve los inactivos).
- **Migración de backfill:** inserta el permiso, lo otorga a `admin_clinica` y
  siembra los 39 valores por defecto (los mismos que tenían los `Literal`
  fijos) en cada sucursal existente — sin importar código de la aplicación
  (convención del proyecto para migraciones de datos). `app/seed.py` siembra
  lo mismo para la sucursal de demostración, compartiendo la lista de datos
  con `tests/conftest.py` (la fixture `clinic`, usada por casi toda la suite
  de integración, ya incluye estos 39 elementos).
- **Pendiente de la IA (Fase 13/Parte C):** Ollama necesita un `Literal`
  cerrado para forzar la decodificación estructurada (`app/ai/actions.py`), así
  que por ahora mantiene su propia copia fija de hallazgos/diagnósticos/
  categorías — la instrucción original ("el prompt, la gramática rápida y los
  catálogos de validación de la IA deben leer de estas tablas") queda explícita
  como trabajo de Dentia, no de esta fase.
- **Importar/exportar por CSV** (`GET /catalogs/{tipo}/export`, `POST
  /catalogs/{tipo}/import`, solo `catalogs.manage`): el CSV incluye los
  inactivos (código, nombre, activo, orden, `extra` como JSON en una columna)
  para que editar y reimportar no reactive nada sin querer. La importación es
  por `code` — crea o actualiza, nunca borra — y es parcial: una fila inválida
  se reporta en la respuesta (`CatalogImportSummary.errors`) y se salta, sin
  abortar el resto del archivo.
- **Gabinetes (`Resource`) y Sucursal (`Clinic`) ya tienen pestaña propia**
  dentro de esta misma pantalla (ya no quedan fuera, a diferencia de la
  primera versión de B1):
  - *Gabinetes*: `Resource` ganó `PATCH /resources/{id}` (renombrar/desactivar,
    mismo permiso `agenda.write` que ya exigía crearlo) y `GET /resources`
    ahora filtra los inactivos por defecto — antes nunca filtraba nada porque
    nunca existió la desactivación; igual que con los catálogos genéricos,
    solo quien tiene `agenda.write` puede pedir `include_inactive=true`.
  - *Sucursal*: `PATCH /clinics/current` edita nombre/dirección/teléfono —
    siempre la sucursal activa (`X-Clinic-Id`), nunca recibe un id por la URL,
    así que no hay forma de editar una sucursal ajena desde aquí. Gated por
    `catalogs.manage` (`admin_clinica`), **no** por `iam.manage_clinics` (solo
    `superadmin`, crear/administrar sucursales entre organizaciones, CLAUDE.md
    sec. 5) — son decisiones distintas a propósito: esto es la propia clínica
    editando sus datos de contacto, no creación ni administración entre
    organizaciones.
- Frontend: pantalla **Configuración → Catálogos** (`/configuracion/catalogos`,
  solo `admin_clinica`) con una pestaña por catálogo (seis genéricas + una
  pestaña "Procedimientos y precios" que reutiliza la API de la Fase 7, más
  "Gabinetes" y "Sucursal"), tabla con alta, activar/desactivar y exportar/
  importar CSV en línea.

### 5.15 Gabinete y profesional por defecto (Fase 12.2, Parte B — B2/B3)
Antes de esta fase, agendar una cita siempre partía de cero: elegir profesional,
gabinete y tipo de cita desde el principio, cita tras cita, aun para el mismo
paciente con el mismo odontólogo de siempre. Dos columnas nuevas (nunca una
tabla nueva — son metadatos de una fila que ya existía) resuelven esto:

- **`Provider.default_resource_id`** (B2): el gabinete donde normalmente
  atiende ese profesional *en esta sucursal* — recordar que `Provider` ya era
  una fila por sucursal (`uq_provider_clinic_user`), así que un profesional que
  trabaja en dos sucursales puede tener un gabinete por defecto distinto en
  cada una, sin ningún modelo nuevo.
- **`Patient.default_resource_id` / `Patient.primary_provider_id`** (B3): el
  gabinete y el profesional tratante habitual de un paciente.
- Ambas se validan contra la sucursal al guardarse (`agenda_service.get_resource_in_clinic`/
  `get_provider_in_clinic`, ya existían para validar una cita — reutilizadas,
  no duplicadas) y son siempre opcionales: un profesional o un paciente sin
  asignación simplemente no preselecciona nada, como antes de esta fase.
- **Alta de usuario (B2):** el formulario de "Agregar usuario" deja elegir el
  gabinete por defecto del profesional nuevo en la sucursal activa, y además
  **una o más sucursales adicionales** (cada una con su propio gabinete) —
  antes el alta sólo creaba al usuario en la sucursal activa. El administrador
  solo puede elegir ahí sucursales donde **también** tiene `iam.manage_users`
  (mismo chequeo que ya hace `require_permission` para la sucursal activa,
  repetido explícitamente por sucursal elegida — `IAM`/`service.py::create_clinic_user`);
  elegir la misma sucursal dos veces, o una donde no administra usuarios, se
  rechaza (400/403). Cada sucursal adicional recibe su propio `UserClinic` +
  `Provider` (si el rol es `agenda_rules.PROVIDER_ROLES`), igual que la
  sucursal activa.
- **Alta de paciente (B3):** paso 1 del alta ("Datos") deja elegir el
  profesional tratante y el gabinete por defecto, opcionales.
- **Edición controlada (B3):** cambiar el gabinete o el profesional tratante
  de un paciente ya existente exige un motivo (`care_assignment_reason`),
  igual que cambiar su estado (`status_reason`, Fase 3) — se audita en
  `patients.updated` junto con el resto de cambios de esa edición.
- **Agenda:** `NewAppointmentForm.tsx` preselecciona el gabinete del
  profesional ya elegido al abrir el formulario; al elegir un paciente por el
  buscador, preselecciona su profesional y gabinete tratante (si el paciente
  no tiene uno propio, cae al gabinete por defecto del profesional ya
  elegido) — el usuario siempre puede cambiar cualquiera de los dos antes de
  agendar.
- **"Mis pacientes" (B3):** `GET /patients?mine_only=true` filtra por
  `primary_provider_id` igual al `Provider` del usuario que hace la consulta
  en la sucursal activa; un rol sin `Provider` ahí (p. ej. `recepcion`) recibe
  una lista vacía, no un error. Toggle visible en el listado de pacientes
  solo para `odontologo`/`especialista`.
- **Hallazgo colateral corregido en esta misma fase:** `app/modules/catalogs/models.py`
  (B1) nunca se agregó a `backend/alembic/env.py` — `alembic check` lo marcaba
  como una tabla a **eliminar** (autogenerate no la veía registrada en
  `Base.metadata`). No afectaba a `alembic upgrade head` (la migración de B1 ya
  tenía su DDL escrito a mano), pero sí a cualquier migración futura generada
  con `--autogenerate`. Corregido agregando el import que faltaba.

**Verificación en vivo de Parte B (2026-10-09):** B1, B2 y B3 se reprodujeron contra el
sistema corriendo de verdad (no solo pytest): catálogo nuevo de tipo de cita visible de
inmediato al agendar y desaparece del selector al desactivarlo (B1); alta de odontólogo con
gabinete por defecto confirmada en `Provider.default_resource_id` (B2); filtro "Mis
pacientes" filtrando correctamente por `primary_provider_id` (B3). Los tres funcionan sin
corregir nada de Parte B en sí. De paso se encontró y corrigió un bug real de infraestructura
(no específico de B1/B2/B3, pero es lo que explicaba pantallas colgadas en "Cargando..."):

- **`apiRequest` (`frontend/src/api/client.ts`) no deduplicaba `refreshSession()`:** cuando
  el access token expira con varias peticiones en vuelo a la vez (p. ej. el tablero de inicio
  pidiendo pacientes/agenda/cobranza simultáneamente), cada una recibía 401 y llamaba a su
  propio `refreshSession()` — con el refresh token de un solo uso, las llamadas de más
  colisionaban y la petición original se quedaba esperando para siempre (visto en vivo: el
  checkbox "Mis pacientes" se quedó en "Cargando pacientes..." indefinidamente tras un rato
  de inactividad de la pestaña). Distinto del bug de doble-bootstrap de StrictMode que ya
  corrigió `AppProviders` (commit `68ea22a`): ese es solo al montar la app una vez; este pasa
  con cualquier número de peticiones concurrentes, en cualquier momento de la sesión.
  Corregido compartiendo una sola promesa de refresh entre todas las peticiones que lo
  disparen mientras dure (`refreshSessionOnce()`); prueba nueva `frontend/src/api/client.test.ts`.

### 5.16 "Dentia": asistente de voz conversacional — 13.1 "Base de voz" (Fase 13, Parte C)
Diseño completo en `docs/05_ASISTENTE_DENTIA_VOZ_CONVERSACIONAL.md` y decisiones
fijadas en `docs/06_INSTRUCCIONES_CLAUDE_CODE_CORRECCIONES_Y_FASE13.md` sec. C.
Esta es la primera de seis etapas (13.1–13.6); el alcance de **esta** etapa es
deliberadamente angosto, tal como lo fija su propio criterio de aceptación:
decir "Dentia" enciende el orbe y Dentia responde "¿Sí?" con voz. **Todavía no
hay diálogo ni intenciones** — eso es 13.2 en adelante.

- **Backend `app/voice/`:** WebSocket `/api/v1/voice/ws`. El primer
  mensaje debe ser `{"type": "auth", "token", "clinic_id"}` (el navegador no
  puede mandar el header `Authorization` en un WebSocket); se valida con el
  mismo `decode_token` del resto de la API y se exige `voice.use` o
  `voice.clinical` en esa sucursal — Dentia nunca puede hacer nada que el
  usuario no pueda hacer a mano (sec. 9 del diseño). El endpoint usa
  `websocket.app.state.db_sessionmaker` en vez de `Depends(get_db)` (un
  WebSocket no vuelve a correr sus dependencias en cada mensaje — mismo patrón
  que `AccessDeniedAuditMiddleware`).
- **Detección de "Dentia" (etapa 1 del diseño, `app/voice/wake.py`):** filtro
  de energía barato primero (evita transcribir silencio puro en escucha
  pasiva) y, si hay voz, Whisper `tiny` (modelo propio, separado del que usa
  `app/ai/stt.py` para dictados completos) sobre un buffer circular de ~2.5 s;
  se acepta si la frase **empieza** por "Dentia" (normalizado sin acentos ni
  mayúsculas) — nunca una coincidencia difusa amplia, para no despertar con
  "dentista". La etapa 2 (modelo propio entrenado, openWakeWord/
  livekit-wakeword) queda para la 13.6; el interruptor (`VOICE_WAKE_ENGINE`)
  ya existe.
- **`VoiceCommandLog`** (tabla propia, append-only, sin `AuditedMixin`): texto
  de las órdenes dirigidas a Dentia — nunca el audio, nunca la conversación
  con el paciente (sec. 9 del diseño). En 13.1 solo registra el evento
  `wake_detected`; 13.2+ añadirá intención/resultado sin tocar columnas.
- **`VOICE_FAKE_MODE`** (mismo patrón que `AI_FAKE_MODE`, Fase 8/12): el
  mensaje de cliente `{"type": "fake_wake"}` dispara la misma secuencia que
  detectar "Dentia" de verdad, sin VAD ni Whisper — así es como se prueba el
  WebSocket de punta a punta sin audio real (`tests/integration/voice/`).
- **Permisos nuevos `voice.use`/`voice.clinical`** (migración incremental):
  asignados exactamente como la tabla de la sec. C1 del doc 06 —
  odontólogo/especialista con ambos, recepción solo con `voice.use`,
  caja/admin_clinica/superadmin sin ninguno (activable después). `asistente`
  no está en esa tabla; se dejó **sin** el permiso por defecto en vez de
  asumírselo por similitud con otros permisos de odontólogo (ver
  `docs/PENDIENTES_CLINICOS.md` #36).
- **Frontend `modules/voice/`:** `useVoiceSession` (hook de orquestación:
  conecta el WebSocket, arranca la captura de audio en cuanto llega el primer
  mensaje del servidor, maneja mute/`Alt+M`) + `DentiaOrb` (orbe fijo esquina
  inferior derecha, colores por estado vía variables de tema — gris pasivo,
  azul escuchando/despierto, verde hablando, rojo muteado/desconectado).
  `audioCapture.ts`: `getUserMedia` + `AudioWorklet` (procesador cargado desde
  un Blob URL, no un archivo estático aparte) a 16 kHz mono, frames PCM16 de
  ~30 ms. Una sola pestaña tiene el micrófono a la vez, coordinado por
  `BroadcastChannel` con una elección simple (reclamar, esperar 200 ms por un
  líder existente, promoverse si nadie responde); las demás pestañas quedan
  en gris "activo en otra pestaña". `ttsPlayer.ts`: reproduce audio si el
  backend lo manda, o cae a `speechSynthesis` del navegador (voz
  `es-MX` si el navegador ofrece una) — siempre hay respuesta hablada, nunca
  se queda muda.
- **Voz de salida (Piper, instalado):** se evaluaron Piper y Kokoro TTS (ambos
  gratuitos). Decisión del usuario: **Piper**, invocado como subproceso aparte
  — nunca `import piper` en el proceso del backend. Motivo: el repo activo del
  motor (`OHF-Voice/piper1-gpl`, lo que instala `piper-tts` desde oct. 2025) es
  **GPL-3.0** — el repo MIT original (`rhasspy/piper`) quedó archivado sin
  mantenimiento — y este sistema se *distribuye* instalado en cada clínica (no
  se opera como SaaS propio), así que importar esa librería directamente en el
  backend incorporaría esa licencia al programa que la llama. Invocarla como
  proceso aparte (igual que ya se hace con Ollama) evita eso — mismo
  razonamiento que usar `ffmpeg` por subproceso en vez de enlazarlo; no es una
  garantía legal absoluta (ver `docs/PENDIENTES_CLINICOS.md` #37). Kokoro
  (Apache 2.0, sin esa ambigüedad) se descartó por ahora: sin voz mexicana
  dedicada (español "neutro") y con una dependencia mucho más pesada (PyTorch +
  `espeak-ng`) frente a Piper (solo `onnxruntime`, ya instalado por
  `faster-whisper`).
  - **`app/voice/piper_worker.py`** es el único archivo de todo el proyecto que
    hace `import piper` — y aun así sigue siendo un proceso aparte (`tts.py` lo
    arranca con `subprocess_exec`). Se queda vivo entre llamadas: medido real,
    un `python -m piper` nuevo por frase tardaba **~3 s** (sobre todo cargar el
    modelo de 63 MB), muy por encima del presupuesto de latencia de Dentia
    (sec. 5.1 del diseño: < 1.5 s en la ruta rápida); con el proceso caliente,
    cada frase nueva tarda del orden de décimas de segundo. Protocolo propio
    por stdin/stdout: una línea de texto por petición, un frame binario con
    longitud + PCM16 crudo por respuesta (nunca `readline()` para el audio —
    unos pocos segundos de PCM en base64 superan el límite de línea por
    defecto de `asyncio.StreamReader`). El proceso se apaga limpio al cerrar el
    backend (`lifespan` de FastAPI en `main.py`).
  - Modelo descargado con `python -m piper.download_voices es_MX-claude-high
    --download-dir ../voices` (63 MB) — **no se versiona** (`.gitignore`,
    mismo patrón que `storage/`); cada clínica/entorno lo descarga una vez.
  - `tts.synthesize()` sigue devolviendo `None` si `VOICE_TTS_ENGINE` no es
    `"piper"` o el modelo no está descargado — el cliente cae a
    `speechSynthesis`, nunca se queda muda.
- **Lo que queda explícitamente pendiente de esta etapa** (ver
  `docs/PENDIENTES_CLINICOS.md` #37 y comentarios en el código):
  - **`getUserMedia` no se solicita en el mismo clic de "Iniciar sesión"**
    como pide la sec. 7.1 del diseño — se solicita un poco después, cuando
    `useVoiceSession` arranca la captura tras el primer mensaje del servidor.
    Es una desviación de UX menor (el usuario ve el prompt del navegador un
    instante más tarde), no un bloqueo técnico; conectar el permiso al clic
    exacto de login queda para cuando se afine el arranque automático (13.6).
  - **No hay verificación real con micrófono/bocinas** en este entorno de
    desarrollo: la tubería completa (WebSocket, detección, voz de vuelta) está
    cubierta por pruebas automatizadas con `VOICE_FAKE_MODE`, pero el criterio
    de aceptación literal ("decir Dentia enciende el orbe en < 400 ms") solo
    se puede confirmar probando en un navegador con hardware real.
  - El `AudioContext({ sampleRate: 16000 })` de `audioCapture.ts` depende de
    que el navegador honre esa tasa de muestreo (Chrome/Firefox sí; Safari
    puede ignorarlo) — remuestreo manual si se necesita soportar Safari.

### 5.17 "Dentia" — 13.2 "Navegación" (Fase 13, Parte C)
Segunda etapa: Dentia ya entiende órdenes simples (sin LLM, sin diálogo
clínico todavía — eso es 13.3+) y puede navegar la interfaz por el usuario.
Sigue siendo "ruta rápida" declarativa (sec. 5.1 y 8 del diseño); el enrutado
por LLM queda explícitamente para 13.5.

- **Captura de la orden tras despertar (`app/voice/session.py`):** en vez de
  descartar el audio del buffer de detección de "Dentia" al confirmarse la
  palabra clave, se usa como semilla del buffer de la orden — en el habla
  natural, la orden suele venir en la misma respiración que "Dentia" ("Dentia,
  abre el odontograma"). El cierre de la captura es por silencio final
  (`_ORDER_SILENCE_S = 0.8 s`, medido con el mismo filtro de energía barato de
  13.1, no con VAD completo) o por un tope de seguridad
  (`_ORDER_MAX_S = 8.0 s`). La orden completa se transcribe con el modelo
  Whisper principal (`app/ai/stt.py::transcribe_pcm16`, configurable —
  separado del Whisper `tiny` que solo detecta la palabra clave).
- **`app/voice/nlu_fast.py`:** emparejador declarativo (regex/palabras clave,
  sin LLM) de 7 intenciones: `ayuda`, `repetir`, `silencio`, `ir_a`,
  `abrir_expediente`, `leer_alertas`, `citas_hoy`. **Orden de los patrones
  importa:** `ir_a` (vocabulario cerrado de destinos: "agenda", "pacientes",
  "odontograma"...) se revisa *antes* que `abrir_expediente` (patrón abierto
  "abre/busca `<nombre>`") — si no, "abre el odontograma" se clasificaba mal
  como `abrir_expediente` con `query="el odontograma"`, porque ambos aceptan
  "abre" como disparador y la cláusula intermedia de `abrir_expediente` es
  opcional. Encontrado por una prueba de integración fallando, no por
  inspección manual.
- **`app/voice/dialogue.py` (`handle_order`):** despacha por intención, sin
  LLM. `leer_alertas` exige `has_clinical` (permiso `voice.clinical`) —
  recepción con solo `voice.use` recibe una negativa hablada en vez de las
  alertas del paciente. `citas_hoy` usa `agenda_service` para la siguiente
  cita no terminada/cancelada del profesional que corresponde al usuario
  autenticado.
- **`app/voice/context.py` (`ScreenContext`):** el frontend manda
  `{"type": "context", route, patient_id, encounter_id, tab}` cada vez que
  cambia de pantalla; así "lee las alertas" no necesita repetir el nombre del
  paciente si ya se está viendo su expediente. Vive en un store de Zustand
  propio (`modules/voice/screenContext.ts`), separado de `useVoiceStore`
  (estado del orbe) — una pantalla lo declara con el hook
  `useReportScreenContext({ patientId, tab })` (p. ej. `PatientDetailPage`) y
  se limpia sola al desmontar.
- **Navegación por voz (`ui_action`):** el backend contesta una orden como
  "abre el odontograma de Pérez" con `{"type": "ui_action", "action":
  "navigate", "payload": {"path": "/pacientes/<id>", "tab": "odontograma"}}`.
  `useVoiceSession.ts` llama a `useNavigate()` de React Router. La pestaña
  del expediente (`PatientDetailPage`) es estado local (`useState`), no parte
  de la URL — se manda por `location.state` y la pantalla la lee al montar
  (`isTab()` como guarda de tipo sobre `location.state?.tab`).
- **`VoiceCommandLog`:** ahora también registra `event="order"` con el
  transcript, el resultado (`intent` reconocido o `unrecognized`) y la
  latencia — sin tocar columnas, tal como se previó en 13.1.
- **Pendiente explícito:** el rol `asistente` sigue sin `voice.use`/
  `voice.clinical` por defecto (`docs/PENDIENTES_CLINICOS.md` #36, sin
  cambios en esta etapa).

### 5.18 "Dentia" — 13.3 "Captura en consulta" (Fase 13, Parte C)
Tercera etapa: Dentia ya puede iniciar la consulta y capturar hallazgos del
odontograma por voz, con los niveles de confirmación de la sec. 3 del diseño
y la ventana de seguimiento de la sec. 2.1 — sigue siendo ruta rápida
declarativa, sin LLM (13.5 sigue pendiente). Criterio de aceptación del plan
(doc 06, sec. 13.3): "20 hallazgos seguidos dictados en el odontograma sin
tocar el teclado; 'cancela' y 'deshaz' funcionan" — cubierto por
`tests/integration/voice/test_voice_ws.py::test_full_capture_flow_start_consulta_20_findings_cancela_and_deshaz`.

- **Niveles de confirmación (`app/voice/dialogue.py::PendingCapture`,
  `app/voice/session.py`):** una intención de captura ya no ejecuta de
  inmediato — devuelve un `PendingCapture` (nivel 2 o 3) con la frase de
  vista previa y un `execute()` (closure async) que de verdad aplica el
  cambio. `dialogue.py` nunca usa temporizadores; es `session.py` quien
  decide CUÁNDO llamar a `execute()`:
  - **Nivel 2 (`hallazgo`):** dice la vista previa ("Coloco caries en la 18,
    oclusal.") y arranca una cuenta regresiva (`VOICE_CAPTURE_COUNTDOWN_S`,
    3 s por defecto) en una tarea de fondo (`asyncio.create_task`). "Cancela"
    la cancela. Cualquier otra orden que llegue ANTES de que la cuenta
    termine ejecuta la pendiente de inmediato (no espera el resto de los 3 s)
    y procesa la orden nueva a continuación — así se puede dictar rápido, una
    tras otra, sin perder ninguna (`session.py::_handle_pending_reply`).
  - **Nivel 3 (`iniciar_consulta`):** dice la vista previa + "¿Confirmas?" y
    espera "sí"/"no" explícito (sin temporizador); un tercer tipo de
    respuesta reintenta una vez ("¿Sí o no?").
  - `app/voice/nlu_fast.py::match_confirmation()` reconoce las frases de la
    sec. 3 del diseño (sí/correcto/adelante/confirmo/ok ·
    no/cancela/cancélalo/olvídalo/espera/alto) por **coincidencia exacta de
    toda la frase**, no por palabra suelta — para que un "no" dicho de paso
    en otra conversación (con el paciente, por ejemplo) no cancele nada.
- **Ventana de seguimiento (sec. 2.1, `VOICE_FOLLOWUP_S`, 8 s por defecto):**
  tras resolver cualquier orden, la sesión entra a un modo `follow_up` (orbe
  en "escuchando", igual que capturando una orden) en el que la siguiente
  voz ya es el principio de una orden nueva, sin repetir "Dentia". Se
  implementa con el mismo mecanismo que la cuenta regresiva (tarea de fondo
  cancelable), nunca bloqueando el bucle principal del WebSocket.
- **`iniciar_consulta`:** reutiliza al paciente activo de `ScreenContext`;
  si ya hay una atención de hoy la retoma (misma idea que
  `useEncounterPicker.ts` del frontend, pero resuelta del lado del servidor
  porque Dentia no puede esperar a que alguien elija en un menú), si no crea
  una (`encounters_service.create_encounter`). Al confirmarse, lee las
  alertas críticas del paciente y las dice (sec. 3: "antes de acciones
  relevantes"). El `encounter_id` resultante se guarda en
  `VoiceSession.active_encounter_id` — **no** en `ScreenContext` (ese es el
  que manda el navegador; este lo decide Dentia).
- **`hallazgo`:** `app/voice/nlu_fast.py` combina `app/ai/dental_parser.py`
  (ya existía, Fase 8) para la pieza FDI y las superficies, con un mapa de
  palabras de hallazgo propio (`_FINDING_KEYWORDS`) para el código del
  catálogo. Si el catálogo de la sucursal marca ese hallazgo como
  "requiere superficie" y no se dio ninguna, Dentia pide que se repita la
  orden completa con la superficie — **sin conversación de varios turnos**
  (ver pendiente abajo). La ejecución crea una `AiSuggestion` (igual que la
  Fase 8) y la aplica con `app/ai/applier.py::accept_suggestion(...,
  confirmation_mode="voice_implicit")` — se reusa toda la validación,
  servicios de dominio y auditoría existentes, no se duplica lógica (sec.
  6.4 del diseño).
- **`app/ai/applier.py::accept_suggestion`** ahora acepta
  `confirmation_mode` (`"touch"` por defecto, el panel de la Fase 8;
  `"voice_implicit"`/`"voice_explicit"` desde Dentia) y lo guarda en el
  `AuditEvent ai.suggestion_accepted` (sec. 9 del diseño) — también devuelve
  el id de la entidad creada, que Dentia necesita para la pila de deshacer.
- **Deshacer (`deshaz`, sec. 6.5):** cada sesión de voz guarda una pila (máx.
  10) de las últimas capturas aplicadas, en memoria — **no sobrevive una
  reconexión** (es la sesión del WebSocket, no la atención en la BD; ver
  pendiente abajo). `odontogram_service.retire_finding` (nuevo, mismo patrón
  que `retire_planned` de la Fase 7): marca el hallazgo como no vigente y, si
  remplazaba a uno anterior, lo reactiva — nunca borra (regla 2 de
  CLAUDE.md).
- **Pendiente explícito de esta etapa** (ver `docs/PENDIENTES_CLINICOS.md`):
  - **Sin conversación de varios turnos:** si falta un dato obligatorio
    (p.ej. la superficie), Dentia pide que se repita la orden completa en
    vez de recordar lo ya dicho y solo preguntar lo que falta (la "ASKING"
    de la sec. 6.2 del diseño). Igual para una respuesta de nivel 3 no
    reconocida dos veces: no hay todavía una tarjeta con opciones en
    pantalla.
  - **La pila de deshacer no persiste:** vive en la instancia de
    `VoiceSession`; una reconexión (recargar la página, perder la red) la
    vacía. El historial real del odontograma (regla 5) nunca se pierde —
    solo el atajo de voz para deshacer lo último.
  - **Sin "barge-in" de audio real:** "cancela" interrumpe la cuenta
    regresiva (una tarea de fondo), pero no interrumpe el audio de Piper ya
    en reproducción en el navegador (sec. 7 del diseño) — no verificable sin
    micrófono/bocinas reales en este entorno.
  - Solo `iniciar_consulta` y `hallazgo` de las intenciones de la sec. 4.2/4.3
    del diseño; `signos_vitales`, `motivo_consulta`, `nota`, `alergia`,
    `medicamento` y `diagnostico` quedan para una etapa futura (agenda por voz
    ya se cubrió en 13.4, ver sec. 5.19).
  - Resaltado visual (`ui_action: "highlight_tooth"`) se manda pero el
    frontend todavía no lo pinta en el odontograma — sec. 7 del diseño
    ("resaltado en contexto").

### 5.19 "Dentia" — 13.4 "Diagnóstico, plan y agenda" (Fase 13, Parte C)
Cuarta etapa, **completa**: agenda por voz para recepción (C2 del doc 06) —
`agendar_cita`, `confirmar_cita`, `registrar_llegada`, `reprogramar_cita`,
`huecos_libres`, `cancelar_cita`, `no_show`, `lista_espera` y
`alta_rapida_paciente` — disponibles para cualquiera con `voice.use` (no
exigen `voice.clinical`, a diferencia de lo de abajo: es justo lo que
recepción puede hacer por rol), más la mitad clínica (`diagnostico`,
`procedimiento_planeado`, `procedimiento_realizado`), que sí exige
`voice.clinical`, igual que `iniciar_consulta`/`hallazgo` de 13.3.

- **`app/voice/datetime_parse.py` (nuevo):** fecha/hora relativas dichas en
  voz, funciones puras igual que `dental_parser.py` — "hoy"/"mañana"/un día
  de la semana/"en N días" para la fecha, "a las 10"/"a las diez y media"
  para la hora. Deliberadamente no cubre fechas explícitas ("el 21 de
  octubre") ni distingue a.m./p.m. — una ruta rápida cubre lo frecuente, no
  todo (sec. 5 del diseño); la frase libre cae en "no te entendí" y espera a
  la ruta LLM de la 13.5.
- **`app/voice/nlu_fast.py`:** las órdenes de agenda se reconocen por
  **anclas de palabra clave** ("con", "el"/"al", "a las"), no una gramática
  libre — `_segment_by_anchors()` encuentra cada ancla y corta el texto entre
  una y la siguiente, en cualquier orden en que aparezcan ("agenda a María
  López el jueves a las 11 con la doctora Ruiz" funciona igual que "...a las
  11 con la doctora Ruiz el jueves"). Antes de buscar la siguiente ancla se
  "enmascara" (se sustituye por espacios) lo que ya consumió la anterior —
  si no, el "el" de "con **el** doctor Gómez" se confundía también con el
  ancla de fecha ("el"/"al"). "mañana"/"hoy" son anclas de ancho cero (no
  llevan ninguna palabra delante en el habla natural, a diferencia de "el
  jueves").
- **Emparejamiento por nombre (`dialogue.py`):** profesional y tipo de cita
  se buscan por **palabras en común** contra la lista de profesionales
  (corta por sucursal, no necesita búsqueda tolerante como pacientes) y el
  **código** del catálogo de tipos de cita (no el nombre para mostrar: nombres
  como "Consulta / valoracion" o "Restauracion (resina/amalgama)" traen
  puntuación y varias palabras que nadie diría completas en voz; el código es
  un identificador corto y limpio, CLAUDE.md sec. 6).
- **Huecos libres reales (gabinete/profesional predeterminados, B2/B3):**
  `agendar_cita` usa el `default_resource_id` del profesional automáticamente
  si no se menciona un gabinete — no hace falta preguntarlo. **Proponer
  horarios libres** cuando falta la hora (sec. 4.5 del diseño: "El jueves
  tienes libre a las 10:00 y a las 12:30, ¿cuál?") ya está resuelto (ver
  siguiente punto).
- **`agenda_service.find_free_slots` (nuevo, resto de 13.4):** candidatos cada
  15 minutos dentro de cada ventana de horario laboral del día de la semana
  pedido, descartando lo que choque con un bloqueo o una cita activa del
  profesional — las mismas reglas que `create_appointment`, solo que
  explorando en vez de reservar. `_handle_agendar_cita` lo usa cuando falta
  la hora (en vez de solo pedirla) y la nueva intención `huecos_libres`
  ("¿cuándo hay espacio con la doctora Ruiz esta semana?", nivel 0, igual que
  `citas_hoy`) lo usa para responder disponibilidad sin agendar nada. Sin
  continuidad entre turnos (mismo criterio que el resto de la ruta rápida,
  pendiente #38 de `docs/PENDIENTES_CLINICOS.md`): Dentia propone horarios y
  el usuario repite la orden completa con la hora elegida, no hay un "sí, esa"
  que recuerde la propuesta.
- **`cancelar_cita`/`no_show` (nuevo):** `cancelar_cita` reusa la misma
  búsqueda por paciente-u-hora de `confirmar_cita` (`_find_todays_appointment`)
  y exige el motivo en la misma frase ("cancela la cita de las 12, motivo:
  enfermedad") — regla 2 de CLAUDE.md, igual que la anulación de cualquier
  registro clínico. `no_show` no pide motivo por voz (usa "No se presentó"
  por defecto) porque el diseño (C2 del doc 06) no lo pide en su ejemplo;
  ambas son nivel 3 (cambian el estado de una cita, igual que `agendar_cita`).
- **`lista_espera` (nuevo):** admite nombre explícito ("agrega a María López a
  la lista de espera") o el pronombre del ejemplo del doc 06 ("agrégala a la
  lista de espera"), que se resuelve contra `VoiceSession.last_patient_ref`
  — el último paciente que **cualquier** intención de agenda de esta misma
  conexión resolvió (`DialogueResult.patient_ref`, nuevo campo que
  `session.py` recuerda igual que ya hacía con `encounter_id`). Reusa
  `agenda_service.create_waitlist_entry` de la Fase 6 tal cual.
- **`alta_rapida_paciente` (nuevo):** nivel 1, sin confirmación de voz (igual
  que `ir_a`/`abrir_expediente`) — Dentia **nunca crea el paciente
  directamente** (regla 9 de CLAUDE.md): solo manda un `ui_action navigate` a
  `/pacientes/nuevo` con el nombre y teléfono dictados como query params;
  `NewPatientPage.tsx` los lee con `useSearchParams` para prellenar el paso 1,
  y el alta se termina a mano en pantalla con la detección de duplicados
  obligatoria de siempre. El nombre se separa con una heurística fija (última
  palabra = apellido paterno) — ver limitación en
  `docs/PENDIENTES_CLINICOS.md` #45.
- **Nunca "sin querer" se traslapan citas:** `agendar_cita`/`reprogramar_cita`
  llaman a los mismos `create_appointment`/`reschedule_appointment` que ya
  usa la pantalla de Agenda (Fase 6) — el traslape se rechaza exactamente
  igual (`AppError APPOINTMENT_CONFLICT`), Dentia solo lo convierte en una
  frase hablada ("Ese horario ya está ocupado. Dime otra hora.") en vez de
  dejar que la excepción tumbe la sesión de voz.
- **Red de seguridad en `session.py`:** `_execute_pending` ahora atrapa
  cualquier `AppError` que una captura futura olvide manejar dentro de su
  propio `execute()` — nunca debería dispararse si cada intención atrapa lo
  suyo (como hacen todas las de esta etapa), pero evita que un error nuevo
  tumbe la conexión completa de voz.
- **`diagnostico`, `procedimiento_planeado`/`procedimiento_realizado`
  (mitad clínica, nuevo):** a diferencia de `hallazgo`, el diagnóstico es
  texto libre por naturaleza — `nlu_fast` solo reconoce el VERBO que
  introduce la orden ("pon un diagnóstico de...", "diagnóstico:") y la pieza,
  si se menciona; el texto en sí nunca se normaliza a un catálogo cerrado.
  Revisados **antes** que `_match_hallazgo` (orden del `for` en `match()`):
  sin eso, "planea una resina en la 36" se confundiría con un hallazgo
  porque "resina" también es palabra clave de hallazgo (→ "restauracion").
  Los procedimientos sí resuelven contra el catálogo real
  (`treatment_service.list_procedure_catalog`, Fase 7) por **código**
  (`_find_procedure_code`, mismo criterio que `_find_appointment_type`); si
  no reconoce ninguno, lo dice en vez de adivinar. Las tres reusan
  `app/ai/applier.py::_apply_action` tal cual (misma `AiSuggestion` +
  `accept_suggestion` que `hallazgo`) — `add_planned_procedure` ya sabe
  crear el plan/fase borrador si no existe uno
  (`_get_or_create_draft_plan_and_phase`), así que no se duplicó esa lógica
  aquí. Nivel 3 (no 2 como `hallazgo`): son decisiones puntuales, no una
  captura repetitiva fila tras fila, y `procedimiento_realizado` además
  genera un `Charge` "SUGERIDO" (regla 4 de CLAUDE.md: un procedimiento
  realizado no es un pago).
- **Pendiente explícito** (ver `docs/PENDIENTES_CLINICOS.md`):
  - La fecha solo se reconoce en el formato cerrado de
    `datetime_parse.extract_relative_date` (hoy/mañana/día de la semana/"en N
    días") — una fecha explícita ("el 21 de octubre") no se reconoce.
  - La hora dicha no distingue a.m./p.m. — se toma tal como se dice.
  - `cancelar_cita` sin motivo en la misma frase pide repetir la orden
    completa (no recuerda la cita mencionada para el siguiente turno, #43).
  - `lista_espera` por pronombre solo recuerda al último paciente de una
    intención de agenda de la misma conexión, en memoria (#44).
  - `find_free_slots` usa la duración por defecto, no la del tipo de cita
    dictado, al proponer horarios (#40, ya resuelto en lo demás).
  - `diagnostico` no admite superficie (ni por voz ni por la ruta LLM: el
    esquema `AddDiagnosisAction` de la Fase 8 tampoco la tiene) — solo pieza.
    Los procedimientos sí la admiten (vía `dental_parser.extract_surfaces`,
    igual que `hallazgo`).
- **Bug real encontrado al probar esta etapa, resuelto** (no de esta etapa
  misma — ver sec. 5.1): `_handle_citas_hoy` (13.2), `_find_or_create_todays_
  encounter` (13.3), `_find_todays_appointment` y `_find_upcoming_
  appointment_for_patient` (13.4) usaban `date.today()`/`datetime.now(UTC).
  date()` (hora del servidor) junto con columnas `TIMESTAMPTZ` en UTC — en
  una zona horaria detrás de UTC (México, UTC-6), entre que el reloj local
  marca la tarde y la medianoche, Dentia podía no encontrar una cita/
  atención "de hoy" que sí lo era para la clínica. Las cuatro ahora usan
  `_clinic_zoneinfo`/`_local_day_bounds_utc` (nuevo) contra la zona horaria
  configurable de la sucursal (`Clinic.timezone`, sec. 5.1). Ver
  `docs/PENDIENTES_CLINICOS.md` #42.

### 5.20 "Dentia" — 13.5 "Ruta LLM y dictado" (Fase 13, Parte C)
Quinta etapa, **completa**: cuando la ruta rápida (nlu_fast, sin LLM) no
reconoce una orden, Dentia ya no se rinde directo con "no te entendí" —
intenta la ruta LLM antes, con DOS esquemas fijos según el tipo de orden: el
clínico, reutilizando **el mismo intérprete de la Fase 8**
(`app/ai/interpreter.py`: texto → Ollama → `AiSuggestion` validada contra
catálogos reales), y el de agenda (`app/voice/agenda_llm.py`, nuevo — ver
abajo), en vez de construir un esquema de voz aparte para cada uno. También
se implementó `modo_dictado` completo (sec. 4.2 del diseño).

- **Una orden suelta clínica (`dialogue.py::_try_llm_fallback`):** solo si
  hay una atención activa y el usuario tiene `voice.clinical` (recepción y
  cualquier pantalla sin consulta caen directo a la ruta LLM de agenda, ver
  abajo). Si el intérprete
  devuelve **exactamente una** acción reconocida y nada sin reconocer, Dentia
  la convierte en una vista previa hablada (`_describe_action`, genérica por
  tipo de acción — el detalle completo queda en el panel de Propuestas) y
  pide confirmar. **Siempre nivel 3** (sec. 3 del diseño: "baja certeza sube
  de nivel" — una orden de la ruta libre nunca tiene la confianza de un
  patrón reconocido, nunca se aplica con cuenta regresiva implícita). Cero
  acciones, más de una, o algo sin reconocer → `None` → cae en "no te
  entendí" (más de una acción es exactamente lo que `modo_dictado` resuelve).
- **`modo_dictado` (sec. 4.2 del diseño):** "Dentia, dictado" → nuevo modo de
  sesión `dictating` — cada frase se acumula tal cual (sin pasar por
  `nlu_fast.match`, para no perder acentos/puntuación que le sirven al
  intérprete) y se manda un mensaje `transcript` por frase para que la
  pantalla muestre el avance en vivo (sec. 6.1 del diseño). Solo "fin del
  dictado" (y variantes, `nlu_fast.is_dictation_end`) termina el modo: el
  texto completo acumulado va al intérprete de la Fase 8, que puede devolver
  varias `AiSuggestion` de una vez — Dentia dice "Tengo N propuestas, ¿las
  acepto todas?" (nivel 3). "Sí" las acepta todas
  (`confirmation_mode="voice_explicit"`); "no" las deja **PENDING** en el
  panel de Propuestas de la Fase 8 en vez de perderlas (`PendingCapture.
  cancel_say` personalizado).
- **Aviso "Un momento..." (C4 del doc 06):** `session.py::
  _handle_order_with_stall_notice` envuelve CUALQUIER llamada a
  `dialogue.handle_order` con un temporizador de 2 s — si no ha terminado,
  manda "Un momento..." y sigue esperando. Vive en `session.py` (no en
  `dialogue.py`, que no conoce el websocket) y es genérico: no le importa si
  la orden acabó siendo lenta por la ruta LLM o por cualquier otra razón.
- **`AI_FAKE_MODE`/`ollama_client.chat` siguen siendo el punto de mock de
  siempre:** las pruebas de 13.5 reusan el mismo patrón de
  `tests/integration/ai/test_ai.py` (`monkeypatch.setattr(ollama_client,
  "chat", ...)`), no uno nuevo para voz. Importante: cualquier prueba de voz
  con `has_clinical=True` **y** una atención activa que mande una frase que
  la ruta rápida no reconozca ahora sí puede llegar a intentar un Ollama
  real si no se mockea — un caso real apareció en la prueba de 20 hallazgos
  de 13.3 (el "gracias" de relleno) y tuvo que agregarse el mock ahí también.
- **`app/voice/agenda_llm.py` (nuevo, resto de 13.5): ruta LLM de agenda por
  frase libre.** Cuando `nlu_fast` no reconoce una orden de agenda porque no
  calza con sus anclas de palabra clave ("con", "a las"...), se intenta una
  vez con Ollama antes de rendirse — disponible para **cualquiera con
  `voice.use`** (recepción incluida: a diferencia de la ruta LLM clínica, NO
  exige `voice.clinical` ni atención activa, igual que la agenda de la ruta
  rápida, C2 del doc 06). Esquema propio (`AgendaInterpretResult`, unión
  discriminada de 8 acciones: `agendar_cita`, `reprogramar_cita`,
  `confirmar_cita`, `registrar_llegada`, `cancelar_cita`, `no_show`,
  `lista_espera`, `huecos_libres`) — deliberadamente NO le pide al modelo
  que resuelva fecha/hora a un valor final: el esquema le pide devolverlas
  en el MISMO formato de texto que ya entiende `datetime_parse.py` ("manana",
  "el jueves", "10", "10:30"). Así, `dialogue.py::_try_agenda_llm_fallback`
  convierte el resultado en un `dict` de slots **idéntico** al que ya
  producen los regex de `nlu_fast.py`, y lo pasa por los MISMOS manejadores
  (`_handle_agendar_cita`, etc.) que la ruta rápida — cero lógica de agenda
  duplicada, mismo nivel de confirmación y mismo camino de ejecución.
  `cancelar_cita` exige `reason` en el esquema (Pydantic): si Ollama no lo
  manda, la validación falla y se trata igual que "no reconocí nada" (mismo
  criterio que la ruta rápida, pendiente #43). `lista_espera.patient_name` es
  el único campo opcional entre las 8 acciones — para el pronombre del
  ejemplo del doc 06 ("agrégala a la lista de espera"), resuelto contra
  `last_patient` igual que la ruta rápida. Se intenta **después** de la ruta
  LLM clínica (nunca antes, para no desplazar un dictado clínico real) y no
  requiere `model_digest` (no crea `AiSuggestion`: la agenda nunca pasó por
  ahí, ver más arriba).
- **`OLLAMA_INTENT_MODEL`/`OLLAMA_KEEP_ALIVE` (nuevo, sec. 8 del diseño):**
  modelo e idle-timeout dedicados a la ruta LLM de voz — separados de
  `OLLAMA_MODEL` (el de la Fase 8, dictado clínico completo) porque una
  orden de agenda es corta y la intención ya viene acotada, no necesita el
  modelo grande. `keep_alive` ahora es un parámetro opcional de
  `ollama_client.chat`/`ai_interpreter.interpret` (`None` por quien no lo
  pase, como el dictado REST normal de la Fase 8) — tanto `agenda_llm.py`
  como la ruta LLM clínica de voz (`_try_llm_fallback`/`finish_dictation`)
  lo pasan para evitar la espera de recarga del modelo en cada orden
  durante una sesión de voz activa.
- **Pendiente explícito** (ver `docs/PENDIENTES_CLINICOS.md`):
  - El esquema **dinámico por pantalla y rol** que describe la sec. 5/6.3
    del diseño (un registro declarativo de intenciones del que se derivaría
    el esquema permitido) no se construyó — en su lugar hay dos esquemas
    FIJOS (el clínico de la Fase 8 y el nuevo de agenda), ninguno varía por
    pantalla. Cubre bien los dos casos reales de hoy (dictado clínico y
    agenda), pero una intención nueva fuera de esos dos universos seguiría
    sin ruta LLM.

### 5.21 "Dentia" — C3 "Vocabulario odontológico" y resto de 13.6 "Afinación" (Fase 13, Parte C)
C3 (extracción del vocabulario) y la parte de 13.6 que SÍ se puede hacer sin
grabar audio real: corpus de regresión + script de evaluación de la ruta
rápida, y un E2E con `VOICE_FAKE_MODE` de punta a punta por un navegador
real. Las partes de 13.6 que de verdad necesitan audio real (pruebas de
ruido, entrenamiento de un modelo propio de palabra de activación) **no se
hicieron** — ver el pendiente #49 de `docs/PENDIENTES_CLINICOS.md`: ninguna
herramienta de código puede generar esas grabaciones de forma honesta.

- **`app/ai/vocab/build.py` (nuevo, C3):** `python -m app.ai.vocab.build
  --source ../docs/Diccionario_odontológico_2023.pdf` extrae ~1100 términos
  del diccionario (166 páginas) hacia `terminos_dentales.txt`/`.json`
  (término → categoría, cuando el diccionario trae un paréntesis que no es
  una remisión "Ver X"). No es un analizador de diccionarios perfecto
  (deliberado, ver docstring del módulo): el objetivo es vocabulario para
  Whisper/`rapidfuzz`, no una base lexica — un puñado de remisiones o
  nombres de la bibliografía coladas es inofensivo. Dos bugs reales
  corregidos probando esto: (1) la palabra normal "bibliografía" dentro de
  una oración activaba el corte de la sección de bibliografía (se corrigió
  exigiendo el encabezado ESPACIADO letra por letra, "B I B L I O G R A F I
  A", que es como aparece tipografiado ahí); (2) una letra sola en su propio
  renglón (divisor alfabético de sección, p.ej. "B") se fusionaba con la
  entrada siguiente si el separador de sinónimos permitía saltos de línea —
  "BANDAS" se perdía por completo (se corrigió sin permitir `\n` ahí). Si el
  PDF no tiene suficiente texto extraíble (probablemente escaneado), avisa y
  no escribe nada — nunca inventa un vocabulario.
- **`app/ai/vocab/terms.py` (nuevo):** combina DOS fuentes — el diccionario
  externo y las ETIQUETAS (no los códigos) de los catálogos clínicos FIJOS
  del sistema (`FINDING_CATALOG`, `DIAGNOSIS_CATALOG`). Necesario porque el
  diccionario externo no trae todo: "pulpitis reversible" (el ejemplo
  literal del diseño, sec. 3 del doc 05) no es una entrada del PDF, sino una
  etiqueta de `app/modules/diagnosis/rules.py`. Los catálogos
  ADMINISTRABLES por sucursal (B1) y los nombres de pacientes quedan fuera a
  propósito — `stt.transcribe()`/`transcribe_pcm16()` siguen siendo funciones
  puras sobre audio, sin sesión de BD; ese vocabulario por contexto lo arma
  un módulo aparte, ver más abajo.
- **`app/voice/vocab_context.py` (nuevo, resuelve el pendiente #47):**
  `contextual_terms(db, clinic_id=..., context=...)` junta, en cada orden,
  las ETIQUETAS de los 6 tipos de catálogo administrable de la sucursal
  (`catalogs_service.list_items`, B1), los nombres de los pacientes con cita
  **hoy** en esa sucursal (reutiliza `agenda_service.list_appointments` +
  `dialogue._clinic_zoneinfo`/`_local_day_bounds_utc` — misma zona horaria de
  la sucursal que ya corrigió el bug #42, no `date.today()` del servidor) y
  el nombre del paciente de la pantalla actual (`ScreenContext.patient_id`,
  si el cliente lo mandó). `app/ai/stt.py::transcribe()`/`transcribe_pcm16()`
  ahora aceptan `extra_hotwords` opcional (sin romper al único otro llamador,
  `app/ai/router.py` de la Fase 8, que sigue sin pasarlo) y lo suman al
  `hotwords` fijo de siempre. `VoiceSession._finalize_order`
  (`app/voice/session.py`) es el único punto que lo conecta — llama a
  `contextual_terms()` y, como son puras lecturas sin nada que necesite
  seguir vivo en la sesión, hace `db.rollback()` antes de transcribir (mismo
  cuidado que el bug real de fuga de conexión de `authenticate()`, ver más
  arriba: sin este rollback, una orden que no termina en una escritura propia
  — "citas hoy", una orden no reconocida — dejaría la transacción abierta).
  Pruebas: `tests/integration/voice/test_vocab_context.py` (la función
  aislada) y `test_finalize_order_vocab_context.py` (el cableado real en
  `session.py`, incluido el rollback).
- **`app/ai/vocab/correct.py` (nuevo):** corrige la transcripción contra el
  vocabulario combinado con `rapidfuzz` — el ejemplo literal del diseño
  ("pulpitis reversibe" → "pulpitis reversible") ya funciona. Revisa pares
  de palabras consecutivas (frases de dos palabras del vocabulario) ANTES
  que palabras sueltas, pero en bolsas separadas a propósito: un par nunca
  se compara contra un término de una sola palabra. Bug real encontrado
  probando esto: sin esa separación, "endodoncia en" calzaba por pura
  casualidad contra "endodoncia" sola (alta similitud: casi todos los
  caracteres coinciden) y SE TRAGABA la palabra "en" completa. Umbral alto
  (85) y largo mínimo (5) a propósito: conservador, para no "corregir" una
  palabra común del español por un término técnico parecido.
  `app/ai/stt.py::transcribe()`/`transcribe_pcm16()` ya llaman a esto
  despues de transcribir, y pasan el vocabulario combinado completo como
  `hotwords` de faster-whisper (sin el límite de ~224 tokens de
  `initial_prompt`, que sigue siendo el `DENTAL_VOCABULARY` corto de
  siempre).
- **`tests/voice/commands.jsonl` + `app/voice/eval.py` (nuevo, resto de
  13.6):** 168 frases clínicas + 66 de recepción (supera el ≥150/≥60 del
  doc 06) generadas validando cada una contra `nlu_fast.match` de verdad
  (`python -m app.voice.eval` imprime el % por rol/intención); también
  corre dentro de `pytest` (`test_eval_corpus.py`, parametrizado por
  frase) como regresión continua. Da 100% porque el corpus se construyó así
  a propósito — no es una medición independiente de qué tan bien entiende
  Dentia una orden real dicha con palabras propias (pendiente #48).
- **`e2e/tests/voice.spec.ts` (nuevo):** primer E2E de Dentia, contra el
  frontend real en un navegador real (no solo el backend vía WebSocket de
  prueba, que ya cubrían las pruebas de integración de 13.1-13.5).
  `window.__dentiaTestSend` (nuevo, `useVoiceSession.ts`) es el único gancho
  que se agregó al frontend — nunca existe en producción
  (`import.meta.env.MODE !== 'production'`), y manda `fake_wake`/`fake_order`
  al WebSocket real de la sesión, igual que ya hacían las pruebas de
  integración del backend. `playwright.config.ts` arranca el backend de E2E
  con `VOICE_FAKE_MODE=true` (mismo patrón que `AI_FAKE_MODE`) y una
  ventana de seguimiento generosa (8 s, no los 8 s de producción por
  casualidad sino para que Playwright alcance a comprobar el estado antes
  de que la sesión vuelva sola a pasivo). Deliberadamente NO comprueba el
  estado intermedio "awake": el servidor manda awake/speaking/listening en
  una ráfaga casi instantánea (sin audio real que sintetizar) y Playwright
  podría no alcanzar a verlo entre un sondeo del DOM y el siguiente — habría
  sido una prueba inestable sin aportar nada que el resto no confirme ya.
- **Pendiente explícito** (ver `docs/PENDIENTES_CLINICOS.md`):
  - #47: **resuelto** — vocabulario por contexto dinámico (pantalla/catálogos
    de sucursal/pacientes del día), ver `app/voice/vocab_context.py` arriba.
  - #48: el corpus de 13.6 es autovalidado, no una medición independiente.
  - #49: pruebas de ruido real y entrenamiento de un modelo propio de
    palabra de activación — **bloqueado**, necesita grabaciones reales de
    la clínica que no existen todavía.

**Verificación en vivo de Parte C (2026-10-09):** `python -m app.voice.eval` sigue dando
234/234 (100%, ≥90% exigido); `npx playwright test tests/voice.spec.ts` pasa contra el
backend/frontend reales de E2E. En el navegador real (no solo el E2E con `VOICE_FAKE_MODE`):
el orbe aparece tras el login con el título "Dentia escuchando en segundo plano", clic y
`Alt+M` lo silencian/reactivan correctamente (`_orb_.../_passive_.../_muted_...` con el
`title`/`aria-label` esperado en cada estado). Los dos bugs reales de 13.1 encontrados
verificando Parte A/B en vivo (CPU al 400% por el detector de "Dentia" sin cooldown en
`_process_wake_audio`, y la fuga de conexión de BD por no cerrar la transacción tras
`authenticate()`, ambos en `app/voice/session.py`) ya están corregidos — ver el apartado
"Verificación en vivo de Parte B" más arriba. El pendiente #47 (vocabulario por contexto)
se implementó en esta misma sesión — ver `app/voice/vocab_context.py` arriba. #48 y #49
siguen abiertos tal como están documentados arriba; #49 sigue bloqueado por falta de
grabaciones reales de la clínica.

### 5.22 Rediseño del expediente según formatos oficiales — Fase A (infraestructura compartida + Historia Clínica General)
Primer slice de un rediseño mayor (ver `docs/clinica/` para los PDF oficiales de
referencia: historia general, odontológica, pediátrica, endodoncia, ficha de
tratamientos, nota de evolución, receta, referencia/contrarreferencia). Esta
fase cubre solo la infraestructura compartida entre todos esos documentos y la
Historia Clínica General completa; las demás historias/documentos/odontograma
nuevo quedan para slices siguientes (ver tabla de fases en el plan de esta
entrega).

- **`Patient` — campos compartidos nuevos (todos nullable):** `birth_place`,
  `blood_type`, `education_level`, `can_read_write`, `religion`,
  `ethnic_group`, `race`, `occupation`, `marital_status`. Texto libre, no
  catálogo administrable (decisión técnica, ver pendiente #54 en
  `docs/PENDIENTES_CLINICOS.md`) — se autollenan en la Historia Clínica
  General y, a futuro, en los demás documentos que los pidan.
- **`app/modules/document_settings` ("Formatos de documentos"):** tabla
  `clinic_document_settings` (una fila por sucursal, `clinic_id` PK, mismo
  patrón que `ClinicBranding`): `logo_left_path`/`logo_right_path` (subida de
  imagen reutilizando `StorageBackend` y `branding/svg_sanitize.py`, mismos
  límites de tamaño/formato que el logo único de Marca y Temas),
  `institutional_title` (separado de `display_name`/`subtitle` de branding —
  decisión confirmada con el usuario: el encabezado impreso puede llevar una
  razón social distinta del nombre comercial de la app) y `place_label`
  (autocompleta "Lugar y fecha" en todo documento). Permiso nuevo
  `document_settings.manage` (superadmin + admin_clinica, igual que
  `branding.manage`); lectura solo requiere autenticación (la necesitan los
  PDF y cualquier rol que imprima un documento).
- **`app/modules/documents/pdf_header.py` — encabezado compartido de TODO
  PDF:** `get_pdf_header_info(db, storage, clinic_id=...)` resuelve logo
  izquierdo (con fallback al logo único de branding si "Formatos de
  documentos" no tiene uno propio, para no romper los PDF existentes de
  consentimientos/presupuesto), logo derecho, título institucional (cae a
  `branding.display_name` si no hay uno propio) y lugar. `render_header_html`
  arma la tabla HTML de 2 logos + título para los PDF basados en `xhtml2pdf`
  (`documents/pdf.py`, `records/pdf.py`); `treatment/pdf.py` (reportlab) arma
  su propia tabla equivalente con flowables `Image`. `place_and_date_label`
  arma la línea "Lugar y fecha: {lugar} a {fecha}" (o solo la fecha sin
  lugar configurado). `build_consent_pdf` y `build_budget_pdf` migraron su
  firma de `clinic_name`/`logo` sueltos a un único `header: PdfHeaderInfo`.
- **Historia Clínica General — modelos nuevos en `records/models.py`** (no
  tocan `MedicalHistory`/`Allergy`/`Medication`, que se conservan intactos;
  mismo patrón `_AnnullableMixin` + `AuditedMixin`, `clinic_id`/`patient_id`/
  `encounter_id` por regla 6 de CLAUDE.md):
  - `FamilyHistoryEntry`: parentesco (catálogo `family_relationship`),
    estatus (en_vida/fallecido) y `conditions` JSONB (catálogo
    `family_condition`) en vez de ~16 columnas booleanas.
  - `PersonalPathologicalHistory`: campos puntuales del formato (dolor al
    masticar, sensibilidad, sangrado de encías, extracciones,
    complicaciones, etc.) + `diseases` JSONB `{codigo: {present, evolution}}`
    validado contra el catálogo `pathological_condition`.
  - `PersonalNonPathologicalHistory`: alimentación, higiene bucal, deportes,
    derechohabiencia, estado civil, `servicios_basicos`/`adicciones` JSONB.
  - `SystemsReviewEntry`: un JSONB por aparato (hematológico, cardiovascular,
    neurológico, endocrino, respiratorio, genitourinario — catálogo
    `systems_review_finding` filtrado por `extra.system`) +
    `reproductor_masculino`/`reproductor_femenino` JSONB de forma libre (sin
    catálogo, mezclan booleanos/fechas/conteos — ver pendiente #56).
  - `VitalSigns` (extendida, no reemplazada): `height_m`, `weight_kg`,
    `spo2`, `glucose_index`, `glucose_timing`, `patient_attitude`,
    `asa_classification`. El IMC se calcula al vuelo
    (`records/rules.py::body_mass_index`) y nunca se persiste.
  - Ninguna de estas 4 tablas impone una fila única por `encounter_id`
    (decisión técnica, ver pendiente #57): se corrige con anulación +
    recaptura, igual que `MedicalHistory`.
- **Catálogos administrables nuevos** (`app/modules/catalogs`, mismo patrón
  que `history_category`/`odontogram_finding`): `family_relationship`,
  `family_condition`, `pathological_condition`, `systems_review_finding`.
  Sembrados para sucursales existentes en la migración de backfill
  `7f28821611b0` (mismo criterio que `4d7a2e9c15f3`); valores por defecto
  razonables, no validados con la clínica (pendiente #55).
- **Alertas críticas (regla 8) extendidas:**
  `records.service.get_patient_alerts` ahora también recorre
  `PersonalPathologicalHistory` activas: `rules.pathological_history_alert_text`
  concatena los códigos de enfermedad marcados `present` más los campos de
  texto libre del renglón, y se reutiliza `match_alert_keywords` tal cual
  (misma lógica que ya usaban `MedicalHistory`/`Medication`).
- **Endpoints nuevos** bajo `/api/v1/patients/{id}/general-history/...`
  (mismo estilo que el resto de `records/router.py`: GET para listar, POST
  para capturar, `POST .../{item_id}/annul` con motivo obligatorio — regla 2,
  nunca borrado físico): `family`, `pathological`, `non-pathological`,
  `systems-review`. `vital-signs` se extendió con los campos nuevos (no es un
  endpoint nuevo). `GET /patients/{id}/general-history/pdf` genera el PDF
  completo (paciente + las 4 tablas nuevas + alergias/medicamentos/signos
  vitales ya existentes + el odontograma de diagnóstico actual **tal cual
  existe hoy**, sin el rediseño anatómico que trae la Fase B).
- **`app/modules/records/pdf.py`:** `build_general_history_pdf` (xhtml2pdf,
  mismo motor que `documents/pdf.py`), función pura — recibe un
  `GeneralHistoryPdfData` ya resuelto por `records/service.py` (que hace las
  consultas a BD, incluida la resolución de etiquetas de catálogo
  código→nombre para mostrar texto legible en vez de códigos internos).

### 5.23 Rediseño del expediente — Fase C (Historia Clínica Odontológica)
Tercer slice del rediseño (Fase B — odontograma con figura anatómica y
paleta reconciliada — ya estaba implementada; Fase C es solo backend, el
frontend se construye en un slice aparte). Cubre las secciones del PDF
"historia clinica odontologica" que **no** son el dibujo del odontograma
(eso ya existe desde la Fase B) ni el periodontograma completo con sondeo
por sitio (eso quedó para la Fase G, el último slice del rediseño — ver
sección 5.26 y `docs/PENDIENTES_CLINICOS.md`).

- **Paquete nuevo `app/modules/odontological_history/`** (no una extensión
  de `records/`): para cuando se programó esta fase, `records/service.py`
  ya tenía 1020 líneas y `records/router.py` 455; sumarle 8 tablas más con
  su CRUD + anulación lo hubiera dejado en >1900/~900 líneas. Se siguió el
  mismo patrón de paquete completo que `document_settings/`
  (`models.py`/`schemas.py`/`rules.py`/`service.py`/`router.py`/`pdf.py`),
  reutilizando catálogos y utilidades de fases previas (`app.modules.catalogs`,
  `app.modules.odontogram.rules.TOOTH_FDI_PERMANENT` para validar piezas FDI)
  en vez de duplicarlos. Mismo patrón `_AnnullableMixin` + `AuditedMixin`,
  `clinic_id`/`patient_id`/`encounter_id` (regla 6), ninguna tabla impone fila
  única por encuentro (se corrige anulando y recapturando).
- **8 tablas nuevas**, una fila por `encounter_id`:
  - `OdontologicalExam`: cráneo (catálogo `skull_type`) y biotipo facial
    (catálogo `facial_biotype`) + observaciones; ATM (aperturas en mm,
    chasquidos/crepitación por lado, dolor, fatiga muscular, desviación) +
    observaciones; 9 campos de tejidos blandos (ganglios, carrillos, labios,
    lengua, piso de boca, región retromolar, paladar, faringe, encía
    libre/marginal) + observaciones.
  - `PeriodontalAnamnesis`: **cuestionario de entrevista, NO sondeo
    clínico** (el sondeo de 6 sitios/diente e índices de placa/gingival
    calculados por cara son la Fase G — sección 5.26, `app.modules.
    periodontogram`). `answers` JSONB
    `{código_pregunta: "si"|"no"|"no_recuerda"}` validado contra el catálogo
    `periodontal_anamnesis_question` (30 códigos — ver nota de discrepancia
    en `odontological_history/rules.py` y pendiente en
    `docs/PENDIENTES_CLINICOS.md`) + ~12 columnas de texto libre
    complementarias (cepillado, hábitos, última visita, salud bucal
    autopercibida). Los campos que ya existen en Antecedentes No Patológicos
    (Fase A: tabaco/alcohol) y Alergias no se duplican — el backend solo
    expone lo que pide el PDF; el autollenado/referencia cruzada es
    responsabilidad del frontend.
  - `RadiographicAnalysis`: `findings` JSONB
    `{tipo: {organos_dentarios, porcentaje, alteracion}}` con `tipo` fijo
    (no catálogo administrable): `perdida_osea_horizontal`,
    `perdida_osea_vertical`, `alteraciones_forma_longitud_radicular`,
    `ensanchamiento_ligamento_periodontal`, `hallazgos`. `anexos_nota` es
    solo una referencia textual — adjuntar el archivo en sí ya lo resuelve
    `app.modules.imaging`, no se duplica.
  - `OdontogramDiagnosisDetail`: datos complementarios del odontograma de
    diagnóstico que **no** son el dibujo (eso ya existe, Fase B): espacio
    interoclusal disponible, clasificación de Kennedy superior/inferior
    (`I`/`II`/`III` + modificación) y `fixed_prosthesis_analysis` JSONB lista
    `[{tooth_fdi, cr_relation}]` (piezas FDI permanentes validadas).
  - `ParallelometerAnalysis`: `entries` JSONB lista
    `[{organo_dental, caracteristicas, plan_tratamiento}]`.
  - `RemovablePartialDentureDesign`: 6 columnas de texto libre (conector
    mayor/menor, retenedores directos, conectores indirectos, base
    protésica, dientes artificiales).
  - `ToothDiagnosisEntry` / `ToothTreatmentPlanEntry`: misma estructura
    (`diagnoses`/`plans` JSONB `{tooth_fdi: texto}` + `observaciones`),
    claves validadas contra piezas FDI permanentes (11-18/21-28/31-38/41-48)
    reutilizando `app.modules.odontogram.rules.TOOTH_FDI_PERMANENT` — regla 3
    de CLAUDE.md: esto es solo el plan propuesto por pieza, `ProcedurePlanned`/
    `ProcedurePerformed` (`treatment`) siguen siendo las entidades operativas.
- **Catálogos administrables nuevos**: `skull_type` (mesocéfalo/braquicéfalo/
  dolicocéfalo), `facial_biotype` (mesofacial/braquifacial/dolicofacial),
  `periodontal_anamnesis_question` (30 preguntas). Sembrados para sucursales
  existentes en la migración de backfill `b052393edaf4` (mismo criterio que
  `7f28821611b0`); valores por defecto razonables, no validados con la
  clínica (ver `docs/PENDIENTES_CLINICOS.md`).
- **Endpoints nuevos** bajo
  `/api/v1/patients/{id}/odontological-history/...` (mismo estilo que
  `records/router.py` y `general-history`: GET lista, POST crea,
  `POST .../{item_id}/annul` con motivo obligatorio): `exam`,
  `periodontal-anamnesis`, `radiographic-analysis`,
  `odontogram-diagnosis-detail`, `parallelometer-analysis`,
  `removable-partial-denture-design`, `tooth-diagnosis`,
  `tooth-treatment-plan`. Permisos `records.read`/`records.write`
  (reutilizados, no se creó un permiso nuevo). `GET
  .../pdf` genera el PDF completo (paciente + odontograma de diagnóstico
  actual, reutilizado tal cual de la Fase B + las 8 secciones nuevas).
- **`app/modules/odontological_history/pdf.py`:**
  `build_odontological_history_pdf` (xhtml2pdf, mismo motor y mismo
  encabezado compartido — `documents/pdf_header.py` — que `records/pdf.py`),
  función pura sobre un `OdontologicalHistoryPdfData` ya resuelto por
  `service.py`.
- **Migraciones:** `a7382cfd3971` (crea las 8 tablas) →
  `b052393edaf4` (backfill de los 3 catálogos nuevos para sucursales
  existentes), encadenadas tras `9b1f4c7a0e2d` (Fase B). Cadena completa
  verificada reversible (`alembic downgrade` de vuelta a `9b1f4c7a0e2d` y
  `alembic upgrade head` sin errores).

### 5.24 Rediseño del expediente — Fase E (Historia Clínica Pediátrica)
Cuarto slice del rediseño (backend puro, igual que la Fase C — el frontend se
construye en un slice aparte). Cubre las secciones del PDF "historia clinica
pediatrica" que no estaban ya cubiertas por la Fase A (datos generales,
responsable legal, alergias) ni por el odontograma/plan de tratamiento ya
existentes.

- **Corrección sobre el plan original:** la distinción ausente
  congénito/adquirida (triángulo amarillo/verde en la vista pediátrica) NO se
  agregó como códigos nuevos al catálogo GLOBAL `odontogram_finding` (Fase B)
  — eso habría alterado la leyenda de 4 colores ya cerrada que usan Historia
  General, Odontológica y Tratamiento. En su lugar es una anotación propia y
  exclusiva de esta historia: dos valores más (`ausente_congenito`/
  `ausente_adquirida`) del catálogo nuevo `pediatric_tooth_anomaly`, modelados
  junto con las demás anomalías pediátricas (fu/Gem/Sn/Hip/tr/CEx/MV/PMA) en
  `PediatricToothAnnotation`. `odontogram/models.py` no se tocó.
- **Paquete nuevo `app/modules/pediatric_history/`** (mismo patrón de paquete
  completo que `odontological_history/`: `models.py`/`schemas.py`/`rules.py`/
  `service.py`/`router.py`/`pdf.py`), reutilizando catálogos y utilidades de
  fases previas (`app.modules.catalogs`,
  `app.modules.odontogram.rules.TOOTH_FDI_ALL` para validar piezas FDI,
  permanentes y temporales) en vez de duplicarlas.
- **6 tablas nuevas**, una fila por `encounter_id` excepto la última (varias
  filas, una por pieza anotada):
  - `PediatricPerinatalHistory`: problemas del embarazo/periodo perinatal,
    medicamentos durante el embarazo y el primer año de vida (con detalle),
    vacunas completas, fecha de la última visita al dentista (texto libre).
  - `PediatricOralHabits`: 9 preguntas Sí/No (cepillado, sangrado de encías,
    conocimiento del flúor, fluoruro sistémico aplicado, extracción previa,
    accidentes/fracturas, dolor dental reciente, bruxismo nocturno,
    respiración bucal frecuente).
  - `PediatricBehaviorMaturity`: experiencia con el dentista, relación con el
    médico, control de esfínteres, uso de biberón (`edad_dejo_biberon` es
    texto libre a propósito — el PDF original lo pregunta como texto a pesar
    de un error de imprenta que muestra casillas Sí/No ahí), succión de
    labio/dedo, relación con otros niños, `caracter` (catálogo administrable
    `pediatric_character`) y observaciones.
  - `PediatricOcclusion`: planos terminales izq/der (catálogo administrable
    `terminal_plane`), relación molar de Angle izq/der (texto libre — el PDF
    no da opciones cerradas), overjet/overbite en mm (`overbite_mm` acepta
    negativos, mordida abierta), mordida cruzada, diastema, mordida abierta
    anterior/posterior en mm, línea media y clasificación de Angle (I/II/III,
    `Literal` fijos).
  - `PediatricEruptionDentition`: 6 preguntas Sí/No (secuencia normal,
    pérdida prematura, retención prolongada, erupción retardada, falta de
    contacto proximal, malposición dentaria) + otras anormalidades, edad
    dental y estado general de higiene (texto libre). La tabla estática de
    cronología de erupción/caída del PDF (incisivo central 8-12 meses
    erupción / 6-7 años se cae, etc.) NO se captura como datos — es
    contenido de referencia fijo en
    `pediatric_history/rules.py::PRIMARY_TOOTH_ERUPTION_CHRONOLOGY`/
    `PERMANENT_TOOTH_ERUPTION_CHRONOLOGY` para que el frontend lo muestre como
    tabla de consulta junto al formulario.
  - `PediatricToothAnnotation`: `tooth_fdi` validado contra
    `app.modules.odontogram.rules.TOOTH_FDI_ALL` (permanentes Y temporales,
    a diferencia de `ToothDiagnosisEntry` de Fase C) + `anomaly_code`
    (catálogo administrable `pediatric_tooth_anomaly`, 10 valores) +
    `hipoplasia_detail` (texto libre — notación ambigua en el PDF original,
    "1/3 2/3 3/3" o "i/c/ce", ver `docs/PENDIENTES_CLINICOS.md`). **Decisión
    de re-anotación:** anotar de nuevo la misma pieza en el mismo encuentro
    anula automáticamente la anotación activa anterior de esa pieza (solo una
    vigente a la vez, mismo criterio que la regla 5 de CLAUDE.md aplicada
    aquí a esta anotación exclusiva).
- **Plan de tratamiento pediátrico (permanente/temporal): NO hay tabla
  nueva.** Reutiliza `odontological_history.ToothTreatmentPlanEntry` (Fase C)
  tal cual, mismo endpoint `/odontological-history/tooth-treatment-plan` —
  cambio exacto: `odontological_history/rules.py` agrega
  `TOOTH_FDI_ALL_CODES`/`is_valid_tooth_code` (importando
  `TOOTH_FDI_ALL` de `odontogram.rules`, sin duplicarlo) y
  `odontological_history/service.py::_check_tooth_codes` gana un parámetro
  `include_temporary: bool = False` — solo el call site de
  `create_tooth_treatment_plan_entry` lo pasa en `True`; `tooth-diagnosis` y
  `fixed_prosthesis_analysis` (de `OdontogramDiagnosisDetail`) siguen
  validando solo piezas permanentes, sin cambio de comportamiento.
- **Catálogos administrables nuevos**: `pediatric_character` (apático/
  introvertido moderado/inquieto/irritable/hiperactivo/agresivo),
  `terminal_plane` (recto/mesial/distal), `pediatric_tooth_anomaly` (10
  valores, incluye `ausente_congenito`/`ausente_adquirida`). Sembrados para
  sucursales existentes en la migración de backfill `c1a9f3b7d2e4` (mismo
  criterio que `b052393edaf4`); valores por defecto razonables, no validados
  con la clínica (ver `docs/PENDIENTES_CLINICOS.md`).
- **Endpoints nuevos** bajo `/api/v1/patients/{id}/pediatric-history/...`
  (mismo estilo que `odontological-history`: GET lista, POST crea,
  `POST .../{item_id}/annul` con motivo obligatorio): `perinatal-history`,
  `oral-habits`, `behavior-maturity`, `occlusion`, `eruption-dentition`,
  `tooth-annotation`. Permisos `records.read`/`records.write` (reutilizados,
  no se creó un permiso nuevo). `GET .../pdf` genera el PDF de las 6
  secciones (sin el dibujo del odontograma pediátrico ni el plan de
  tratamiento por pieza — se consultan en sus propias vistas, decisión
  documentada en `pediatric_history/service.py`).
- **`app/modules/pediatric_history/pdf.py`:** `build_pediatric_history_pdf`
  (xhtml2pdf, mismo motor y mismo encabezado compartido —
  `documents/pdf_header.py` — que `odontological_history/pdf.py`), función
  pura sobre un `PediatricHistoryPdfData` ya resuelto por `service.py`.
- **Migraciones:** `914ebc0df26e` (crea las 6 tablas) →
  `c1a9f3b7d2e4` (backfill de los 3 catálogos nuevos para sucursales
  existentes), encadenadas tras `b052393edaf4` (Fase C). Cadena completa
  verificada reversible (`alembic downgrade` de vuelta a `b052393edaf4` y
  `alembic upgrade head` sin errores).

### 5.25 Rediseño del expediente — Fase F (Historia Clínica de Endodoncia)
Quinto slice del rediseño (backend puro, igual que las Fases C/E — el
frontend se construye en un slice aparte). Cubre las secciones del PDF
"historia clinica endodoncia" que no estaban ya cubiertas por la Fase A
(datos generales, alergias, motivo de consulta).

- **Paquete nuevo `app/modules/endodontic_history/`** (mismo patrón de
  paquete completo que `odontological_history/`/`pediatric_history/`:
  `models.py`/`schemas.py`/`rules.py`/`service.py`/`router.py`/`pdf.py`).
- **Ningún catálogo administrable nuevo.** A diferencia de las Fases C/E,
  todos los checklists de esta fase (antecedentes, dolor, estímulo, examen
  intra/extrabucal, percusión horizontal/vertical, cámara/conducto/
  periodonto, tratamiento, cirugía) son checklists cerrados y pequeños —
  mismo criterio que `odontological_history.rules.RADIOGRAPHIC_FINDING_TYPES`
  — y se validan como tuplas fijas directamente en
  `endodontic_history/service.py::_check_fixed_keys` (nunca contra
  `app.modules.catalogs`).
- **7 tablas nuevas**, una fila por `encounter_id` excepto
  `EndodonticPulpSensitivityTest` (varias pruebas por encuentro, el PDF
  muestra 2 bloques idénticos pero no hay límite clínico de exactamente 2) y
  `EndodonticToothDiagnosisCode` (varias filas, una por pieza+`kind`
  anotada):
  - `EndodonticInterrogation`: antecedentes/dolor/estímulo/examen
    intrabucal/examen extrabucal, cada uno `dict[str, bool]` de claves fijas
    + detalle de texto libre para la opción "otro".
  - `EndodonticPulpSensitivityTest`: 8 columnas booleanas (frío, calor,
    fugaz, persistente, localizado, irradiado, decrece, incrementa) +
    diente testigo O.D., prueba de cavidad y prueba eléctrica O.D. (texto
    libre).
  - `EndodonticPeriodontalTest`: percusión horizontal y vertical son 2
    columnas del mismo formulario (mismas 4 claves cada una, NO entradas
    repetibles), movilidad horizontal/vertical (`positiva`/`negativa`) con
    grado (`I`/`II`/`III`, el servicio rechaza un grado si la movilidad
    correspondiente no es `positiva`) y palpación.
  - `EndodonticRadiographicInterpretation`: cámara/conducto/periodonto,
    cada uno `dict[str, bool]` de claves fijas + detalle libre para "otro".
  - `EndodonticDiagnosisTreatment`: `diagnostico_pulpar`/
    `diagnostico_periapical` son selección ÚNICA (`Literal` fijo, 6 valores
    cada uno — clínicamente es un diagnóstico, no multi-select); tratamiento
    y cirugía son checklists multi-select.
  - `EndodonticToothDiagnosisCode`: odontograma de endodoncia — **18 códigos
    numéricos (0-17) propios de esta historia, catálogo independiente del
    catálogo general del odontograma (Fase B) — `odontogram/models.py` NO se
    tocó.** El PDF repite el mismo dibujo dos veces (diagnóstico inicial /
    evolución del tratamiento): se modeló como UNA tabla con el
    discriminador `kind` (`diagnostico`/`evolucion`) en vez de duplicarla,
    mismo criterio de simplicidad que el resto del proyecto. Solo piezas FDI
    permanentes (`odontogram.rules.TOOTH_FDI_PERMANENT`, reutilizada sin
    duplicar). **Decisión de re-anotación** (mismo patrón que
    `PediatricToothAnnotation` de la Fase E): anotar de nuevo la misma pieza
    con el mismo `kind` en el mismo encuentro anula automáticamente la
    anotación activa anterior de esa pieza+`kind` (solo una vigente por
    pieza+`kind`); una pieza puede tener `diagnostico` Y `evolucion` activas
    simultáneamente (son independientes), pero no dos `diagnostico` activas
    a la vez.
  - `EndodonticWorkingLength`: longitud de trabajo de una pieza por visita.
    `canal_measurements` es un JSONB `{clave_conducto: {aparente_rx,
    real_localizador, relacion}}` validado contra 10 claves fijas (mesial,
    mesiolingual, mesiovestibular, mesiopalatino, distal, distolingual,
    distopalatino, distovestibular, palatino, único) + técnica de
    instrumentación/obturación, indicaciones y fechas de inicio/término
    (texto libre, mismo criterio que `fecha_ultima_visita_dentista` de la
    Fase E).
- **Endpoints nuevos** bajo `/api/v1/patients/{id}/endodontic-history/...`
  (mismo estilo que `odontological-history`/`pediatric-history`: GET lista,
  POST crea, `POST .../{item_id}/annul` con motivo obligatorio):
  `interrogation`, `pulp-sensitivity-test`, `periodontal-test`,
  `radiographic-interpretation`, `diagnosis-treatment`,
  `tooth-diagnosis-code` (con filtro opcional `?kind=diagnostico|evolucion`,
  mismo patrón de query param que `imaging`), `working-length`. Permisos
  `records.read`/`records.write` (reutilizados). `GET .../pdf` genera el PDF
  de las 7 secciones (el odontograma de 18 códigos se lista como texto
  "Pieza NN (kind): código - nombre", igual criterio que el odontograma
  pediátrico de la Fase E — el dibujo visual se consulta en su propia
  vista).
- **`app/modules/endodontic_history/pdf.py`:** `build_endodontic_history_pdf`
  (xhtml2pdf, mismo motor y mismo encabezado compartido —
  `documents/pdf_header.py` — que `odontological_history/pdf.py` y
  `pediatric_history/pdf.py`), función pura sobre un
  `EndodonticHistoryPdfData` ya resuelto por `service.py`.
- **Migración:** `32fce2f53516` (crea las 7 tablas), encadenada tras
  `c1a9f3b7d2e4` (Fase E). Sin backfill de catálogos (no se creó ninguno
  nuevo). Cadena completa verificada reversible (`alembic downgrade -1` de
  vuelta a `c1a9f3b7d2e4` y `alembic upgrade head` sin errores).

### 5.26 Rediseño del expediente — Fase G (Periodontograma completo)
**Último slice del proyecto de rediseño del expediente** (backend puro,
igual que las Fases C/E/F — el frontend, el más complejo del proyecto por
ser un periodontograma interactivo de 32 piezas × 6 sitios, se construye en
un slice aparte). Cierra formalmente el pendiente dejado abierto desde la
Fase C (`docs/PENDIENTES_CLINICOS.md` #59): `odontological_history.
PeriodontalAnamnesis` (Fase C) es solo un **cuestionario de entrevista**,
nunca sondeo clínico — este paquete es el sondeo clínico que faltaba.

- **Fuente de verdad ambigua, resuelta con el estándar clínico universal.**
  La página "PERIODONTOGRAMA" y las de "ÍNDICE DE PLACA DENTOBACTERIANA"/
  "ÍNDICE GINGIVAL" del PDF oficial son una cuadrícula dibujada a mano (no
  texto estructurado): las etiquetas de fila exactas (E.Q/E.I/N.I/P.B.,
  repetidas de forma algo ambigua en el escaneo) no se pudieron transcribir
  pixel-perfecto. Ante esa ambigüedad, el modelo de datos sigue el
  **estándar clínico periodontal universal** (6 sitios de sondeo por pieza,
  movilidad de Miller 0-3, grado de furca 0-3, índice de placa de O'Leary e
  índice gingival de Löe-Silness) en vez de intentar adivinar la cuadrícula
  original — documentado para validar con la clínica real en
  `docs/PENDIENTES_CLINICOS.md`.
- **Paquete nuevo `app/modules/periodontogram/`** (mismo patrón de paquete
  completo que `odontological_history/`/`pediatric_history/`/
  `endodontic_history/`: `models.py`/`schemas.py`/`rules.py`/`service.py`/
  `router.py`/`pdf.py`). **Ningún catálogo administrable nuevo**: todos los
  valores son escalas clínicas estándar fijas y pequeñas (enteros/enums),
  no listas que una clínica concreta vaya a querer personalizar — se
  definieron como constantes en `rules.py` (mismo criterio que
  `endodontic_history.rules` para sus checklists cerrados).
- **5 tablas nuevas**, todas con varias filas por `encounter_id` excepto la
  última:
  - `PeriodontalProbingSite`: el periodontograma propiamente dicho — una
    fila por pieza × uno de los 6 sitios estándar (mesiovestibular/
    vestibular/distovestibular/mesiolingual/lingual/distolingual; "lingual"
    aplica igual para la arcada superior, donde clínicamente es "palatino"
    — es solo una etiqueta de interfaz, `rules.PROBING_SITE_LABELS`, el
    código no distingue arcada). `probing_depth_mm` (0-15) y `recession_mm`
    (-5 a 15, puede ser negativa: agrandamiento/cobertura gingival sobre la
    unión cemento-esmalte) + `bleeding_on_probing`/`suppuration`. Solo
    piezas FDI **permanentes** (`odontogram.rules.TOOTH_FDI_PERMANENT`, el
    dibujo del PDF no muestra temporales). El **nivel de inserción clínica
    (CAL) no se persiste**: se calcula al vuelo como
    `probing_depth_mm + recession_mm` (mismo criterio que el IMC de la Fase
    A, dato derivado nunca desincronizado), expuesto en
    `PeriodontalProbingSiteOut.clinical_attachment_level_mm` (calculado en
    `router.py`, igual patrón que `records/router.py` con el IMC). **Decisión
    de re-anotación** (mismo patrón que `PediatricToothAnnotation`/
    `EndodonticToothDiagnosisCode`): volver a capturar la MISMA pieza+sitio
    en el MISMO encuentro anula automáticamente la anotación activa
    anterior de esa pieza+sitio.
  - `PeriodontalToothMeasurement`: movilidad dentaria (clasificación de
    Miller, 0-3) y grado de afectación de furca (0-3, relevante en molares
    pero el código no restringe la pieza) — una fila por pieza, mismo
    criterio de re-anotación que la tabla anterior.
  - `PeriodontalIndexEntry`: índices de placa dentobacteriana y gingival —
    **una sola tabla con discriminador `index_type`** (`"placa"`|
    `"gingival"`, igual patrón que `kind` en `EndodonticToothDiagnosisCode`
    de la Fase F, en vez de duplicar la tabla). Solo 2 superficies por pieza
    (`"vestibular"`/`"lingual"` — NO 6 sitios: el PDF muestra una cuadrícula
    mucho más simple para los índices que para el sondeo). `grade` 0-3, cuyo
    significado depende de `index_type` (textos documentados en
    `rules.PLAQUE_GRADE_LABELS`/`GINGIVAL_GRADE_LABELS` para que el
    frontend/PDF los muestre). Mismo criterio de re-anotación por
    pieza+`index_type`+`surface`. Los totales (índice de O'Leary, índice de
    Löe-Silness) **no se persisten**: se calculan al vuelo en
    `rules.compute_plaque_index`/`compute_gingival_index`.
  - `OcclusalContactEntry`: tablas de oclusión — contactos marcados en 4
    movimientos (`centrica`/`lateralidad_izquierda`/`protrusion`/
    `lateralidad_derecha`). Solo se crea una fila cuando el contacto está
    marcado (la ausencia de fila para una pieza+movimiento significa "sin
    contacto"); sin `grade` ni campo adicional, la existencia de la fila
    activa ES la marca. **Decisión**: volver a marcar la MISMA
    pieza+movimiento en el mismo encuentro es **idempotente** (devuelve la
    fila activa existente en vez de duplicarla, al no haber un "grado" que
    reemplazar); "desmarcar" usa el endpoint de anulación.
  - `PeriodontogramObservation`: observaciones de texto libre, una fila por
    encuentro (sin restricción única, mismo criterio que el resto del
    expediente).
- **Endpoints nuevos** bajo
  `/api/v1/patients/{id}/periodontogram/...` (mismo estilo GET lista/POST
  crea/`POST .../{item_id}/annul` que el resto del expediente):
  `probing-sites`, `tooth-measurements`, `index-entries` (con filtro
  opcional `?index_type=placa|gingival`, mismo patrón de query param que
  `endodontic-history/tooth-diagnosis-code?kind=`), `occlusal-contacts`,
  `observations`. Permisos `records.read`/`records.write` (reutilizados, no
  se creó ningún permiso nuevo).
  - **`GET .../indices-summary`** (query param opcional `encounter_id`):
    devuelve los índices calculados al vuelo — si no se especifica
    `encounter_id`, usa el **encuentro más reciente con al menos una
    entrada activa de `PeriodontalIndexEntry`** (decisión de diseño:
    documentada en `service.py::get_indices_summary` y
    `docs/PENDIENTES_CLINICOS.md` — es más útil que forzar siempre al
    llamador a indicar un encuentro). Responde
    `{encounter_id, placa: {numero_caras_totales, numero_caras_pigmentadas,
    indice_placa_dentobacteriana}, gingival: {numero_sitios_totales,
    indice_gingival_total}}`; ambos índices son `null` (no `0.0`) cuando no
    hay datos registrados, para no sugerir falsamente "sin placa"/"encía
    sana".
  - **`GET .../pdf`** genera el PDF completo.
- **`app/modules/periodontogram/pdf.py`:** `build_periodontogram_pdf`
  (xhtml2pdf, mismo motor y mismo encabezado compartido —
  `documents/pdf_header.py` — que el resto del expediente), función pura
  sobre un `PeriodontogramPdfData` ya resuelto por `service.py`. **Decisión
  documentada:** la cuadrícula de sondeo por pieza/sitio se representa como
  una **tabla de datos clara**, sin replicar el dibujo gráfico del
  odontograma de 32 piezas dentro de este PDF basado en texto/xhtml2pdf —
  mismo criterio que el odontograma de endodoncia de la Fase F (listado
  como texto); el dibujo interactivo vive en el frontend.
- **Migración:** `1138d7738a75` (crea las 5 tablas), encadenada tras
  `1ce0f3ad4a1a` (último head antes de esta fase — varias migraciones sin
  relación con el rediseño del expediente se agregaron entre la Fase F y
  esta). Sin backfill de catálogos (no se creó ninguno nuevo). Autogenerate
  también detectó "eliminar" el índice `ix_patients_full_name_trgm` —falso
  positivo ya documentado en migraciones anteriores (la expresión GIN con
  `immutable_unaccent` no se refleja en los metadatos de SQLAlchemy) — se
  quitó a mano del archivo de migración, no se aplicó. Cadena completa
  verificada reversible (`alembic downgrade` de vuelta a `1ce0f3ad4a1a` y
  `alembic upgrade head` sin errores).

## 6. Frontend
- **Layout:** barra lateral (logo de la clínica), búsqueda global de pacientes y **encabezado de paciente persistente** con barra de alertas.
- **Pestañas del paciente:** Resumen | Expediente | Odontograma | Tratamientos | Consentimientos | Imágenes | Cuenta.
  La Agenda (Fase 6) no es una pestaña del paciente: es una pantalla propia en el menú lateral
  (`/agenda`), porque una cita es de la clínica/profesional, no de un paciente concreto — se llega
  a un paciente *desde* la cita, no al revés.
- **Odontograma:** componente SVG propio con `<Arch>`, `<Quadrant>`, `<Tooth>` y `<Surface>` (5 zonas clicables), leyenda configurable y un control deslizante de historial por fecha.
- **Asistente de voz (Fase 8):** botón de micrófono y panel de "Propuestas del asistente"
  dentro de la pantalla de Atención (`Alt+M`), no flotante en toda la app: el dictado
  pertenece a una atención concreta, igual que la nota SOAP que lo acompaña.
- Atajos de teclado: `Alt+N` nueva atención, `Alt+O` odontograma, `Alt+M` micrófono, `Esc` cancelar dictado.
- **Página de inicio (Fase 11):** tablero por rol (ver sección 5.11) en vez del
  mensaje fijo de versiones anteriores; pantalla "Reportes" propia (`/reportes`)
  en el menú lateral, visible solo con permiso `reports.read`.
- **Control de versiones (Fase 17):** pantalla `/configuracion/version`
  (`version_info/VersionInfoPage.tsx`), visible solo con permiso
  `version_info.read` (superadmin/admin_clinica), que muestra la versión de
  DentalCare corriendo en el servidor y enlaza al historial de releases en
  GitHub.

## 7. Respaldo
- `scripts/backup.ps1`/`.sh`: `pg_dump --format=custom` del rol de aplicación
  (`dentia`, sin privilegios de administrador) + copia comprimida de `storage/`,
  ambos cifrados con OpenSSL (AES-256-CBC + PBKDF2) si hay una frase de paso en
  `BACKUP_PASSPHRASE` — si no la hay, el respaldo se completa sin cifrar con una
  advertencia visible en el log, para no romper una corrida desatendida. Retención
  configurable (30 días por defecto) que borra los respaldos más viejos al final
  de cada corrida.
- `scripts/restore_test.ps1`/`.sh`: restaura el respaldo más reciente en una base
  de datos desechable (requiere credenciales de un superusuario de PostgreSQL,
  solo por variable de entorno, nunca en un archivo — el rol `dentia` no tiene
  `CREATEDB` a propósito), verifica con una consulta sobre tablas clave y el
  `.zip` de `storage/`, limpia todo y registra `PASS`/`FAIL`. Ver
  `docs/OPERACION.md` para la programación en Windows (Programador de tareas) y
  Linux (cron), y el detalle de la verificación manual hecha en esta fase.

## 8. Estado de implementación
| Fase | Alcance | Estado |
|---|---|---|
| 0 | Base del proyecto: estructura de carpetas, FastAPI con `/api/v1/health`, Alembic (async) configurado sin migraciones aún, frontend Vite + React 18 + TS con layout base (barra lateral, encabezado, contenido), `docker-compose.yml` (PostgreSQL 16), `.vscode/`, lint/format/test configurados en ambos lados | Hecho |
| 1 | IAM (`organizations`, `clinics`, `users`, `roles`, `permissions`, `user_clinics`, `refresh_tokens`) y `audit` (`audit_events` append-only). Login JWT + MFA TOTP + rate limiting, `require_permission` por `X-Clinic-Id`, catálogo de permisos seedeado por migración (`docs/MATRIZ_PERMISOS.md`), `app/seed.py` con admin y odontólogo ficticios. Frontend: login, selección de sucursal, gestión de usuarios, guardia de rutas por permiso | Hecho |
| 2 | `clinic_branding` (nombre, logo, favicon, preset o colores personalizados, modo oscuro, radio de bordes). `GET /branding` público, `PUT /branding` y `POST /branding/logo` con permiso `branding.manage`. 6 presets + derivación de hover/soft + validación de contraste WCAG (avisa y sugiere, no bloquea). SVG saneado (sin `<script>`/eventos), favicon generado con Pillow. Frontend: `ThemeProvider`, pantalla Configuración → Apariencia (preset, colores, logo, vista previa en vivo, restablecer) y script que verifica que no haya colores fijos fuera de `theme/` | Hecho |
| 3 | `patients` (alta, edición controlada con motivo, 5 estados, contactos tutor/emergencia, foto permisionada) y expediente autonumérico por sucursal. Búsqueda tolerante (`pg_trgm` + `unaccent`) y detección de duplicados (nombre + nacimiento o teléfono) con confirmación obligatoria. Lectura de ficha auditada. Frontend: búsqueda global (`Ctrl+K`), listado con filtro de estado, alta en 3 pasos (datos → posibles duplicados → contactos), encabezado persistente del paciente (nombre, edad, foto, barra de alertas vacía) y controles de edición ocultos para roles sin `patients.write`. Seed con 50 pacientes ficticios (Faker es_MX) | Hecho |
| 4 | `records` (antecedentes, alergias, medicamentos, signos vitales; anulación con motivo, no borrado) y `encounters` (atención + nota clínica SOAP versionada: DRAFT→FINAL→CORRECTED\|CANCELLED). Alertas críticas derivadas (no almacenadas) a partir de alergias/medicamentos/antecedentes, exigidas antes de finalizar una nota (regla 8). Dos bugs de raíz corregidos: constraint de paciente ausente del modelo (autogenerate destructivo) y `MissingGreenlet` en columnas `onupdate` (fix global con `eager_defaults`). Frontend: pestañas Resumen (línea de tiempo clínica, "Iniciar atención") y Expediente (secciones colapsables) del paciente, pantalla de Atención con SOAP, autoguardado cada 10 s, modal de alertas antes de finalizar, corregir/cancelar con motivo. Seed con 3 encounters de ejemplo (nota finalizada, nota en borrador, nota corregida) | Hecho |
| 5 | `odontogram` (`ToothFinding` como eventos con `supersedes_id`/`is_current`, índice único parcial por pieza/superficie/tipo; catálogos de piezas FDI, superficies y hallazgos en `rules.py`/`finding_catalog.py`). Reconstrucción histórica vía `GET .../odontogram?at=`. Frontend: pestaña Odontograma con SVG propio (arcadas superior/inferior, vistas permanente/temporal/mixta, 5 superficies clicables, menú rápido de hallazgos, leyenda, deslizador de fecha de solo lectura, panel de historial por pieza) | Hecho |
| 6 | `agenda` (`Provider`, `Resource`, horario laboral y bloqueos informativos, `Appointment` con máquina de estados RESERVADA→CONFIRMADA→EN_SALA→EN_ATENCION→TERMINADA \| CANCELADA/NO_SHOW/REPROGRAMADA, `AppointmentStatusHistory`, `ReminderTask` idempotente, lista de espera). Traslapes validados en el backend y respaldados por restricciones `EXCLUDE` de Postgres (`btree_gist` + `tstzrange`). Reprogramar crea una cita nueva y marca la vieja `REPROGRAMADA` (nunca la edita). Frontend: pantalla Agenda con vistas día/semana/mes, agrupación por profesional o gabinete, calendario propio con arrastrar-para-reprogramar (HTML5 DnD, sin librería), colores por estado desde variables de tema, y botón "Iniciar atención" que crea el `Encounter` y navega a la nota SOAP | Hecho |
| 7 | `diagnosis` (texto libre + código opcional del catálogo, pieza/superficie validadas contra `odontogram/rules.py`) y `treatment` (`ProcedureCatalog` por sucursal, `TreatmentPlan` con fases y prioridad, `ProcedurePlanned`/`ProcedurePerformed` como entidades separadas —regla 3—, descuentos autorizados, aceptación total o parcial por ítem con fecha y responsable, PDF del presupuesto con el logo de la clínica). Lo planificado se refleja como `PLANNED` en el odontograma y, al realizarse, genera `PERFORMED` + `EXISTING` y retira el `PLANNED` (reusando la Fase 5 sin modificarla). Registrar un realizado genera un `Charge` "SUGERIDO" (módulo `billing` mínimo, nunca un pago —regla 4—). Dos permisos que faltaban desde la Fase 1 (`diagnosis.read`, `treatment.read`) agregados por migración incremental; bug de raíz corregido en `AccessDeniedAuditMiddleware` (guardaba la ruta completa en una columna de 100 caracteres). Frontend: quinta sección "Diagnósticos" en Expediente, pestaña nueva "Tratamientos" con el plan por fases, aceptación por checkboxes, descuentos, "marcar como realizado" y descarga de PDF | Hecho |
| 8 | `app/ai/` (`AiSuggestion`, `AiClinicSettings`): transcripción con `faster-whisper` (vocabulario dental en `initial_prompt`, VAD), pre-parser determinista de números FDI hablados (`dental_parser.py`), interpretación con Ollama (unión discriminada de 11 acciones como `format`, `temperature=0`, catálogos reales de la clínica), validación en dos capas (esquema + catálogos de BD), acciones prohibidas descartadas por tipo, aceptar/editar/rechazar por sugerencia (nunca escritura directa — regla 9), `origin=AI_ASSISTED` extendido a expediente/odontograma/diagnóstico/tratamiento (regla 10). `python -m app.ai.eval` + `tests/ai/corpus.jsonl` (50 dictados) miden precisión contra el Ollama real. Dos bugs de raíz corregidos probando con el modelo real: bucle de repetición infinito bajo decodificación forzada (`repeat_penalty`) y una acción con todos los campos opcionales que el modelo usaba como salida de mínimo esfuerzo (validador que exige al menos un valor). Frontend: micrófono + transcripción editable + panel de propuestas por destino dentro de la pantalla de Atención, con reserva de texto libre si Ollama no responde; Configuración → Asistente IA (estado, modelo, prueba de micrófono) | Hecho |
| 9 | `documents` (`DocumentTemplate` versionada regla 7, `Consent` firmado con `<canvas>` táctil, PDF con xhtml2pdf, hash SHA-256, ligado a lo sumo a un procedimiento o un plan) e `imaging` (`Image` por archivo, carga múltiple con metadatos compartidos, miniatura solo para JPG/PNG, lectura de PDF/imagen completa auditada). `StorageBackend` de la Fase 0 reutilizado tal cual (ya generaba rutas no adivinables). Frontend: `SignaturePad` con eventos de puntero (sin librería), visor de imágenes con zoom (`scale`) y brillo/contraste (`filter`) puramente en el cliente; pestañas nuevas "Consentimientos" e "Imágenes" en el paciente | Hecho |
| 10 | `billing` completo: `Payment` (efectivo/tarjeta/transferencia), `PaymentAllocation` (aplicación total o parcial a un cargo, o anticipo sin aplicar), saldo y estado de cada `Charge` calculados contra los pagos activos (regla 4, nunca guardados), cancelación de cargos/pagos con motivo (regla 2; un cargo con pagos aplicados no se puede cancelar sin cancelar esos pagos primero), recibo PDF con el logo de la clínica, corte de caja por sesión (`CashSession`, totales por método y diferencia contra lo esperado). `ClinicBillingSettings.billing_enabled` permite desactivar la cobranza por sucursal (p.ej. clínicas universitarias de práctica) sin dejar de generar el cargo sugerido al registrar un procedimiento realizado. Nuevo permiso `billing.configure` (incremental, solo `admin_clinica`). Frontend: pestaña "Cuenta" en el paciente, pantalla "Caja" para abrir/cerrar sesión, Configuración → Cobranza | Hecho |
| 11 | `reports` (sin tablas propias, seis reportes de solo lectura sobre modelos existentes: pacientes, citas y tasa de no-show, producción por profesional, planes de tratamiento, cuentas por cobrar como fotografía actual, uso del asistente de IA) con exportación CSV auditada (`reports.export`) y `GET /reports/dashboard`, un tablero de inicio por rol que no exige `reports.read` sino el permiso propio de cada sección que arma (`patients.read`, `agenda.read`, `treatment.read`, `billing.read`, `ai.use`/`ai.configure`). `scripts/backup.ps1`/`.sh` (pg_dump + storage/ cifrados con OpenSSL si hay `BACKUP_PASSPHRASE`, retención configurable) y `scripts/restore_test.ps1`/`.sh` (restaura en una base desechable, verifica y limpia) documentados en `docs/OPERACION.md`, con programación en Windows (Programador de tareas) y Linux (cron). Frontend: pantalla "Reportes" con selector de fechas y exportación por pestaña; página de inicio reconstruida como tablero por rol | Hecho |
| 12 | E2E con Playwright (flujo completo, accesibilidad con `axe-core`, rendimiento p95 ≤ 2 s), revisión de seguridad OWASP (cabeceras, docs deshabilitados en producción, `JWT_SECRET` obligatorio, `pip-audit`/`npm audit`) y documentación (`docs/SEGURIDAD.md`, `docs/MANUAL_USUARIO.md`, `docs/MANUAL_TECNICO.md`) | Hecho |
| 12.1 | Parte A de `docs/06_INSTRUCCIONES...`: 7 errores reportados corregidos de raíz (profesionales sin `Provider`, búsqueda de pacientes por palabra, selector de atención compartido + red de seguridad global de errores de mutación, plantillas de consentimiento sembradas, logo como enlace a inicio), puertos de E2E dedicados (8011/5185) y contraste WCAG corregido en los 4 presets de marca que faltaban — ver sección 5.13 | Hecho |
| 12.2 | Parte B completa de `docs/06_INSTRUCCIONES...`: **B1** catálogos de tipos de cita, hallazgos, diagnósticos, categorías de antecedentes y palabras clave de alerta administrables por sucursal (tabla genérica `clinic_catalog_items`, permiso `catalogs.manage`), pantalla Configuración → Catálogos (sección 5.14); **B2** gabinete por defecto del profesional (`Provider.default_resource_id`) y alta de usuario en varias sucursales a la vez; **B3** gabinete/profesional tratante por defecto del paciente (`Patient.default_resource_id`/`primary_provider_id`, edición controlada con motivo) y filtro "Mis pacientes" — ver sección 5.15 | Hecho |
| 13 (13.1–13.5, C3) | Parte C de `docs/06_INSTRUCCIONES...`: "Dentia" — 13.1 "Base de voz", 13.2 "Navegación", 13.3 "Captura en consulta", 13.4 "Diagnóstico, plan y agenda" (**completa**), 13.5 "Ruta LLM y dictado" (**completa**: ruta LLM clínica + ruta LLM de agenda — `app/voice/agenda_llm.py` — antes de rendirse; `modo_dictado`; `OLLAMA_INTENT_MODEL`/`OLLAMA_KEEP_ALIVE` dedicados) y C3 "Vocabulario odontológico" (**completo**: `app/ai/vocab/build.py` extrae ~1100 términos del diccionario + catálogos clínicos fijos hacia `hotwords`/corrección con `rapidfuzz` de `app/ai/stt.py`) — ver secciones 5.16 a 5.21. De 13.6 "Afinación": corpus de regresión (`tests/voice/commands.jsonl`, `app/voice/eval.py`) y primer E2E de voz (`e2e/tests/voice.spec.ts`, `VOICE_FAKE_MODE`) **hechos**; pruebas con audio con ruido real y entrenamiento de un modelo propio de palabra de activación **bloqueados** (necesitan grabaciones reales de la clínica que no existen — ver `docs/PENDIENTES_CLINICOS.md` #49); vocabulario por contexto (pantalla/catálogos de sucursal/pacientes del día, #47) **resuelto** — ver `app/voice/vocab_context.py`, sec. 5.21; esquema LLM dinámico por pantalla/rol (sec. 5.20) sigue sin hacerse | En curso |
| 14 | App móvil DENT-IA (`mobile/`, Expo SDK 57 + React Native 0.86 + TS estricto, cliente puro de `/api/v1`): dependencias alineadas (`npm install` + `expo install --fix`, `react`/`react-dom`/`react-native` pineados entre sí vía `overrides`), `npm run typecheck`/`npm test`/`npx expo-doctor` en verde. Contrato contra el backend verificado generando `src/api/schema.d.ts` con `openapi-typescript` y comparando cada tipo/endpoint a mano: varios mismatches reales corregidos en la app (query `starts_from`/`starts_to` de `/appointments`, `patient_full_name`/`provider_full_name`, `/ai/interpret` esperaba `transcript` no `text`, `/patients/.../odontogram` es un arreglo sin envolver, `expediente_number`/`date_of_birth`, alertas como `string[]` sin `severity` estructurada, forma real de `/branding` y `/ai/status`, `edits` no `payload` en aceptar sugerencia). Cambios B1–B5 del backend (docs/05_APP_MOVIL.md §7) verificados con pytest: B1/B2/B3/B5 ya los cumplía el backend tal cual (tokens siempre en el cuerpo, sin content-type gate en `/ai/transcribe`, nombres de campo de MFA ya correctos); **B4** sí requirió cambio real — `GET /me/clinics` ahora incluye `clinic_name` y `permissions` (aditivo, sin tocar `clinic`/`role` anidados que ya usa el frontend web) | Hecho |
| 15 | Marca DENT-IA en el sistema web (`docs/CAMBIOS_WEB_MARCA.md` W1–W7, misma paleta que `DENTIA_BRAND` de `mobile/src/theme/theme.tsx`): preset `dentia` nuevo y por defecto para sucursales nuevas (W1), `GET /branding/logo`\|`/favicon` ya no 404 — sirven el logo/favicon de DENT-IA por defecto, `has_custom_logo` distingue cuál se muestra (W2), pie de página de marca en los tres PDF (presupuesto, recibo, consentimiento — fuera del contenido firmado, W3), "DentalCare"/"DENTIA" → "DENT-IA" en textos visibles del backend y frontend (W4), `index.html`/favicon/manifest PWA (W5), tokens de marca fijos (`--brand-dentia-*`) y tipografía Montserrat en encabezados, más `dark_primary` opcional por preset derivado en `theme/store.ts` si falta (W6), componentes `src/components/brand/Brand.tsx` (`DentiaLogo`, `ClinicLogo`, `DentiaIsotipo`, `PoweredByDentia`, `BrandStripe`) usados en login y barra lateral (W7). Verificado en vivo: `pytest` completo, `ruff`/`black`/`mypy`, `npm run build`/`lint`/`test` del frontend, y la suite completa de Playwright (incluida `accessibility.spec.ts`, sin violaciones nuevas) contra el sistema corriendo de verdad; capturas de `docs/manual/` regeneradas con `CAPTURE_SCREENSHOTS=1` | Hecho |
| 16 | A petición del operador, dos tandas de cambios sobre el sistema ya existente, sin módulos nuevos. **Primera tanda:** horario laboral por defecto abierto los 7 días sin restricción de hora (antes lunes–viernes con hora de comida); nombre comercial de la clínica (`ClinicBranding.display_name`) ahora siempre visible junto al logo (barra lateral y login), no solo con logo propio; menú **Ayuda** nuevo en la barra lateral (`frontend/src/modules/help/HelpPage.tsx`), visible para cualquier rol, con el contenido de `docs/MANUAL_USUARIO.md` adaptado, resumen de qué hace cada rol y las capturas de `docs/manual/`; paciente de ejemplo completo en el seed (`_seed_example_patient`, `app/seed.py`) con expediente, odontograma, plan de tratamiento y citas. **Segunda tanda (bugs reales encontrados al probar lo anterior):** `SignaturePad` (`frontend/src/modules/documents/SignaturePad.tsx`) tenía un bug de raíz — su resolución interna (`canvas.width`/`height`, fija en 400×150) no coincidía con su tamaño real en pantalla (estirado por `flex`/`max-width:100%`), así que solo la esquina superior izquierda del área visible respondía al trazo; corregido igualando ambas en un `ResizeObserver`. De paso: las plantillas de consentimiento ya no se crean desde la ficha de un paciente (solo se previsualizan — decisión registrada en `docs/PENDIENTES_CLINICOS.md`), el PDF firmado se abre de inmediato para revisar/imprimir (antes había que buscarlo en la lista), y un fallo al firmar ahora se muestra en pantalla (antes fallaba en silencio). `TreatmentPlan`/`PlanOut`/`PlanDetailOut` exponen `professional_name` (quién atiende, ya existía como `professional_id` pero nunca se resolvía a nombre). `GET /appointments` acepta `patient_id` (antes solo `provider_id`/`resource_id`), usado por una tarjeta "Citas" nueva en el Resumen del paciente para mostrar su historial de citas con estado (asistió/no asistió/etc.) | Hecho |
| 17 | A petición del operador: "Control de versiones", pantalla nueva visible solo para administradores (`version_info.read`, superadmin/admin_clinica) que muestra qué versión de DentalCare está corriendo. Backend: `Settings.app_version` (`backend/app/core/config.py`, lee la variable de entorno `VERSION` vía `validation_alias`, default `"dev"`) y paquete nuevo sin tablas `app/modules/version_info/` (`GET /version-info` → `{version, environment}`, permiso nuevo incremental igual patrón que `document_settings.manage`). `deploy/vps/compose/docker-compose.yml` ahora reenvía `VERSION: ${VERSION}` al contenedor `api` — antes esa variable solo se usaba para resolver el tag de imagen a descargar, el proceso de la API no tenía forma de saber en qué versión corría. Frontend: `frontend/src/modules/version_info/VersionInfoPage.tsx` (`/configuracion/version`, nav lateral junto a "Formatos de documentos"), con enlace externo al historial de releases de GitHub en vez de llamar a la API de GitHub desde el backend (evita una dependencia externa innecesaria) | Hecho |

**Verificación en vivo de Parte A (2026-10-09):** los 7 puntos de la sección 5.13 se
reprodujeron de nuevo contra el sistema corriendo de verdad (backend/frontend/Postgres/Ollama
reales, no solo pytest) y siguen funcionando — no hizo falta corregir nada de Parte A. De paso
se encontraron y corrigieron dos bugs reales de Fase 13 (Parte C, ya implementada), ninguno
reportado en `docs/06_INSTRUCCIONES...`:
- **Lentitud generalizada:** `VoiceSession._process_wake_audio` (`app/voice/session.py`)
  volvía a transcribir con Whisper el búfer completo en cada frame de audio que llegaba (el
  `AudioWorklet` real manda uno cada ~30 ms) una vez pasado el umbral de 1.5 s, sin ningún
  límite — con voz/ruido de consultorio de por medio, eso disparaba Whisper decenas de veces
  por segundo mientras la sesión de voz siguiera abierta y sin silenciar (visto en vivo: el
  proceso de `uvicorn` al ~400 % CPU). Corregido con un intervalo mínimo de 0.5 s entre
  intentos (`_WAKE_CHECK_MIN_INTERVAL_S`); prueba nueva
  `tests/unit/voice/test_session_wake_throttle.py`.
- **Prueba intermitente de `reprogramar_cita`:** `test_reprogramar_cita_moves_the_appointment_keeping_the_time`
  fallaba cualquier viernes (como el día en que se corrió esta verificación) porque
  `datetime_parse.py` resuelve "el viernes" a *hoy* cuando hoy mismo ya es viernes (deliberado:
  "si hoy mismo es ese día, es hoy"), así que la cita vieja (ahora REPROGRAMADA) cae en el mismo
  rango de fecha que se consulta — y el calendario real no oculta las citas reprogramadas, las
  muestra con otro color en su lugar original (`agenda/catalog.ts`), así que `list_appointments`
  no debe filtrarlas. No era un bug de producción: se corrigió la prueba para que verifique la
  fila RESERVADA nueva específicamente, no la cantidad total de filas del día.

El módulo `reports` de la sección 2 ya existe, sin tablas propias (es deliberadamente solo
consultas de lectura). `patients`, `records`/`encounters`, `odontogram`, `agenda`, `diagnosis`,
`treatment`, `ai`, `documents`, `imaging`, `billing` y `reports` ya existen completos, incluida
la pestaña "Cuenta" del paciente, la pantalla "Caja", Configuración → Cobranza (Fase 10) y la
pantalla "Reportes" más el tablero de inicio por rol (Fase 11).
