# Instrucciones para Claude Code — Correcciones (Fase 12.1), mejoras de administración y Fase 13 "Dentia"

> Proyecto: `C:\workspace\dentia-system`
> Documentos de referencia: `docs/02_ARQUITECTURA.md`, `docs/03_AGENTE_IA_VOZ.md`,
> `docs/05_ASISTENTE_DENTIA_VOZ_CONVERSACIONAL.md` (diseño completo de Dentia), `CLAUDE.md`.
> Orden obligatorio: **Parte A → Parte B → Parte C**. No empezar la Fase 13 con errores de la
> Parte A abiertos: Dentia usa la agenda, el expediente y los consentimientos, y heredaría sus fallas.

---

## 0. Reglas de trabajo para cada punto

1. **Reproducir primero.** Antes de corregir, reproducir el fallo (en el navegador o con una prueba)
   y anotar la causa real encontrada. Las "causas probables" de este documento son hipótesis
   a verificar, no hechos.
2. **Prueba que falla → corrección → prueba que pasa.** Cada error corregido deja una prueba de
   integración (backend) o E2E (Playwright) que lo cubra, para que no regrese.
3. **Corregir la causa raíz**, no el síntoma en una sola pantalla (mismo criterio que los
   "bugs de raíz" de las Fases 4, 7 y 8).
4. **Migraciones incrementales** de Alembic. No recrear catálogos ni tablas existentes. Revisar que
   el autogenerate no proponga borrar índices/constraints escritos a mano (`immutable_unaccent`,
   `ux_tooth_findings_current`, restricciones `EXCLUDE` de agenda).
5. **Respetar las reglas de `CLAUDE.md`**: anular en vez de borrar, eventos en vez de sobrescribir,
   colores solo por variables de tema, permisos con `require_permission`, auditoría.
6. Al terminar cada punto: `pytest`, `mypy`, lint, `npm run build` y los E2E existentes en verde.
7. Actualizar documentación al cerrar cada parte: `docs/02_ARQUITECTURA.md` (nueva sección 5.13+ y
   tabla de estado), `docs/MANUAL_USUARIO.md`, `docs/MATRIZ_PERMISOS.md` y
   `docs/PENDIENTES_CLINICOS.md`.
8. Al final de cada parte, entregar un resumen: qué se encontró, qué se cambió, qué queda pendiente.

---

## Parte A — Correcciones de errores detectados (Fase 12.1)

### A1. Los odontólogos/especialistas nuevos no aparecen en la agenda
*(Reportado dos veces: "usuarios nuevos no aparecen para elegir" y "no aparecen todos los odontólogos ya siendo usuarios".)*

- **Causa probable:** en la Fase 6 `Provider` es una entidad separada de `User`. Crear un usuario
  con rol `odontologo`/`especialista` no crea su `Provider`, y la agenda solo lista `Provider`.
  Los odontólogos del *seed* sí lo tienen; los creados desde la pantalla de usuarios, no.
  Verificar también si la agenda filtra por sucursal (`X-Clinic-Id`) y el usuario no tiene
  `UserClinic` en esa sucursal, o si filtra `is_active`.
- **Corrección:**
  - Al crear un usuario, o al asignarle un rol clínico en una sucursal, crear automáticamente su
    `Provider` en esa sucursal (servicio de `iam` llama a `agenda_service.ensure_provider`),
    con un color por defecto tomado de una paleta rotativa.
  - Al quitar el rol o desactivar al usuario, desactivar su `Provider` (no borrarlo: tiene citas).
  - **Migración de datos** que cree el `Provider` faltante para todos los usuarios clínicos
    existentes.
  - En Agenda, el selector de profesional muestra todos los `Provider` activos de la sucursal.
- **Aceptación:** crear un odontólogo nuevo → aparece inmediatamente en el selector y en la vista
  agrupada por profesional de la agenda, sin pasos manuales. Prueba de integración y E2E.

