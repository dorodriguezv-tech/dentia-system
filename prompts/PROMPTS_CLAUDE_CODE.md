# Prompts para Claude Code (copiar y pegar en orden)

**Uso:** abre la carpeta del proyecto en VS Code, abre una terminal y ejecuta `claude`. Pega un prompt a la vez. Al terminar cada fase, revisa el resultado, ejecuta las pruebas y haz commit antes de pasar a la siguiente.

> Consejo: empieza cada fase con `/clear` para iniciar con contexto limpio. CLAUDE.md se carga automáticamente.

---

## FASE 0 — Base del proyecto
```
Lee CLAUDE.md y todos los archivos de docs/. Después crea la base del proyecto:

1. Estructura de carpetas exactamente como en CLAUDE.md sección 3.
2. backend/: FastAPI con app/main.py, core/config.py (pydantic-settings leyendo .env),
   core/db.py (SQLAlchemy 2 async + asyncpg), Alembic configurado para async,
   core/errors.py (formato {code,message,details}), endpoint GET /api/v1/health.
   requirements.txt con versiones fijadas. ruff, black y mypy configurados en pyproject.toml.
3. frontend/: Vite + React 18 + TypeScript strict, React Router, TanStack Query, Zustand,
   eslint + prettier, cliente API en src/api/ con baseURL desde VITE_API_URL,
   layout base con barra lateral, encabezado y área de contenido.
4. docker-compose.yml con PostgreSQL 16 (volumen persistente) y .env.example completo
   (incluye las variables de IA de docs/03_AGENTE_IA_VOZ.md).
5. .vscode/: launch.json (depurar FastAPI con uvicorn y Chrome contra Vite),
   settings.json (formatOnSave, intérprete .venv), extensions.json recomendadas
   (Python, Pylance, Ruff, ESLint, Prettier, PostgreSQL).
6. .gitignore (incluye .env, storage/, .venv, node_modules).
7. README.md con instalación en Windows y Linux, con y sin Docker.
8. docs/adr/ADR-001-ruta-b-stack.md con la decisión de docs/01.

Verifica: el backend arranca, /api/v1/health responde, el frontend muestra el layout y
pytest y npm run test pasan (aunque haya pocas pruebas). Inicializa git y haz el primer commit.
```

## FASE 1 — IAM, sucursales y auditoría
```
Implementa el módulo iam y el módulo audit como vertical slice completo:
- Modelos: Organization, Clinic, User, Role, Permission, UserClinic. Seeds de roles y
  permisos de CLAUDE.md sección 5 (matriz en docs/MATRIZ_PERMISOS.md).
- Login con JWT (acceso 15 min, refresh 8 h, rotación), Argon2id, rate limiting en el login,
  MFA TOTP opcional por usuario y obligatoria para admin_clinica.
- Dependencias require_permission("modulo.accion") y ABAC por clinic_id.
- AuditEvent append-only (trigger en PostgreSQL que bloquee UPDATE y DELETE) y un servicio
  audit.log(). Middleware que registra los accesos denegados.
- Frontend: pantalla de login (con logo y colores de tema), selección de sucursal,
  gestión de usuarios para admin, guardia de rutas por permiso.
- Pruebas: login, refresh, MFA, permiso denegado, inmutabilidad de AuditEvent.
- Script app/seed.py con un admin y un odontólogo de prueba (datos ficticios).
```

## FASE 2 — Tema y marca configurables
```
Implementa docs/04_TEMAS_Y_MARCA.md completo:
- Módulo branding: tabla clinic_branding, GET /api/v1/branding (público, para el login),
  PUT /branding y POST /branding/logo (admin). Valida tipo y tamaño, sanitiza SVG
  (sin scripts ni eventos) y genera el favicon.
- Frontend: theme/tokens.css, ThemeProvider, los 6 presets, derivación automática de
  hover/soft, validación de contraste WCAG con advertencia y ajuste sugerido.
- Pantalla Configuración → Apariencia con selector de preset, selectores de color,
  carga de logo, vista previa en vivo (botón, tarjeta, alerta, barra lateral) y restablecer.
- Revisa que ningún componente tenga colores fijos (agrega una regla de lint o un script
  que busque # hex fuera de theme/).
- Pruebas: cambio de preset, logo inválido rechazado, cálculo de contraste.
```

