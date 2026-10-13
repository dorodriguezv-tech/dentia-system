# Paridad web ↔ móvil — Auditoría M0

Fecha: 2026-10-12. Generado para `docs/06_APP_MOVIL_V1_1_PARIDAD.md` bloque **M0**.
Método: lectura directa de `frontend/src/modules/*`, `mobile/app/*` + `mobile/src/*` y
`backend/app/modules/*` (routers, schemas, service). No se cambió código para este bloque.

---

## 1. Tabla de paridad por flujo

| Funcionalidad | Web (`frontend/src/modules/...`) | Móvil (`mobile/...`) | Endpoint(s) | Permiso | ¿Va en móvil (v1.1)? |
|---|---|---|---|---|---|
| Login + MFA | `auth/LoginPage`, `auth/MfaSetupPage` | `app/login.tsx` | `POST /auth/login`, `/auth/login/mfa` | — | Ya existe |
| Elegir sucursal | `auth/ClinicSelectPage` | `app/sucursal.tsx` | `GET /me/clinics` | — | Ya existe |
| **Cerrar sesión** | cierre de sesión del navegador (no hay botón explícito equivalente; se basa en expirar/borrar cookies) | `app/(app)/ajustes.tsx` → `doLogout()` | `POST /auth/logout` | — | **M1** (ya funciona en código; faltan confirmación y resiliencia — ver §3 R5) |
| Agenda: listar | `agenda/AgendaPage`, `CalendarGrid`, `MonthGrid` | `app/(app)/index.tsx` | `GET /appointments` | `agenda.read` | Ya existe (solo vista día) |
| Agenda: **crear cita** | `agenda/NewAppointmentForm` | — (no existe) | `POST /appointments` | `agenda.write` | **M3** |
| Agenda: reprogramar | `agenda/api.ts::rescheduleAppointment` | — (no existe) | `POST /appointments/{id}/reschedule` | `agenda.write` | **M3** |
| Agenda: cancelar / no-show / check-in | `agenda/api.ts::changeAppointmentStatus` | solo "Llegó" (`EN_SALA`) | `PATCH /appointments/{id}/status` | `agenda.write` | **M3** (cancelar con motivo, no-show) |
| Agenda: disponibilidad | cálculo en `agenda/service.py::find_free_slots` pero **sin endpoint propio** (ver §4) | — | — (no existe ruta) | — | **M3/M7** depende de **B8** |
| Lista de espera | `agenda/api.ts` (`listWaitlist`, etc.) | — | `GET/POST /waitlist`, `POST /waitlist/{id}/resolve` | `agenda.read/write` | Fuera de alcance v1.1 (no listado en M0-M8) |
| Iniciar atención desde cita | `agenda` (botón en `AgendaPage`) | `index.tsx::start` | `POST /appointments/{id}/start-encounter` | `records.write` | Ya existe |
| Iniciar atención **sin cita** (urgencia) | `encounters/api.ts::createEncounter` con `appointment_id: null` | — (no existe botón) | `POST /encounters` (`appointment_id` opcional) | `records.write` | **M4** — el backend ya lo soporta, falta el botón/flujo en la app |
| Pantalla de atención / dictado | `encounters/AtencionPage` (todo: resumen, nota, odontograma, dictado) | `app/atencion/[id].tsx` (**solo** dictado + propuestas IA) | ver filas siguientes | — | **M4** (pestañas Resumen/Nota/Procedimientos) |
| Nota clínica: crear/editar borrador | `encounters/AtencionPage` | — (no existe) | `POST /encounters/{id}/notes`, `PATCH /notes/{id}` | `records.write` | **M6** |
| Nota clínica: finalizar | `encounters/AtencionPage` | — (no existe) | `POST /notes/{id}/finalize` (requiere `alerts_acknowledged`) | `records.write` | **M6** |
| Nota clínica: corregir / cancelar | `encounters/AtencionPage` | — (no existe; por diseño: "Corregir en la web") | `POST /notes/{id}/correct`, `/cancel` | `records.write` | No va en móvil (regla 1 + decisión de producto) |
| **Cerrar consulta** (encounter) | **No existe tampoco en la web** — ver §4, hallazgo nuevo | — | No existe `POST /encounters/{id}/close`; `ended_at` nunca se escribe en ningún service | `records.write` | **M6** depende de **B11** (nuevo en ambos lados, no solo móvil) |
| Cita queda "Atendida" | manual: alguien cambia el estado a `TERMINADA` con `PATCH /appointments/{id}/status` | — | `PATCH /appointments/{id}/status` `{status: "TERMINADA"}` | `agenda.write` | **M6** debe disparar esta llamada (la web tampoco la automatiza) |
| Odontograma: ver | `odontogram/Odontograma`, `OdontogramaTab` | `paciente/[id].tsx` + `components/Odontogram.tsx` | `GET /patients/{id}/odontogram` | `odontogram.read` | Ya existe |
| Odontograma: **crear** hallazgo | `odontogram/api.ts::createToothFinding` | `endpoints.ts::createToothFinding` | `POST /tooth-findings` | `odontogram.write` | Ya existe (solo si hay "atención de hoy") |
| Odontograma: **cambiar** hallazgo vigente | igual que crear: un nuevo `POST /tooth-findings` con la misma pieza/superficie/`kind` hace `supersedes_id` automáticamente (`service.create_finding`) | no implementado en la UI (el `FindingSheet` solo agrega) | `POST /tooth-findings` | `odontogram.write` | **M5** — el backend YA soporta "cambiar" vía create; falta exponerlo en la UI como acción explícita |
| Odontograma: **resolver/anular** hallazgo vigente con motivo | **No existe en ningún lado.** `odontogram/service.py::retire_finding` existe pero **no tiene ruta en el router** — solo lo llama `app/voice/dialogue.py` (el "deshacer" de Dentia, Fase 13.3), directo al service, sin pasar por un endpoint HTTP ni pedir motivo | no implementado | — (no existe endpoint) | — | **M5** depende de un cambio de backend nuevo, no listado en B7–B11 (ver §4, **B12**) |
| Odontograma: historial por pieza | `ToothHistoryPanel` | `FindingSheet` (lista simple) | `GET /patients/{id}/teeth/{fdi}/history` | `odontogram.read` | Ya existe |
| Plan de tratamiento: ver | `treatment/TreatmentTab`, `PlanDetail` | — (no existe) | `GET /patients/{id}/treatment-plans`, `GET /treatment-plans/{id}` | `treatment.read` | **M4** (pestaña Resumen: "plan vigente") — solo lectura, ya soportado por el backend |
| Plan de tratamiento: crear/aceptar/anular ítem | `treatment/api.ts` | — | `POST /treatment-plans`, `/accept`, `/items/{id}/annul`, etc. | `treatment.write` / `treatment.accept_budget` | Fuera de alcance v1.1 (no está en M0–M8; coherente con "cobranza y planes se usan mejor en computadora") |
| Procedimientos realizados | `treatment/api.ts` | — | `POST /procedures-performed`, `GET /patients/{id}/procedures-performed` | `treatment.write`/`read` | **M4** (pestaña "Procedimientos" — regla 3: separado de lo planificado) |
| Preferencias de usuario (idioma, voz, tema) | **No existe ninguna pantalla ni endpoint** — la web no tiene concepto de "preferencias por usuario" hoy; el tema es por sucursal (`branding/api.ts`) | `app/(app)/ajustes.tsx` (solo voz de Dentia, en memoria del proceso, no persistida) | — (no existe ruta) | — | **M2** depende de **B7** (nuevo en ambos lados) |
| Marca / branding de la clínica | `branding/AppearancePage` | `ajustes.tsx` (solo lectura del logo vía `theme.tsx`) | `GET /branding`, `PATCH /clinics/current` | `catalogs.manage` | Ya existe (lectura); edición no está en alcance móvil |
| Fotos clínicas | `imaging/ImagesTab` | `paciente/[id].tsx::photo` | `POST /patients/{id}/images` | `imaging.write` | Ya existe |
| Alertas clínicas | `PatientHeader`, `AtencionPage` | `AlertBar` en `paciente/[id].tsx` y `atencion/[id].tsx` | `GET /patients/{id}/alerts` (vía `getPatientSummary`) | `records.read` | Ya existe |

