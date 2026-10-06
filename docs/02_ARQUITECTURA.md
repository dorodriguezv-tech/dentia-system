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
| `documents` | DocumentTemplate (versionada), Consent |
| `imaging` | Image (metadatos + pieza/procedimiento) |
| `billing` | Charge, Payment, PaymentAllocation, CashSession, ClinicBillingSettings |
| `reports` | Vistas/consultas de solo lectura |
| `audit` | AuditEvent |

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

### 5.2 Tema y marca (Fase 2)
- **Catálogo único:** `backend/app/modules/branding/presets.py` es la fuente de verdad de los
  6 presets y de los colores compartidos (`frontend/src/theme/presets.ts` es su copia para la
  UI, igual que el patrón ya usado con el catálogo de permisos de IAM).
- **`GET /branding` es público** (lo necesita la pantalla de login antes de autenticar) y
  resuelve "la" sucursal como la más antigua (`clinics.created_at`); ver pendiente #12 en
  `docs/PENDIENTES_CLINICOS.md` para multi-sucursal.
- **Derivación de color:** `--color-primary-hover`/`-soft` (y `-danger-soft`) nunca se guardan;
  se calculan en el cliente (`theme/colorUtils.ts`) cada vez que se aplica el tema, con la misma
  fórmula HSL que el backend (`color_utils.py`) usa para sugerir ajustes de contraste.
- **Contraste WCAG:** `PUT /branding` siempre guarda lo que mandó el admin (no lo rechaza) pero
  devuelve `contrast_warnings` con el color sugerido si texto/fondo o texto-de-boton/primario
  bajan de 4.5:1; la pantalla de Apariencia calcula lo mismo en vivo mientras se edita.
- **Modo oscuro:** no hay una paleta oscura dibujada a mano por preset; se usa una base neutra
  oscura fija (`DARK_OVERRIDES` en el frontend) y se conservan primary/secondary/accent/
  success/warning/danger del preset.
- **Logo:** PNG/JPG/SVG, máximo 1 MB. El SVG se sanea con `xml.etree` (quita `<script>`,
  `<foreignObject>`, `<style>`, atributos `on*` y `javascript:`) en vez de rechazarse. El favicon
  se genera con Pillow (PNG/JPG a 64×64) o reutiliza el SVG saneado. Los archivos se sirven por
  `GET /branding/logo` y `/branding/favicon`, publicos a propósito (son la imagen de marca, no
  datos clínicos) — a diferencia de `storage/` en general, que nunca se sirve como estático.

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

### 5.5 Odontograma (Fase 5)
- **Catálogos configurables (sec. 7):** `odontogram/rules.py` genera las 32 piezas FDI permanentes
  (11–48) y las 20 temporales (51–85) por fórmula (no a mano); calcula las 5 superficies clicables
  de cada pieza (P solo en piezas superiores, L en inferiores; I solo en anteriores —incisivos y
  canino—, O en posteriores). `odontogram/finding_catalog.py` trae los 12 hallazgos por defecto
  (sano, caries, restauración, corona, endodoncia, ausente, extracción indicada, implante, prótesis
  fija, sellador, fractura, movilidad) con color y símbolo; ninguno validado aún con la clínica
  (pendientes #14 en `docs/PENDIENTES_CLINICOS.md`).
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
- **Frontend — SVG propio sin librerías de terceros:** `Tooth.tsx` dibuja 5 rectángulos en cruz
  (arriba=V, abajo=P/L según si la pieza es superior o inferior, centro=O/I según sea posterior o
  anterior, izquierda/derecha=M/D según el lado de la arcada para que mesial siempre mire a la línea
  media) dentro de un `viewBox` de 44×44 — el recuadro completo de la pieza es el objetivo táctil
  principal (≥44 px, CLAUDE.md Fase 5); las 5 zonas internas son más finas y pensadas para precisión
  con mouse/stylus. El color de cada hallazgo se aplica vía `fill="var(--color-finding-<codigo>)"`
  (variables nuevas en `theme/tokens.css`, semánticas y fijas como `--color-danger`, no derivadas de
  la marca de la clínica) — nunca un `#hex` literal en el componente (CLAUDE.md sec. 6).
  `kind="PLANNED"` se dibuja con `stroke-dasharray` (contorno discontinuo).
  `Arch.tsx`/`Odontograma.tsx` arman las arcadas superior/inferior y las vistas permanente/
  temporal/mixta (en mixta, la fila de temporales se dibuja sobre la de permanentes, pendiente #10).
  Elegir una pieza/superficie abre `FindingQuickMenu` (selector de atención + catálogo de hallazgos
  en botones de ≥44 px) y `ToothHistoryPanel` (historial completo de esa pieza, con autor). El
  control de fecha (`<input type="date">`) cambia `at` y pone la vista en solo lectura con un aviso.

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

## 7. Respaldo
- `pg_dump` diario cifrado, copia de `storage/` y retención configurable.
- Script `scripts/restore_test.ps1`/`.sh` que restaura en una base temporal y registra el resultado.

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
| 11–12 | Ver `prompts/PROMPTS_CLAUDE_CODE.md` | Pendiente |

El módulo de reports de la sección 2 es el diseño objetivo; no tiene modelos ni migraciones
todavía — se crea conforme avanza su fase (11–12). `patients`, `records`/`encounters`,
`odontogram`, `agenda`, `diagnosis`, `treatment`, `ai`, `documents`, `imaging` y `billing` ya
existen completos, incluida la pestaña "Cuenta" del paciente, la pantalla "Caja" y
Configuración → Cobranza de la sección 6 (Fase 10).
