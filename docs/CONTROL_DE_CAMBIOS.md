# Control de cambios

Historial de versiones publicadas (`git tag` → GitHub Release → `deploy.sh`),
generado a partir de los commits reales de cada versión (`git log vX.Y.(Z-1)..vX.Y.Z`).
Complementa a `docs/FLUJO_DE_TRABAJO.md` (cómo se publica) — este documento
es el "qué se publicó y cuándo".

Al preparar una versión nueva, agrega su entrada aquí ANTES de crear el tag
(o inmediatamente después), con el mismo formato: fecha, lista de commits
incluidos (`git log <tag-anterior>..HEAD --oneline`) y una síntesis breve de
qué cambió para quien no quiera leer cada mensaje de commit.

---

## v1.0.7 — 2026-10-28

Commits: `6653f97`, `2adba0c`

- Corrige bug real al editar un usuario ("Datos de entrada inválidos"): el
  formulario permitía escribir una contraseña de 8 caracteres pero el
  backend exige 12 — se alineó el `minLength` del formulario.
- Alta de paciente pediátrico: cuando se detecta/elige tipo pediátrico, oculta
  Ocupación/Estado civil del formulario del paciente y exige al menos un
  contacto tutor (nombre + teléfono) antes de poder crear el paciente;
  agrega captura de ocupación del tutor.
- Agenda: habilita el menú "Horarios" para el perfil Recepción (antes
  gateado por error al permiso de Catálogos); nuevo odontólogo/especialista
  recibe horario "abierto" por default (lunes-sábado 08:00-20:00) al
  crearse; ya no se pueden crear/reagendar citas en un horario que ya pasó,
  y el calendario sombrea las fechas/horas pasadas.
- Corrige que 3 de las 4 historias clínicas (Odontológica, Pediátrica,
  Endodoncia) tuvieran cerrada por default la única sección con el
  selector de atención, bloqueando en silencio toda captura en esas
  pestañas; mejora de usabilidad del panel de sondeo periodontal (celda
  completa clicable, confirmación visible al guardar, no se cierra solo).

## v1.0.6 — 2026-10-28

Commits: `20a84fe`

- Menú "Control de versiones" (solo superadmin/admin_clinica): expone la
  versión desplegada de punta a punta y enlaza al historial de releases de
  GitHub.
- Fase D del rediseño del expediente clínico, integrada como "Otros
  formatos clínicos" dentro de la pestaña Consentimientos: receta (2
  copias por hoja con folio consecutivo), referencia/interconsulta,
  contrarreferencia, nota de evolución (campos nuevos en `ClinicalNote`) y
  ficha de registro de tratamientos realizados, todas con PDF.
- Fase G (periodontograma completo), último slice del rediseño: sondeo de
  6 sitios por pieza con nivel de inserción clínica calculado, movilidad y
  furcación, índices de placa dentobacteriana y gingival calculados,
  tablas de oclusión, con PDF — integrado dentro de Historia Clínica
  Odontológica.

## v1.0.5 — 2026-10-27

Commits: `cfc6d6b`, `3db2240`

- Rediseño del expediente clínico según los formatos oficiales de la
  clínica (Fases A-F): Historia Clínica General, Odontológica, Pediátrica
  y de Endodoncia, cada una con sus propios campos y PDF; módulo "Formatos
  de documentos" (2 logos, lugar, título institucional) reutilizado por
  todos los PDF del sistema; odontograma con figura anatómica nueva
  (corona+raíz) y paleta de colores reconciliada con la leyenda oficial.
- Corrige 2 fallos reales que el pipeline de CI detectó tras el commit
  anterior: contraste de color insuficiente (WCAG AA) en el badge "Faltan
  datos", y una sección de Historia Clínica General que el E2E esperaba
  abierta por default y quedó cerrada por error.

## v1.0.4 — 2026-10-25

Commits: `3c6a784`, `817e093`

- Cuenta de demostración de tiempo limitado; edición y borrado de usuarios
  y pacientes.
- Usuarios: correo de acceso editable y foto de perfil; corrige un error
  silencioso al subir la foto de un paciente.

## v1.0.3 — 2026-10-24

Commits: `e23f344`, `44ab878`, `1d9dfbb`, `d8116be`, `9f2cabb`, `3393fee`,
`bf47b5a`, `9f1c26d`, `14d9c59`, `2107f93`

- Horarios abiertos por default, título/logo de la clínica configurables,
  menú de Ayuda, paciente de ejemplo.
- Firma y PDF de consentimientos corregidos; profesional expuesto en
  tratamientos; historial de citas del paciente.
- Cédula profesional del odontólogo; normaliza el logo en todos los PDF.
- Corrige el E2E de consentimientos y agrega `aria-label` a selects sin
  nombre.
- Documentación operativa del VPS (guía de flujo de trabajo, usuarios y
  accesos, pendientes, hallazgo de `PasswordAuthentication`).

## v1.0.2 — 2026-10-24

Commits: `1d324c7`

- El rol odontólogo gana el permiso `patients.write`.

## v1.0.1 — 2026-10-24

Commits: `ec7fb7c`, `153fe70`, `885c56f`, `e98d42e`, `250b071`, `e2e4aff`,
`b076695`, `b4a3220`

- Correcciones del primer despliegue real al VPS: `deploy.sh` no aborta si
  falla el login a GHCR y omite el respaldo en el primer despliegue;
  permisos de secretos (644); sintaxis del Caddyfile; `VITE_API_URL` roto
  en `ci-build-push.sh` (el login nunca funcionaba); pasos de CI que
  necesitaban la base de datos arriba.

## v1.0.0 — 2026-10-24

Primera versión publicada del pipeline de release (imágenes firmadas,
SBOM, paquete VPS). Incluye las correcciones de arranque del propio
pipeline: orden de siembra en `app/seed.py`, usuarios demo sembrados antes
de E2E, `pip` actualizado antes de instalar dependencias, `ruff`/`pip-audit`
corregidos, migración base de permisos reparada para una base de datos
nueva.

---

## Nota sobre el módulo de voz/IA

`app/voice`/`app/ai` (asistente de voz local con Ollama/Whisper) existe en
el código y tiene su propia suite de pruebas, pero está **deshabilitado en
producción** (`AI_ENABLED: "false"` en `deploy/vps/compose/docker-compose.yml`)
— es un módulo pendiente, no una funcionalidad que los usuarios reales
tengan disponible todavía. Un fallo ahí no debería, por sí solo, bloquear
una versión que no toca ese módulo; úsese criterio (y este documento como
registro) en vez de tratarlo automáticamente como igual de crítico que un
módulo sí habilitado.