---

## 2. Endpoints que usa la web, por flujo de §M0

| Flujo | Endpoints (web) |
|---|---|
| Crear cita | `POST /appointments` |
| Editar cita | No existe "editar" genérico: se reprograma (abajo) o se cambia estado |
| Reprogramar cita | `POST /appointments/{id}/reschedule` |
| Cancelar cita | `PATCH /appointments/{id}/status` con `{status: "CANCELADA", reason}` |
| Disponibilidad | **Ninguno expuesto.** Existe `agenda/service.py::find_free_slots` pero no hay ruta en `agenda/router.py` que lo llame; la web tampoco lo consume hoy (no hay buscador de horarios libres en `NewAppointmentForm`, a confirmar con un vistazo rápido si se agregó después — no se encontró uso en `agenda/api.ts`) |
| Iniciar atención (encounter) | `POST /appointments/{id}/start-encounter` (desde cita) · `POST /encounters` con `appointment_id` opcional (sin cita) |
| Nota clínica — crear | `POST /encounters/{id}/notes` |
| Nota clínica — guardar borrador | `PATCH /notes/{id}` (mismo endpoint, no cambia `status`) |
| Nota clínica — finalizar | `POST /notes/{id}/finalize` body `{alerts_acknowledged}` |
| Nota clínica — corregir | `POST /notes/{id}/correct` body `{reason}` (crea versión `CORRECTED`) |
| Nota clínica — cancelar | `POST /notes/{id}/cancel` body `{reason}` |
| Hallazgos odontograma — crear | `POST /tooth-findings` |
| Hallazgos odontograma — cambiar | mismo `POST /tooth-findings` (el service detecta el vigente de esa pieza/superficie/`kind` y lo supera) |
| Hallazgos odontograma — resolver | **No existe endpoint.** No hay concepto de "resuelto" en el modelo (`ToothFinding` solo tiene `is_current`, no un estado "resuelto/tratado" distinto de superar con PERFORMED) |
| Hallazgos odontograma — anular | **No existe endpoint HTTP.** El service `retire_finding` existe pero solo se usa internamente desde `app/voice/dialogue.py` (deshacer de Dentia), sin pasar por el router, sin permisos declarados vía `require_permission`, y sin pedir motivo |
| Plan de tratamiento | `GET/POST /treatment-plans`, `GET /treatment-plans/{id}`, `PATCH /treatment-plans/{id}/status`, `POST /treatment-plans/{id}/accept`, fases e ítems (`/phases`, `/items/{id}/annul`, `/items/{id}/discount`) |
| Preferencias de usuario | **No existen.** No hay módulo `preferences` ni campos de preferencia en `User` (confirmado: no hay ningún archivo ni ruta con "preference" en `backend/app`) |
| Logout | La web no tiene un botón "cerrar sesión" equivalente con `POST /auth/logout` localizado en sus módulos (no se encontró uso de `/auth/logout` en `frontend/src`); probablemente se apoya en que el token expira o se borra localStorage/cookies. Confirmar con el equipo si falta paridad inversa (web no cierra sesión en servidor) — **no es tarea de este documento, solo se deja constancia** |

