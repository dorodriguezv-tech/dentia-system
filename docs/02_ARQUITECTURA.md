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
| POST | /diagnoses, /treatment-plans, /treatment-plans/{id}/accept | Clínico |
| POST | /ai/transcribe, /ai/interpret, /ai/suggestions/{id}/accept\|reject | Asistente IA |
| GET | /ai/status | Estado de Ollama y Whisper |
| POST | /payments, /charges | Cobranza |
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

## 6. Frontend
- **Layout:** barra lateral (logo de la clínica), búsqueda global de pacientes y **encabezado de paciente persistente** con barra de alertas.
- **Pestañas del paciente:** Resumen | Expediente | Odontograma | Tratamientos | Imágenes | Documentos | Cuenta.
  La Agenda (Fase 6) no es una pestaña del paciente: es una pantalla propia en el menú lateral
  (`/agenda`), porque una cita es de la clínica/profesional, no de un paciente concreto — se llega
  a un paciente *desde* la cita, no al revés.
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
| 1 | IAM (`organizations`, `clinics`, `users`, `roles`, `permissions`, `user_clinics`, `refresh_tokens`) y `audit` (`audit_events` append-only). Login JWT + MFA TOTP + rate limiting, `require_permission` por `X-Clinic-Id`, catálogo de permisos seedeado por migración (`docs/MATRIZ_PERMISOS.md`), `app/seed.py` con admin y odontólogo ficticios. Frontend: login, selección de sucursal, gestión de usuarios, guardia de rutas por permiso | Hecho |
| 2 | `clinic_branding` (nombre, logo, favicon, preset o colores personalizados, modo oscuro, radio de bordes). `GET /branding` público, `PUT /branding` y `POST /branding/logo` con permiso `branding.manage`. 6 presets + derivación de hover/soft + validación de contraste WCAG (avisa y sugiere, no bloquea). SVG saneado (sin `<script>`/eventos), favicon generado con Pillow. Frontend: `ThemeProvider`, pantalla Configuración → Apariencia (preset, colores, logo, vista previa en vivo, restablecer) y script que verifica que no haya colores fijos fuera de `theme/` | Hecho |
| 3 | `patients` (alta, edición controlada con motivo, 5 estados, contactos tutor/emergencia, foto permisionada) y expediente autonumérico por sucursal. Búsqueda tolerante (`pg_trgm` + `unaccent`) y detección de duplicados (nombre + nacimiento o teléfono) con confirmación obligatoria. Lectura de ficha auditada. Frontend: búsqueda global (`Ctrl+K`), listado con filtro de estado, alta en 3 pasos (datos → posibles duplicados → contactos), encabezado persistente del paciente (nombre, edad, foto, barra de alertas vacía) y controles de edición ocultos para roles sin `patients.write`. Seed con 50 pacientes ficticios (Faker es_MX) | Hecho |
| 4 | `records` (antecedentes, alergias, medicamentos, signos vitales; anulación con motivo, no borrado) y `encounters` (atención + nota clínica SOAP versionada: DRAFT→FINAL→CORRECTED\|CANCELLED). Alertas críticas derivadas (no almacenadas) a partir de alergias/medicamentos/antecedentes, exigidas antes de finalizar una nota (regla 8). Dos bugs de raíz corregidos: constraint de paciente ausente del modelo (autogenerate destructivo) y `MissingGreenlet` en columnas `onupdate` (fix global con `eager_defaults`). Frontend: pestañas Resumen (línea de tiempo clínica, "Iniciar atención") y Expediente (secciones colapsables) del paciente, pantalla de Atención con SOAP, autoguardado cada 10 s, modal de alertas antes de finalizar, corregir/cancelar con motivo. Seed con 3 encounters de ejemplo (nota finalizada, nota en borrador, nota corregida) | Hecho |
| 5 | `odontogram` (`ToothFinding` como eventos con `supersedes_id`/`is_current`, índice único parcial por pieza/superficie/tipo; catálogos de piezas FDI, superficies y hallazgos en `rules.py`/`finding_catalog.py`). Reconstrucción histórica vía `GET .../odontogram?at=`. Frontend: pestaña Odontograma con SVG propio (arcadas superior/inferior, vistas permanente/temporal/mixta, 5 superficies clicables, menú rápido de hallazgos, leyenda, deslizador de fecha de solo lectura, panel de historial por pieza) | Hecho |
| 6 | `agenda` (`Provider`, `Resource`, horario laboral y bloqueos informativos, `Appointment` con máquina de estados RESERVADA→CONFIRMADA→EN_SALA→EN_ATENCION→TERMINADA \| CANCELADA/NO_SHOW/REPROGRAMADA, `AppointmentStatusHistory`, `ReminderTask` idempotente, lista de espera). Traslapes validados en el backend y respaldados por restricciones `EXCLUDE` de Postgres (`btree_gist` + `tstzrange`). Reprogramar crea una cita nueva y marca la vieja `REPROGRAMADA` (nunca la edita). Frontend: pantalla Agenda con vistas día/semana/mes, agrupación por profesional o gabinete, calendario propio con arrastrar-para-reprogramar (HTML5 DnD, sin librería), colores por estado desde variables de tema, y botón "Iniciar atención" que crea el `Encounter` y navega a la nota SOAP | Hecho |
| 7–12 | Ver `prompts/PROMPTS_CLAUDE_CODE.md` | Pendiente |

Los módulos de agenda/diagnosis/treatment/documents/imaging/billing/reports/ai de la sección 2 son
el diseño objetivo; ninguno tiene modelos ni migraciones todavía — se crean conforme avanza cada
fase. `patients`, `records`/`encounters` y `odontogram` ya existen pero todavía sin las pestañas de
Tratamientos, Imágenes, etc. de la sección 6 (llegan con sus respectivas fases).