## FASE 3 — Pacientes
```
Implementa el módulo patients:
- Alta, edición controlada, estados (activo, inactivo, referido, fallecido, bloqueado).
- Contactos, tutor o responsable y contacto de emergencia.
- Búsqueda tolerante a errores (extensiones pg_trgm y unaccent) por nombre, teléfono,
  correo, fecha de nacimiento y número de expediente.
- Detección de duplicados antes de crear (similitud de nombre + fecha de nacimiento o teléfono),
  con una pantalla que muestre los posibles duplicados y obligue a confirmar.
- Lectura de ficha auditada.
- Frontend: búsqueda global en el encabezado (Ctrl+K), listado y alta en varios pasos,
  y ficha con el ENCABEZADO PERSISTENTE del paciente (nombre, edad, foto opcional,
  barra de alertas vacía por ahora).
- Seed con 50 pacientes ficticios (Faker es_MX).
```

## FASE 4 — Expediente, atención y notas
```
Implementa los módulos records y encounters según docs/02 y las reglas 1, 2, 6 y 8 de CLAUDE.md:
- Antecedentes heredofamiliares, personales patológicos y no patológicos, odontológicos,
  alergias (con severidad), medicamentos actuales, hábitos y factores de riesgo, signos vitales.
- ClinicalAlert derivada (alergias, anticoagulantes, diabetes, embarazo, etc., catálogo
  configurable) que se muestra en la barra de alertas del encabezado.
- Encounter (atención) ligado a paciente, profesional, sucursal y cita opcional.
- ClinicalNote formato SOAP + texto libre con máquina de estados DRAFT/FINAL/CORRECTED/CANCELLED.
  Al finalizar se calcula content_hash. Al corregir se crea una versión nueva con motivo.
  Una nota FINAL no se puede editar (prueba obligatoria).
- Antes de finalizar se muestra el modal de alertas críticas.
- Frontend: pestaña Expediente (secciones colapsables), pantalla "Atención" con nota SOAP,
  autoguardado del borrador cada 10 s y línea de tiempo clínica en la pestaña Resumen.
```

## FASE 5 — Odontograma
```
Implementa el módulo odontogram según docs/02 sección 3 y la regla 5:
- Catálogos configurables: piezas FDI permanentes (11–48) y temporales (51–85),
  superficies O/M/D/V/L/P/I (P solo en piezas superiores, L en inferiores, I en anteriores),
  y hallazgos con color y símbolo editables (seed: sano, caries, restauración, corona,
  endodoncia, ausente, extracción indicada, implante, prótesis fija, sellador, fractura, movilidad).
- ToothFinding como eventos con supersedes_id e is_current e índice único parcial.
  Distingue EXISTING, PLANNED y PERFORMED.
- GET /patients/{id}/odontogram?at=YYYY-MM-DD reconstruye el estado a una fecha.
- Frontend: componente SVG propio (no usar imágenes de terceros) con arcada superior e
  inferior, vista permanente/temporal/mixta, 5 superficies clicables por pieza, menú rápido
  de hallazgos, planificados en contorno discontinuo, leyenda, deslizador de historial
  y panel lateral con el historial de la pieza seleccionada. Uso cómodo en tableta
  (objetivos táctiles de 44 px o más).
- Pruebas: pieza FDI inválida, superficie inválida para la pieza, cambios sucesivos
  conservan el historial, consulta a fecha pasada.
```