---

## 3. Causas de la tabla §0 — confirmadas o descartadas

| # | Causa propuesta | Veredicto | Evidencia |
|---|---|---|---|
| R1 | "La v1.0 nunca implementó `POST /appointments`; solo cambios de estado" | **CONFIRMADA** | `mobile/src/api/endpoints.ts` solo tiene `listAppointments` y `setAppointmentStatus`. No hay `createAppointment`, `rescheduleAppointment` ni cancelación con motivo. |
| R2 | "El botón solo aparece en citas EN_SALA y con permiso `ai.use`; ... no hay forma de iniciar atención desde la ficha del paciente" | **PARCIALMENTE CONFIRMADA.** El botón "Iniciar atención" en `index.tsx` en realidad aparece para `RESERVADA`, `CONFIRMADA` **y** `EN_SALA` (no solo `EN_SALA`) y exige `records.write` (no `ai.use` — ese dato del documento está desactualizado). Pero la segunda mitad es correcta: `paciente/[id].tsx` solo ofrece "Dictar con IA" cuando **ya** existe una `todayEncounter`; no hay botón para crear un encounter nuevo desde la ficha (urgencia / sin cita). | `mobile/app/(app)/index.tsx:93-100`, `mobile/app/paciente/[id].tsx:87-92` |
| R3 | "El odontograma no permite cambios... depende de una atención de hoy... solo permite registrar, no cambiar/resolver/anular" | **CONFIRMADA en ambas partes.** `canWriteOdo = hasPermission('odontogram.write') && !!todayEncounter`. `FindingSheet` solo expone el catálogo para **crear** (`addFinding`); no hay acción de cambiar/resolver/anular un hallazgo vigente. | `mobile/app/paciente/[id].tsx:33,105-168` |
| R4 | "La pantalla de Ajustes completa está protegida con un permiso de administración... idioma y voz son preferencias personales" | **DESCARTADA como causa, confirmada como síntoma distinto.** `ajustes.tsx` ya es visible para **todos** los usuarios (no hay guard de permiso en la pantalla); solo la tarjeta "Asistente de IA" está condicionada a `ai.configure`. El problema real es que **no existe selector de idioma** (solo hay selector de voz, y no se persiste en ningún lado — ni local ni remoto). | `mobile/app/(app)/ajustes.tsx` completo |
| R5 | "`await api.logout()` falla... la excepción corta la función antes de borrar el token" | **DESCARTADA tal como está descrita — el bug específico ya no existe en el código actual.** `logout()` en `endpoints.ts` ya atrapa su propio error (`.catch(() => undefined)`), y `doLogout()` en `ajustes.tsx` ya hace `clear()` y `router.replace('/login')` incondicionalmente después. Lo que **sí falta** (y es lo que pide M1): confirmación antes de cerrar sesión, aviso de "consulta abierta quedará en borrador", detener Dentia/grabación, y envolver en `try/finally` por robustez (hoy, si `qc.clear()` lanzara, `router.replace` no se ejecutaría). | `mobile/app/(app)/ajustes.tsx:29-34`, `mobile/src/api/endpoints.ts:42-43` |
| R6 | "Falta Cerrar consulta... no existe pantalla de nota/cierre en móvil" | **CONFIRMADA — y es más grande de lo esperado: tampoco existe en la web.** `atencion/[id].tsx` es solo dictado + propuestas; no hay nota SOAP ni botón de cierre. Además, en el backend no existe ningún endpoint que cierre un `Encounter` (`ended_at` nunca se escribe en ningún `service.py`) ni que encadene el cambio de la cita a `TERMINADA`. | `mobile/app/atencion/[id].tsx` completo; `grep ended_at` en `backend/app/modules/encounters` sin resultados de escritura |
| R7 | "Falta Generar nueva cita al terminar. Depende de R1 y R6" | **CONFIRMADA**, y depende de R1 (crear cita) tal como predice el documento. | Consecuencia directa de R1 |

