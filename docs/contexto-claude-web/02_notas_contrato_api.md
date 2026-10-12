# Contrato real de la API — nombres de campo no obvios

> Generado el 2026-10-12 comparando cada endpoint contra el backend real con
> `openapi-typescript` (ver `mobile/src/api/schema.d.ts`, que se puede regenerar en
> cualquier momento con `npx openapi-typescript http://localhost:8001/openapi.json
> -o schema.d.ts` mientras el backend corre). Esta lista existe porque varios
> nombres de campo "razonables" que alguien (o la propia IA) asumiría por
> convención **no coinciden** con lo real — sin este archivo, una conversación sin
> acceso al código los va a adivinar mal. Si dudas de algo que no está aquí, pide
> que se regenere `schema.d.ts` o se revise el router/schema real antes de asumir.

## Agenda
- `GET /appointments` recibe **`starts_from`/`starts_to`** (no `date_from`/`date_to`).
- Cada cita trae **`patient_full_name`/`provider_full_name`** (no `patient_name`/
  `provider_name`), más `provider_color`, `resource_id`, `resource_name`.
- `PATCH /appointments/{id}/status` recibe `{status, reason}` — `status` es el
  enum en mayúsculas (`RESERVADA`, `EN_SALA`, ...).

## Pacientes
- `expediente_number` (no `expediente`), `date_of_birth` (no `birth_date`),
  ambos siempre presentes (no opcionales).
- `status` del paciente es un enum en **minúsculas**: `activo`, `inactivo`,
  `referido`, `fallecido`, `bloqueado` — fácil de confundir con el de citas, que sí
  va en mayúsculas.
- `GET /patients/{id}/summary`: `alerts` es un **`string[]` simple** — no hay
  `kind`/`severity`/objeto estructurado en ningún endpoint todavía (tampoco en
  `GET /patients/{id}/alerts`, que es lo mismo en forma dedicada). No tiene `sex`;
  si hace falta, está en `GET /patients/{id}` (ficha completa), no en `/summary`.
  `has_photo: boolean` sí está en `/summary`.

## Odontograma
- `GET /patients/{id}/odontogram` responde un **arreglo directo**
  (`ToothFindingOut[]`), no `{findings: [...]}`.
- `POST /tooth-findings` sí coincide con lo esperado: `{patient_id, encounter_id,
  tooth_fdi, surface, finding_code, kind (default EXISTING), material}`.

## Asistente de IA (dictado)
- `POST /ai/interpret` recibe **`{encounter_id, transcript}`** solamente — no
  `patient_id` ni `screen` (esos campos no existen en el esquema).
- `POST /ai/suggestions/{id}/accept` recibe **`{edits}`** (no `{payload}`) —
  `edits` sobreescribe campos del payload original antes de aplicarlo, opcional.
- `POST /ai/transcribe`: el campo multipart se llama `audio` (no `file`); no hay
  filtro de content-type — acepta webm, mp4/m4a (Android), lo que sea que
  faster-whisper/PyAV puedan decodificar.
- `GET /ai/status` responde `{ai_enabled, ollama_reachable, ollama_model,
  ollama_digest, whisper_model, whisper_device}` — no `{ollama, whisper, model}`.
  Requiere el permiso `ai.configure` (no `ai.use`, que es el de dictar).
- `InterpretResponse.unrecognized` es `{text, reason}[]`, no `string[]`.

## Marca y tema (`/branding`)
- Campos reales: `display_name` (no `clinic_name`), `colors.bg` (no
  `colors.background`), más `surface`, `border`, `text_muted`, `dark_mode`,
  `radius`, `preset`, `subtitle`, `favicon_url`, `has_custom_logo`,
  `contrast_warnings[]`.
- `GET /branding/logo` y `/branding/favicon` **siempre responden 200** (nunca
  404): sin logo propio, sirven el de DENT-IA por defecto. `has_custom_logo`
  dice si el que se está mostrando es el propio.
- Preset por defecto: `dentia` (antes `menta_clinica`) — colores exactos:
  primario `#0A5A8C`, secundario `#1690B6`, acento `#22AAC2`, `dark_primary`
  `#4FC3D9`. Mismos valores en backend, frontend web y la app móvil
  (`DENTIA_BRAND` en `mobile/src/theme/theme.tsx`) — si alguno cambia, deben
  cambiar los tres a la vez.

## Sesión / sucursales
- `GET /me/clinics` responde **`{clinic: {...}, role: {...}, clinic_name,
  permissions}[]`** — `clinic.id` es el id de la sucursal (no hay `clinic_id`
  plano en la raíz); `permissions` es la lista de códigos de permiso de ese rol
  en esa sucursal.
- Login/refresh/logout **siempre** devuelven `access_token`/`refresh_token` en
  el cuerpo JSON (nunca cookies httpOnly) — no hace falta ningún header especial
  para que el cliente móvil los reciba.
- MFA: `/auth/login` responde `{mfa_required: true, mfa_token}` cuando falta el
  segundo factor; `/auth/login/mfa` recibe `{mfa_token, code}`.

## Imágenes clínicas
- `POST /patients/{id}/images`: `encounter_id` es **obligatorio** (no opcional);
  `study_type` es un enum en minúsculas: `intraoral`, `extraoral`, `periapical`,
  `bitewing`, `panoramica`, `cefalometria`. El campo de archivos se llama `files`
  (acepta varios en la misma petición).

## Qué NO ha cambiado (para no perder tiempo revisándolo de nuevo)
`POST /tooth-findings`, `POST /appointments/{id}/start-encounter`,
`PATCH /appointments/{id}/status`, `GET/POST /encounters`,
`GET /ai/suggestions`, `/ai/suggestions/{id}/reject` (`{reason}`) ya coinciden
con lo que cualquiera asumiría por convención — confirmados contra el backend
real en esta misma revisión.