## FASE 6 — Agenda
```
Implementa el módulo agenda:
- Provider (odontólogo), Resource (gabinete o sillón), horarios laborales y bloqueos.
- Appointment con máquina de estados de docs/02 sección 4 y AppointmentStatusHistory.
- Validación de conflictos en el BACKEND (mismo profesional o mismo recurso traslapado),
  con restricción de exclusión en PostgreSQL (btree_gist + tstzrange) como respaldo.
- Duración por tipo de procedimiento, lista de espera, motivo de cancelación y no-show.
- Recordatorios como tareas idempotentes (por ahora solo se registran; el envío real es Fase 2).
- Frontend: vistas día, semana y mes por profesional o gabinete, arrastrar para reprogramar,
  colores por estado (desde variables de tema) y botón "Iniciar atención" que crea el Encounter.
```

## FASE 7 — Diagnóstico, plan de tratamiento y presupuesto
```
Implementa los módulos diagnosis y treatment:
- Catálogo de diagnósticos configurable (texto + código opcional) asociado a encounter,
  profesional y pieza/superficie opcional.
- Catálogo de procedimientos con lista de precios por sucursal.
- TreatmentPlan con fases, alternativas, prioridad, ProcedurePlanned (se refleja como PLANNED
  en el odontograma), presupuesto con descuentos autorizados y aceptación total o parcial
  registrada con fecha y responsable.
- Registrar ProcedurePerformed desde la atención: marca el planificado como realizado
  y crea el evento PERFORMED en el odontograma. NO genera pago automáticamente; genera
  un Charge sugerido (regla 4).
- Frontend: pestaña Tratamientos con plan por fases, total por fase y general,
  y PDF del presupuesto con el logo de la clínica.
```

## FASE 8 — Agente de IA por voz (Ollama)
```
Implementa docs/03_AGENTE_IA_VOZ.md completo. Lee también las reglas 9 y 10 de CLAUDE.md.

Backend (app/ai/):
1. stt.py con faster-whisper: carga perezosa, una sola instancia, language="es",
   vad_filter=True, initial_prompt con vocabulario dental (oclusal, mesial, distal,
   vestibular, palatino, lingual, incisal, resina, amalgama, endodoncia, corona, pulpitis, etc.).
2. dental_parser.py: números hablados a FDI ("treinta y seis", "tres seis", "pieza 36",
   "órgano dentario 36", "el 36"), superficies a O/M/D/V/L/P/I y detección de temporales.
   Con pruebas exhaustivas.
3. ollama_client.py con httpx async: /api/chat con "format" = JSON Schema generado desde
   los modelos Pydantic de actions.py, options.temperature=0, timeout configurable, y
   /api/tags para el estado y el digest del modelo.
4. actions.py: unión discriminada por "type" con las 11 acciones de la sección 4.
   Acciones prohibidas: si el modelo las devuelve, se descartan y se registran.
5. interpreter.py: arma el prompt (prompts/system_es.md + catálogos reales + contexto de
   pantalla + pistas del parser), llama a Ollama, valida y crea AiSuggestion PENDING.
6. applier.py: al aceptar, llama al servicio de dominio correspondiente con
   origin=AI_ASSISTED y deja un AuditEvent AI_APPLY con el modelo y su digest.
7. Endpoints: POST /ai/transcribe (multipart audio), POST /ai/interpret,
   GET /ai/suggestions?encounter_id=, POST /ai/suggestions/{id}/accept (con edición opcional),
   POST /ai/suggestions/{id}/reject, GET /ai/status, GET/PUT /ai/settings.
   Permisos ai.use y ai.configure.
8. Si Ollama no responde: la transcripción funciona y /interpret devuelve 503 con un mensaje
   claro. El frontend ofrece entonces insertar el texto en la nota.

Frontend (src/modules/ai/):
9. Botón flotante de micrófono (Alt+M) con estados inactivo, escuchando y procesando.
   MediaRecorder en fragmentos y transcripción en vivo editable.
10. Panel "Propuestas del asistente": tarjetas por acción con badge "IA", vista previa
    fantasma en el odontograma, botones Aceptar/Editar/Rechazar y "Aceptar todo".
    Muestra las alertas clínicas antes de aceptar procedimientos.
11. Configuración → Asistente IA: estado de Ollama y Whisper, modelo instalado, prueba
    de micrófono, selector de modelo (de /api/tags) y opción de guardar audio (desactivada).

Calidad:
12. tests/ai/corpus.jsonl con 40 o más dictados realistas en español de México y el JSON
    esperado. Script python -m app.ai.eval con un reporte de precisión.
    FakeOllama para las pruebas de integración.
13. Prueba obligatoria: ninguna ruta de la IA escribe en tablas clínicas sin aceptación humana.
```