---

## 4. Cambios de backend — qué hace falta realmente

| # | ¿Hace falta? | Detalle |
|---|---|---|
| **B7** (`GET/PUT /me/preferences`) | **SÍ.** No existe ningún módulo, modelo ni ruta de preferencias de usuario en el backend. Sin esto, idioma/voz/tema solo pueden vivir en el teléfono (`AsyncStorage`/memoria), lo que contradice "sincronizar entre web, tablet y teléfono" de M2. | Nuevo módulo pequeño: `backend/app/modules/preferences/` (o campos JSON en `User`), con prueba pytest. |
| **B8** (`GET /appointments/availability`) | **SÍ.** `agenda/service.py::find_free_slots` ya existe y hace el cálculo, pero **no está expuesto** en `agenda/router.py`. Es un cambio pequeño: agregar la ruta y su schema de salida, con prueba pytest (reutilizando la lógica ya probada internamente, si tiene pruebas unitarias — confirmar en `backend/tests`). | Agregar `@router.get("/appointments/availability")` que llame a `service.find_free_slots`. |
| **B9** (`POST /encounters` acepta `appointment_id` opcional) | **NO hace falta — ya existe.** `EncounterCreateRequest.appointment_id: uuid.UUID | None = None` ya está en `backend/app/modules/encounters/schemas.py`. El móvil solo necesita agregar el botón/flujo que llame a `createEncounter({patient_id, appointment_id: null})`. | Ninguno en backend. |
| **B10** (`GET /encounters/current`) | **SÍ.** No existe ningún endpoint que devuelva la atención abierta del profesional actual; es necesario para la "barra En consulta" (M4/M8) y para recuperar la consulta al reabrir la app. | Nuevo endpoint en `encounters/router.py`, con prueba pytest. Puede modelarse igual que `GET /cash-sessions/current` en `billing/router.py` (mismo patrón ya existente en el código). |
| **B11** (`POST /encounters/{id}/close`) | **SÍ, y es más necesario de lo que sugiere el documento:** hoy **ni la web ni el móvil** tienen una forma de cerrar una consulta. "Cerrar" hoy == finalizar la nota (`POST /notes/{id}/finalize`), pero eso no escribe `Encounter.ended_at` ni cambia el estado de la cita a `TERMINADA` — eso requeriría además una llamada manual a `PATCH /appointments/{id}/status`. Para dar a M6 los "mensajes de validación con `code` estable" que pide el documento, conviene un endpoint que: (1) verifique propuestas IA pendientes, alertas vigentes y procedimientos sin pieza; (2) si todo está en orden, marque `ended_at` y, si hay `appointment_id`, cambie la cita a `TERMINADA`. | Nuevo endpoint en `encounters/router.py` + lógica de validación en `service.py`, con prueba pytest. **No romper la web**: hoy la web no llama a nada parecido, así que no hay riesgo de regresión ahí — pero sí conviene ofrecerlo también a la web en un cambio posterior (fuera de alcance de este documento). |
| **B12 — nuevo, no estaba en la lista** (`POST /tooth-findings/{id}/annul` o similar) | **SÍ.** Hallazgo de esta auditoría: no existe ningún endpoint HTTP para anular/resolver un hallazgo vigente con motivo (regla 2 y regla 5 de CLAUDE.md). El único código que hace algo parecido es `odontogram/service.py::retire_finding`, usado solo internamente por el "deshacer" de voz de Dentia (`app/voice/dialogue.py`), sin pasar por `require_permission`, sin exigir motivo y sin auditar un "annul" explícito (audita como `odontogram.finding_retired`, pensado para deshacer una captura reciente, no para anular clínicamente con justificación). M5 pide "Cambiar", "Marcar como resuelto/tratado" y "Anular con motivo obligatorio" — de los tres, "Cambiar" ya funciona vía `POST /tooth-findings` normal; "Anular con motivo" y "resuelto/tratado" necesitan un endpoint nuevo. | Nuevo endpoint (p. ej. `POST /tooth-findings/{id}/annul` con `{reason}`, usando permiso `odontogram.write` y auditoría `odontogram.finding_annulled`), con prueba pytest. Recomendado antes de programar M5. |

