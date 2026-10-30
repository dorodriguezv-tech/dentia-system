# Control de cambios

Historial de versiones publicadas (`git tag` → GitHub Release → `deploy.sh`),
generado a partir de los commits reales de cada versión (`git log vX.Y.(Z-1)..vX.Y.Z`).
Complementa a `docs/FLUJO_DE_TRABAJO.md` (cómo se publica) — este documento
es el "qué se publicó y cuándo".

## Instrucciones para Claude Code

Al preparar una versión nueva, agrega su entrada aquí ANTES de crear el tag
(o inmediatamente después, si el tag ya se creó) — nunca dejarlo pendiente
hasta que alguien pregunte qué llevó esa versión. Formato exacto, igual al
de las entradas existentes:

1. Encabezado `## vX.Y.Z — AAAA-MM-DD` con la fecha real de publicación (la
   del commit/tag, no necesariamente "hoy" si la entrada se agrega después).
2. Línea `Commits: ` con los hashes cortos de
   `git log <tag-anterior>..HEAD --oneline`, **excluyendo** el propio commit
   que agrega esta entrada (es autorreferencial, no cambia nada del
   sistema).
3. Lista con viñetas, en español de México, agrupando por tema (no un punto
   por commit): describe el efecto para quien usa o despliega el sistema,
   no el mensaje de commit literal.
4. Insertar la entrada nueva arriba de la anterior (orden descendente,
   la más reciente primero) — nunca reescribir ni reordenar entradas de
   versiones ya publicadas; una corrección a una entrada vieja es un ajuste
   puntual de esa entrada, no una reescritura de historia.
5. Antes de dar por terminada la entrada, confirma que sus commits
   coinciden con `git log <tag-anterior>..<tag-nuevo> --oneline` (menos el
   de esta misma edición) — es la verificación que detecta una entrada
   incompleta o un tag movido por error.

## Instrucciones para el usuario

Lee este documento cuando necesites saber **qué cambió y cuándo** en una
versión ya publicada, o para decidir si vale la pena actualizar el
servidor. No es la guía para publicar ni desplegar — eso es
`docs/FLUJO_DE_TRABAJO.md` (secciones 4 y 5) y
`deploy/vps/INSTALACION_VPS.md` (sección 7); aquí solo se registra el
resultado.

- Para pedir que se agregue la entrada de la versión más reciente, basta
  decir "actualiza el control de cambios" — o Claude Code la agrega por su
  cuenta al preparar un release (ver instrucciones de arriba).
- Las versiones están en orden descendente: la más reciente arriba.
- La "Nota sobre el módulo de voz/IA" al final no es una versión — es un
  recordatorio permanente de que ese módulo existe en el código pero sigue
  deshabilitado en producción.

---

## v1.0.8 — 2026-10-29

Commits: `e18ad84`, `5a877c0`, `1ee808d`, `e246838`, `1aa2967`

- Integra al módulo de Formatos (antes "Consentimientos") los 24 formatos
  oficiales reales de `docs/formatos/` (consentimientos informados, aviso de
  privacidad y cartas, incluida la de notificación de caso médico legal),
  reemplazando las 4 plantillas de ejemplo. Prellena automáticamente los
  datos ya conocidos del expediente (paciente, tutor, profesional, hora de
  la atención) y solo pide los campos libres que cada formato puntual
  necesita (tipo de prótesis, motivo de suspensión, etc.).
- Rediseña el menú "Formatos" del expediente (antes "Consentimientos"): ya
  no hay un submenú aparte para firmar — "Plantillas" despliega el
  documento elegido ya resuelto (encabezado, logos, título, datos
  conocidos) con los campos faltantes señalados para completarlos antes de
  firmar e imprimir el PDF; la opción de anular sigue disponible debajo de
  cada formato. Las categorías con más de 5 formatos se listan en un
  selector alfabético en vez de saturar la pantalla, y corrige que el
  listado de plantillas mostrara el nombre repetido y el número de versión.
- Reorganiza las instrucciones de este documento, separando las dirigidas a
  Claude Code de las dirigidas al usuario.
- Corrige la prueba E2E `full-flow.spec.ts`, que todavía buscaba el menú
  "Consentimientos" viejo (y luego una ambigüedad de texto al elegir el
  formato) e hacía fallar el pipeline de release — sin efecto en el sistema
  desplegado, solo en la verificación automática.

## v1.0.7 — 2026-10-28

Commits: `6653f97`, `2adba0c`, `849fc2e`, `1248e33`, `470e927`, `1cc38d9`, `f3232d5`, `ac16aa4`,
`e83c115`

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
- Corrige fixtures de pruebas de voz dependientes de la hora real (no era
  un bug de la validación nueva de "no citas en el pasado", solo exponía
  fragilidad preexistente de los tests); agrega `docs/CONTROL_DE_CAMBIOS.md`
  (este documento) y `scripts/verify-changed.ps1` (verificación rápida
  acotada a lo que cambió desde el último release).
- Corrige contraste insuficiente (WCAG AA) en el encabezado de fechas
  pasadas del calendario de Agenda, detectado por el chequeo de
  accesibilidad del pipeline.
- Corrige una CVE CRITICAL (`brotli-libs`) detectada por el escaneo de
  seguridad de la imagen del frontend.
- Corrige otro caso de la misma fragilidad horaria de pruebas de voz: una
  cita de prueba calculada cerca de la medianoche en hora de la clínica
  (22:00-24:00, que coincide con la ventana en que corre el pipeline) podía
  quedar registrada para "mañana" según la zona horaria de la clínica,
  aunque la hora dicha coincidiera — la prueba nunca encontraba la cita al
  intentar cancelarla.

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