### A2. La búsqueda de pacientes no funciona bien
- **Revisar, en este orden:**
  1. Que el índice GIN trigram y la función `immutable_unaccent` existan en la base real
     (una migración posterior pudo haberlos borrado por autogenerate — ver regla 4).
  2. Que la consulta use `word_similarity`/`%>` (coincidencia parcial dentro del nombre completo)
     y no solo `similarity` sobre el nombre entero: con `similarity`, buscar "perez" no encuentra
     "Juan Carlos Pérez López" porque la cadena completa es muy distinta.
  3. Que el umbral no sea demasiado alto para búsquedas cortas.
  4. Que también busque por **número de expediente**, **teléfono** (solo dígitos) y
     **apellidos en cualquier orden**.
  5. En el frontend: *debounce* (~250 ms), mínimo 2 caracteres, que no se descarten respuestas
     viejas que llegan tarde (usar la última petición, `AbortController`).
- **Corrección esperada:** búsqueda combinada:
  - coincidencia exacta de expediente o teléfono primero;
  - después, `ILIKE` sin acentos por prefijo de cada palabra;
  - al final, similitud trigram ordenada por `word_similarity`.
  - Resultados con nombre, edad, expediente y última visita.
- **Aceptación:** prueba parametrizada con al menos estos casos sobre datos del seed: "perez",
  "Pérez", "PEREZ LOPEZ", "lopez perez", "jua per", "000012", teléfono con y sin guiones, un
  nombre con error de una letra ("Peres").

### A3. "Selecciona una atención" aparece vacío en todo el expediente
- **Causa probable:** cada sección del expediente exige `encounter_id` (regla 6) y el selector
  lista atenciones del paciente. Está vacío cuando el paciente no tiene atenciones, cuando el
  filtro solo trae atenciones "abiertas", o cuando la petición falla sin mostrar error.
- **Corrección:**
  - El selector lista las atenciones del paciente (más reciente primero, con fecha y profesional).
  - **Si hay una atención del día en curso, se preselecciona.**
  - Si no hay ninguna, el selector muestra la opción **"+ Iniciar atención nueva"**, que la crea
    ahí mismo (con permiso `records.write`) y la deja seleccionada. Así nunca queda vacío ni
    bloqueado.
  - Si la petición falla, mostrar el error; nunca un selector vacío en silencio.
- **Aceptación:** en un paciente sin atenciones se puede registrar una alergia en 2 clics.

### A4. Los botones de "Agregar" no funcionan
- **Causa probable:** muy probablemente ligado a A3 (el formulario no envía sin `encounter_id` y
  no avisa). Revisar además la consola del navegador y la respuesta del backend: 403 por permisos,
  422 por validación no mostrada, o un `onClick` sin `type="button"`/`submit` correcto.
- **Corrección:** inventariar **todos** los botones "Agregar" de la aplicación (antecedentes,
  alergias, medicamentos, signos vitales, diagnósticos, contactos, fases e ítems del plan,
  procedimientos, imágenes, pagos, usuarios, profesionales, gabinetes). Cada uno debe:
  - funcionar;
  - mostrar el error del backend (mensaje claro en español) si falla;
  - estar deshabilitado **con tooltip explicando por qué** si falta algo, por ejemplo
    "Selecciona o inicia una atención".
- **Aceptación:** un E2E que recorra cada "Agregar" del expediente y del plan de tratamiento.
  Entregar la tabla del inventario con el estado antes y después.