### Resumen para decidir
- **Ya resuelto, no tocar backend:** B9.
- **Cambios de backend genuinamente necesarios antes de M2/M3/M4/M6:** B7, B8, B10, B11.
- **Cambio de backend adicional, no previsto en el documento original, necesario para M5:** B12.

---

## 5. Notas para los bloques siguientes

- **M1 (cerrar sesión):** el riesgo real no es la excepción no atrapada (ya está atrapada); es la falta de confirmación, el aviso de consulta abierta y detener Dentia/grabación antes de navegar. Bajo riesgo, sin cambios de backend.
- **M2:** no programar nada que dependa de B7 hasta tenerlo listo, o las preferencias solo vivirán en el teléfono (aceptable como fallback si el usuario prioriza velocidad sobre sincronía, pero hay que decidirlo explícitamente).
- **M3:** necesita B8 antes de poder mostrar "horarios disponibles"; sin B8, se puede lanzar una primera versión que solo permita hora manual (con el 409 del backend como red de seguridad).
- **M4:** la "atención sin cita" ya es posible hoy sin tocar backend (B9 ya existe); lo único nuevo de backend ahí es B10 para la barra "En consulta".
- **M5:** no empezar sin B12, o "Anular" tendrá que implementarse como un hack (llamar a crear un finding especial) que violaría la regla 2/5 de forma más sutil.
- **M6/M7:** dependen de B11. Como ni la web lo tiene, conviene validar con el usuario si el criterio de "Atendida" (cambiar status a `TERMINADA`) debe quedar dentro de `POST /encounters/{id}/close` (recomendado, un solo endpoint) o si se prefieren dos llamadas separadas desde el móvil.