## FASE 9 — Consentimientos, documentos e imágenes
```
Implementa documents e imaging:
- Plantillas versionadas (HTML con variables {{paciente.nombre}}, {{procedimiento}}, etc.).
- Consentimiento ligado a procedimiento o plan, firma en pantalla táctil (canvas),
  identificación del firmante, fecha y hora, PDF generado, hash SHA-256 e inmutabilidad (regla 7).
- Imágenes: carga múltiple (JPG, PNG, PDF), metadatos (tipo de estudio: intraoral,
  extraoral, periapical, bitewing, panorámica, cefalometría), pieza o procedimiento opcional,
  miniaturas, visor con zoom y brillo/contraste, y acceso auditado.
- StorageBackend local con rutas no adivinables. Los archivos se sirven por un endpoint
  con permisos (nunca como estáticos públicos).
```

## FASE 10 — Cobranza básica
```
Implementa billing: Charge, Payment (efectivo, tarjeta, transferencia), anticipos,
aplicación de pagos a cargos, saldo del paciente, recibo PDF con logo, cancelación con
autorización y motivo, y corte de caja por sesión. Pruebas de la regla 4 (un pago no
cambia el estado clínico). Pestaña Cuenta en la ficha del paciente.
```

## FASE 11 — Reportes, respaldos y continuidad
```
- Reportes: pacientes nuevos y activos, citas por estado y no-show, producción por
  profesional y sucursal, planes aceptados y pendientes, cuentas por cobrar y uso del
  asistente IA (sugerencias aceptadas y rechazadas). Exportación CSV auditada.
- Dashboard por rol en la página de inicio.
- scripts/backup.(ps1|sh): pg_dump cifrado + storage/ con retención.
  scripts/restore_test: restaura en una BD temporal, verifica y registra el resultado.
- Documenta en docs/OPERACION.md cómo programar el respaldo en Windows (Programador de
  tareas) y en Linux (cron).
```

## FASE 12 — E2E y endurecimiento
```
- Playwright: flujo completo Paciente → Cita → Atención → Dictado IA (con FakeOllama) →
  aceptar propuestas → Odontograma → Diagnóstico → Plan → Consentimiento → Pago → Seguimiento.
- Revisión de seguridad: OWASP Top 10, cabeceras de seguridad, CORS estricto,
  dependencias vulnerables (pip-audit y npm audit) y secretos fuera del código.
- Revisión de accesibilidad (teclado, contraste, etiquetas) y rendimiento (p95 de 2 s o menos
  en pantallas habituales).
- Actualiza README, docs/02 y crea docs/MANUAL_USUARIO.md (con capturas) y docs/MANUAL_TECNICO.md.
```

---

## Prompts útiles en cualquier momento
- **Revisión:** `Revisa el módulo X contra CLAUDE.md y docs/. Lista incumplimientos de reglas clínicas, seguridad y tema, y corrígelos con pruebas.`
- **Pendiente clínico:** `Agrega a docs/PENDIENTES_CLINICOS.md la duda: ... y aplica un valor configurable por defecto.`
- **Afinar IA:** `Estos dictados fallaron: [pegar]. Agrégalos al corpus, ajusta el prompt o el parser y vuelve a correr app.ai.eval.`