### A5. "Firmar y generar PDF" no funciona
- **Revisar:**
  1. respuesta del endpoint `POST /patients/{id}/consents` (código y mensaje);
  2. que el `SignaturePad` realmente envíe el PNG en base64 (no vacío, con o sin prefijo
     `data:image/png;base64,` según lo que espere el backend);
  3. errores de `xhtml2pdf` en Windows (fuentes, rutas con `\`, imágenes referenciadas en el HTML
     como rutas relativas o URLs que no puede resolver, incluida la firma y el logo);
  4. permisos de escritura en `storage/`;
  5. tamaño máximo del cuerpo de la petición.
- **Corrección:**
  - incrustar firma y logo como `data:` URI en el HTML antes de pasarlo a `xhtml2pdf`;
  - capturar el error de render y devolver un mensaje entendible;
  - el botón "Firmar" queda deshabilitado mientras el lienzo esté vacío.
- **Aceptación:** firmar un consentimiento genera el PDF, se descarga y se ve con firma, datos del
  paciente y logo. Prueba de integración que valide que el PDF existe, no está vacío y su SHA-256
  coincide con `content_hash`.

### A6. Las plantillas de consentimiento no funcionan
- **Revisar:** crear, editar (nueva versión, regla 7), listar y elegir plantilla al firmar.
  Verificar si simplemente no hay plantillas sembradas, por lo que el selector queda vacío.
- **Corrección:**
  - Sembrar plantillas **de ejemplo**, marcadas "Ejemplo — validar con la clínica": consentimiento
    general, extracción, endodoncia, cirugía/implante y blanqueamiento.
  - El editor muestra las variables disponibles (`{{paciente.nombre}}`, etc.) como botones que se
    insertan, y una **vista previa** con datos del paciente actual.
  - Registrar en `PENDIENTES_CLINICOS.md` que el texto legal debe validarlo la clínica.
- **Aceptación:** el administrador crea una plantilla, la edita (queda versión 2 y la 1 en el
  historial), y el odontólogo la elige y firma con ella.

### A7. Logo de la clínica arriba a la izquierda
- Mostrar el logo de `GET /branding/logo` en el extremo superior izquierdo, en el encabezado o
  en la parte superior de la barra lateral, visible en todas las pantallas.
- Alto máximo ~40 px, proporción respetada. Clic → página de inicio.
- Sin logo, mostrar el nombre de la clínica. Debe verse bien en modo oscuro y en móvil.

---

## Parte B — Mejoras funcionales de administración (Fase 12.2)

### B1. Módulo de administración de catálogos
Hoy varios catálogos están fijos en código (`rules.py`, `finding_catalog.py`,
`APPOINTMENT_TYPES`...) y solo `ProcedureCatalog` vive en la base. El administrador debe poder
mantenerlos sin desplegar código.

- **Nueva pantalla "Configuración → Catálogos"** (permiso nuevo `catalogs.manage`, solo
  `admin_clinica`; `superadmin` sin acceso a datos clínicos se mantiene).
- **Catálogos a administrar:**

| Catálogo | Hoy vive en | Campos editables |
|---|---|---|
| Tipos de consulta/cita | `agenda/rules.py` `APPOINTMENT_TYPES` | nombre, duración por defecto, color, activo |
| Procedimientos y precios | BD (`procedure_catalog`) | ya existe: integrarlo en la misma pantalla |
| Hallazgos del odontograma | `odontogram/finding_catalog.py` | nombre, símbolo, color (de una paleta de variables de tema), si requiere superficie, activo |
| Diagnósticos | catálogo de `diagnosis` | código, nombre, activo |
| Categorías de antecedentes | `records/rules.py` | nombre, activo |
| Palabras clave de alertas | `CONDITION_ALERT_KEYWORDS`, `MEDICATION_ALERT_KEYWORDS` | palabra, etiqueta de alerta |
| Gabinetes | `agenda` `Resource` | nombre, sucursal, activo |
| Sucursales | `iam` `Clinic` | nombre, dirección, teléfono (solo `admin_clinica` de la organización) |
| Métodos de pago | `billing` | nombre, activo |

- **Diseño:**
  - mover cada catálogo fijo a una tabla por sucursal, con `is_active` (nunca borrar un elemento
    usado: se desactiva);
  - una migración de datos que siembre lo que hoy está en código;
  - un servicio de lectura con caché simple que reemplace las constantes, de modo que el resto del
    código cambie lo mínimo.
  - Los códigos internos (`CARIES`, `RESINA`...) no se editan, porque los usan la IA y los
    reportes; el nombre visible sí.
- **Pantalla:** una pestaña por catálogo, tabla con búsqueda, alta, edición en línea y
  activar/desactivar, con importar/exportar CSV.
- **Dentia:** el prompt, la gramática rápida y los catálogos de validación de la IA deben leer de
  estas tablas. Así, un procedimiento nuevo dado de alta por el administrador se puede dictar sin
  tocar código.
- **Aceptación:** el administrador crea el tipo de consulta "Valoración ortodoncia — 45 min" y
  aparece de inmediato al agendar. Desactivar un hallazgo lo oculta del menú rápido, pero los
  registros históricos lo siguen mostrando.

### B2. Alta de usuario: sucursal y gabinete
- El formulario de nuevo usuario/edición permite elegir **una o varias sucursales** (`UserClinic`)
  y, por sucursal, el **gabinete predeterminado** (nuevo campo `Provider.default_resource_id`,
  opcional).
- Al guardar se crea su `Provider` en cada sucursal (ver A1).
- La agenda usa ese gabinete por defecto al agendar con ese profesional (se puede cambiar).
- **Aceptación:** crear un odontólogo en las sucursales Centro y Norte, con gabinete 2 en Centro;
  aparece en ambas agendas y al agendarle en Centro se preselecciona el gabinete 2.

### B3. Alta de paciente: sucursal, gabinete y profesional
- Nuevos campos en `Patient`:
  - `clinic_id`: ya existe, se toma de la sucursal activa; mostrarlo y permitir elegir otra
    sucursal si el usuario tiene acceso a varias;
  - `default_resource_id` (gabinete, opcional);
  - `primary_provider_id` (odontólogo o especialista tratante, **opcional**).
- Se muestran en el paso 1 del alta y en el Resumen, y se pueden editar con motivo (edición
  controlada).
- Al agendar a ese paciente, profesional y gabinete se preseleccionan con estos datos.
- Filtro "Mis pacientes" en la lista para el odontólogo.
- **Aceptación:** paciente nuevo con profesional asignado → al agendarle, profesional y gabinete
  ya vienen elegidos.

---

## Parte C — Fase 13: asistente de voz "Dentia"

Diseño completo en `docs/05_ASISTENTE_DENTIA_VOZ_CONVERSACIONAL.md`. Esta sección fija las
**decisiones ya tomadas** y el plan de implementación.

### C0. Decisiones confirmadas por el usuario
- **Nombre y activación:** "Dentia". Escucha pasiva desde el inicio de sesión. Voz femenina
  (Piper `es_MX-claude-high`, respaldo: voz del sistema).
- **Confirmación implícita de 3 segundos** para capturas (nivel 2). Dentia repite lo que va a
  hacer, muestra la tarjeta con cuenta regresiva de 3 s y aplica si no se dice "no/cancela".
  Nivel 3 (iniciar consulta, alergias, diagnósticos, procedimientos, citas) sigue pidiendo "sí"
  explícito. Se mantiene configurable, con 3 s como valor por defecto.
- **Recepción también usa Dentia**, limitada a agenda y pacientes (ver C2).
- **Vocabulario odontológico** a partir de `docs/diccionario_odontologico_2023.pdf` (ver C3).

### C1. Permisos de voz por rol
| Rol | Permiso | Intenciones disponibles |
|---|---|---|
| odontólogo, especialista | `voice.use` + `voice.clinical` | todas (sec. 4 del doc 05) |
| recepción | `voice.use` | agenda y pacientes (C2) |
| caja, admin_clinica, superadmin | — (activable después) | — |

- El registro de intenciones declara qué permiso exige cada una.
- El gestor de diálogo **solo ofrece al modelo las intenciones permitidas** para el usuario y la
  pantalla actual.
- El ejecutor vuelve a verificar con `require_permission`. Dentia nunca puede hacer algo que el
  usuario no pueda hacer a mano.

### C2. Dentia para recepción (agenda por voz)
- **Intenciones:**

| Intención | Ejemplo | Nivel |
|---|---|---|
| `buscar_paciente` / `abrir_ficha` | "Dentia, busca a María López" | 1 |
| `citas_hoy` / `agenda_de` | "¿qué citas tiene la doctora Ruiz mañana?" | 0 |
| `huecos_libres` | "¿cuándo hay espacio con el doctor Gómez esta semana?" | 0 |
| `agendar_cita` | "agenda a María López el jueves a las 11 con la doctora Ruiz, limpieza" | 3 |
| `reprogramar_cita` | "mueve la cita de María López al viernes a la misma hora" | 3 |
| `confirmar_cita` | "confirma la cita de las 10" | 2 |
| `registrar_llegada` | "llegó María López" → EN_SALA | 2 |
| `cancelar_cita` / `no_show` | "cancela la cita de las 12, motivo: enfermedad" (pide motivo si falta) | 3 |
| `lista_espera` | "agrégala a la lista de espera" | 2 |
| `alta_rapida_paciente` | "registra paciente nuevo Pedro Sánchez, teléfono…" → abre el formulario prellenado; el alta se termina en pantalla (detección de duplicados obligatoria) | 1 |

- Si falta algún dato, Dentia propone horarios libres reales ("El jueves la doctora Ruiz tiene
  libre 10:00 y 12:30, ¿cuál?") respetando traslapes, horario laboral y el gabinete
  predeterminado (B2/B3).
- **Particularidad de recepción:** hay mostrador, teléfono y pacientes que pueden decir "Dentia"
  si es también el nombre de la clínica. Por eso, para recepción:
  - modo de activación por defecto: **tecla/pedal + palabra**, configurable;
  - sensibilidad de la palabra más baja que en el consultorio;
  - la verificación con Whisper de que la frase empieza con "Dentia" es obligatoria.

### C3. Vocabulario odontológico desde `docs/diccionario_odontologico_2023.pdf`
- **Script** `python -m app.ai.vocab.build --source docs/diccionario_odontologico_2023.pdf` que:
  1. extrae los términos (entradas del diccionario) con `pypdf`/`pdfplumber` y, si el PDF es
     escaneado, avisa en vez de inventar;
  2. normaliza (minúsculas, sin duplicados, conserva acentos);
  3. genera `backend/app/ai/vocab/terminos_dentales.txt` (un término por línea) y un JSON con
     término → categoría cuando el diccionario la indique.
- **Usos del vocabulario:**
  - **Whisper:** `initial_prompt` tiene un límite (~224 tokens), así que no se pasa el
    diccionario completo. Se arma por contexto: términos de la pantalla actual, nombres de los
    catálogos activos (B1) y pacientes del día. Además se usa el parámetro `hotwords` de
    faster-whisper con los más frecuentes.
  - **Corrección posterior:** comparar con `rapidfuzz` las palabras de la transcripción que no
    estén en el diccionario general contra `terminos_dentales.txt` y corregir solo con alta
    similitud. Ejemplo: "pulpitis reversibe" → "pulpitis reversible".
  - **LLM:** glosario breve de términos relevantes a la intención detectada, no la lista completa.
- **Derechos:** el PDF es material de terceros. Usarlo solo internamente como fuente de
  vocabulario. Si el repositorio es público o se comparte, agregar el PDF a `.gitignore` y
  versionar solo la lista de términos generada (o confirmar la licencia del diccionario).
- **Aceptación:** `eval` de voz con 30 frases que contienen términos técnicos del diccionario, con
  mejora medible de aciertos con vocabulario frente a sin vocabulario.

### C4. Plan de implementación 13.1 – 13.6
(Detalle técnico en el doc 05, secciones 5 a 8.)

| Etapa | Alcance | Criterio de aceptación |
|---|---|---|
| **13.1 Base de voz** | WebSocket `/api/v1/voice/ws` con JWT + `X-Clinic-Id`; `AudioWorklet` 16 kHz; `VoiceProvider` global montado tras el login (micrófono solicitado en el mismo clic de "Iniciar sesión"); orbe con estados; VAD; detector etapa 1 (VAD + Whisper `tiny`, frase que **empieza** con "Dentia"); Piper con caché de frases; silenciar (clic en el orbe, `Alt+M`, "Dentia, silencio"); una sola pestaña con micrófono (`BroadcastChannel`); HTTPS en red local documentado en `MANUAL_TECNICO.md` | Decir "Dentia" enciende el orbe en < 400 ms y responde con voz femenina; sin HTTPS se muestra un aviso claro |
| **13.2 Navegación** | Registro declarativo de intenciones con permisos por rol (C1); ruta rápida sin LLM; `abrir_expediente` con desambiguación usando la búsqueda corregida (A2); `ir_a`, `leer_alertas`, `citas_hoy`, `ayuda`, `repetir`; `ScreenContext` + `UiActionBus` (navegar, resaltar pieza/campo) | "Dentia, abre el expediente de Juan Pérez" funciona, incluso con dos homónimos |
| **13.3 Captura en consulta** | `iniciar_consulta` (usa la cita del día o crea la atención, coherente con A3); odontograma, signos, motivo, nota, alergia, medicamento; niveles 2 (**implícito 3 s**) y 3 (explícito); ventana de seguimiento de 8 s; "cancela"; "deshaz" con `odontogram_service.retire_finding` nuevo; ejecución vía `AiSuggestion` + `applier.py` con `confirmation_mode` en la auditoría | 20 hallazgos seguidos en el odontograma sin teclado; "cancela" y "deshaz" funcionan |
| **13.4 Diagnóstico, plan y agenda** | Diagnóstico, procedimientos planeados/realizados (leyendo el catálogo de B1); **todas las intenciones de recepción (C2)**; propuesta de huecos libres con profesional/gabinete predeterminados (B2/B3) | Recepción agenda, confirma, registra llegada y reprograma por voz sin traslapes |
| **13.5 Ruta LLM y dictado** | Ollama con esquema solo de las intenciones permitidas para la pantalla y el rol, `keep_alive=-1`, aviso "Un momento…" si tarda > 2 s; `modo_dictado` integrado con el panel de propuestas de la Fase 8; vocabulario contextual (C3) | Frases libres resueltas en < 4 s en el equipo de la clínica |
| **13.6 Afinación** | Corpus `tests/voice/commands.jsonl` (≥ 150 frases clínicas + ≥ 60 de recepción); `python -m app.voice.eval`; pruebas con audio con ruido de consultorio y de mostrador; script de vocabulario (C3); entrenamiento del modelo propio "Dentia" (etapa 2, openWakeWord/livekit-wakeword); `VOICE_FAKE_MODE` para E2E | Activación ≥ 95 %; < 1 falsa activación por hora; intención correcta ≥ 90 % en la ruta rápida |

### C5. Reglas que no cambian
- La IA no finaliza ni firma notas, no cobra, no borra, no receta y no cambia la identidad del
  paciente. Responde "Eso lo tienes que hacer tú" y abre la pantalla correspondiente.
- El audio no se guarda. Solo se registra el texto de las órdenes dirigidas a Dentia
  (`VoiceCommandLog`).
- Todo cambio hecho por voz lleva `origin="AI_ASSISTED"` y su `AuditEvent` con el modo de
  confirmación.

---

## Entregables finales
1. Partes A, B y C implementadas, con pruebas y en verde.
2. `docs/02_ARQUITECTURA.md` actualizado: secciones 5.13 (Correcciones 12.1), 5.14 (Catálogos y
   administración 12.2) y 5.15 (Dentia 13), y tabla de estado.
3. `docs/MANUAL_USUARIO.md`: cómo usar Dentia (odontólogo y recepción), tarjeta imprimible
   "¿Qué puedo decir?" y administración de catálogos.
4. `docs/MATRIZ_PERMISOS.md`: `catalogs.manage`, `voice.use`, `voice.clinical`.
5. `docs/PENDIENTES_CLINICOS.md`: textos legales de consentimientos, hallazgos que requieren
   superficie, nombres coloquiales de procedimientos ↔ catálogo y licencia del diccionario.
