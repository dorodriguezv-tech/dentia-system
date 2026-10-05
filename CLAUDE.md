# DentalCare — Sistema Clínico Dental

Instrucciones permanentes para Claude Code. Léelas antes de cada tarea y respétalas siempre.

## 1. Qué es este proyecto
Es una plataforma web para clínicas dentales en México. Su núcleo es el **expediente clínico odontológico**, el **odontograma** y el **flujo de atención**:

paciente → cita → consulta → diagnóstico → odontograma → tratamiento → pago → seguimiento

Incluye un **asistente de IA por voz**. Funciona 100 % local con Ollama y Whisper: escucha al odontólogo y **propone** datos para el expediente, el odontograma, los diagnósticos y el plan. El odontólogo siempre confirma antes de guardar.

Documentos de referencia en `docs/`:
- `docs/01_ANALISIS_Y_DECISIONES.md`: resumen de las especificaciones v1.0 y v2.0 y las decisiones tomadas.
- `docs/02_ARQUITECTURA.md`: modelo de datos, API y estructura.
- `docs/03_AGENTE_IA_VOZ.md`: diseño del asistente de voz.
- `docs/04_TEMAS_Y_MARCA.md`: colores y logo configurables.

## 2. Stack (no cambiar sin crear un ADR en docs/adr/)
| Capa | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x (async) + asyncpg, Alembic |
| Base de datos | PostgreSQL 16 |
| Frontend | React 18 + TypeScript (compila a JavaScript) + Vite, React Router, TanStack Query, Zustand |
| Estilos | CSS Modules + **variables CSS** para el tema (no colores fijos en componentes) |
| IA local | Ollama (`http://localhost:11434`) y faster-whisper para voz a texto |
| Autenticación | JWT de corta duración + refresh token, contraseñas con Argon2id, MFA TOTP |
| Archivos | Carpeta local `storage/` mediante una interfaz `StorageBackend` (después S3/MinIO) |
| Pruebas | pytest + httpx (backend), Vitest + Testing Library (frontend), Playwright (E2E) |
| IDE | Visual Studio Code (se incluye `.vscode/` con depuración de API y web) |

## 3. Estructura del repositorio
```
dental-clinic/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/          # config, db, security, deps, errors, storage
│   │   ├── audit/         # AuditEvent, middleware, servicio
│   │   ├── modules/       # un paquete por módulo (vertical slice)
│   │   │   └── <modulo>/  models.py schemas.py service.py router.py rules.py
│   │   └── ai/            # stt.py, ollama_client.py, interpreter.py, actions.py, prompts/
│   ├── alembic/
│   └── tests/{unit,integration}
├── frontend/
│   └── src/
│       ├── app/           # router, layout, providers
│       ├── theme/         # ThemeProvider, presets, tokens.css
│       ├── api/           # cliente HTTP generado/tipado
│       ├── components/    # UI reutilizable
│       └── modules/       # pacientes, expediente, odontograma, agenda, ...
├── e2e/                   # Playwright
├── storage/               # archivos locales (ignorado en git)
├── docs/
├── docker-compose.yml     # PostgreSQL (opcional; también puede ser instalación nativa)
└── .vscode/
```

## 4. Reglas clínicas inviolables
Cada regla debe tener pruebas unitarias.
1. Una nota clínica en estado **FINAL** no se modifica. Las correcciones crean una nueva versión con estado CORRECTED, motivo y autor. Estados: DRAFT → FINAL → (CORRECTED | CANCELLED).
2. No existe borrado físico de registros clínicos desde la aplicación. Se usa anulación con motivo y auditoría.
3. **Lo planificado no equivale a lo realizado.** `ProcedurePlanned` y `ProcedurePerformed` son entidades separadas.
4. **Un presupuesto aceptado no es un pago, y un pago no cambia el estado clínico.**
5. Una pieza puede tener muchos hallazgos históricos, pero solo uno **vigente** por pieza y superficie. El historial se guarda como eventos y nunca se sobrescribe.
6. Cada hallazgo, diagnóstico o procedimiento lleva fecha, autor (profesional) y contexto (encounter).
7. Los documentos firmados no se sobrescriben. Cada versión nueva lleva un hash SHA-256 nuevo.
8. Las alertas críticas (alergias, medicamentos de riesgo, antecedentes) se muestran **antes** de acciones relevantes: recetar, cerrar nota o registrar procedimiento.
9. **La IA nunca escribe directamente en el expediente.** Crea `AiSuggestion` en estado PENDING. Solo una acción humana (aceptar o editar) la aplica. La IA no puede cerrar notas, firmar, borrar ni recetar.
10. Todo lo que provenga de la IA queda marcado `origin = AI_ASSISTED` con modelo, versión y fecha.

## 5. Seguridad y privacidad
- RBAC con estos roles: superadmin, admin_clinica, odontologo, especialista, asistente, recepcion, caja. Además, ABAC por sucursal y tipo de dato.
- El superadmin **no** tiene acceso automático a contenido clínico.
- Se auditan: lectura de expedientes, exportaciones, firmas, cambios clínicos, accesos denegados y uso de IA.
- Los secretos van en `.env` (nunca en git). Existe un `.env.example` siempre actualizado.
- **Prohibido usar datos reales de pacientes.** Los seeds usan datos ficticios (Faker es_MX).
- La IA no hace llamadas a servicios externos. El audio no se guarda por defecto.
- Se valida toda la entrada con Pydantic. Las consultas pasan por el ORM o son parametrizadas. Hay protección contra XSS en el frontend y rate limiting en el login.

## 6. Convenciones de código
- Identificadores en inglés; textos de la interfaz y mensajes de usuario en **español de México**.
- Llaves primarias UUID. Todas las tablas tienen `created_at`, `created_by`, `updated_at` y `clinic_id` cuando aplique.
- API versionada en `/api/v1`. OpenAPI generado por FastAPI. Errores con formato `{code, message, details}`.
- Las máquinas de estado (cita, nota, plan) son explícitas en `rules.py`, con transiciones válidas probadas.
- Las validaciones de conflicto de agenda viven en el **backend**.
- El frontend no lleva colores fijos: usa siempre `var(--color-...)`.
- Notación dental **FDI** (11–48 permanentes, 51–85 temporales).
- Python: ruff + black + mypy (modo estricto en `domain`). TS: eslint + prettier, `strict: true`.

## 7. Forma de trabajar
- Se trabaja por **vertical slices**. Cada módulo se cierra con: migración Alembic + API + UI + pruebas unitarias e integración + documentación. Después se pasa al siguiente.
- Antes de programar un módulo, presenta un plan corto (modelos, endpoints, pantallas, pruebas) y espera confirmación si hay ambigüedad clínica.
- Si una decisión clínica no está definida (por ejemplo, el catálogo de estados del odontograma), usa un **catálogo configurable** con valores por defecto razonables y anótala en `docs/PENDIENTES_CLINICOS.md`.
- Ejecuta las pruebas antes de declarar terminado. No marques nada como listo con pruebas fallando.

## 8. Comandos
```bash
# Base de datos (Docker) — o PostgreSQL 16 nativo con los datos de .env
docker compose up -d db

# Backend
cd backend
python -m venv .venv && .venv\Scripts\activate      # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
alembic upgrade head
python -m app.seed                                   # datos ficticios
uvicorn app.main:app --reload --port 8001            # 8000 esta ocupado por otro sistema en esta maquina
pytest

# Frontend
cd frontend
npm install
npm run dev                                          # http://localhost:5174 (5173 ocupado tambien)
npm run test

# IA local
ollama pull qwen2.5:7b
ollama serve
```

## 9. Definición de terminado (por módulo)
- [ ] Migración aplicada y reversible
- [ ] Endpoints con permisos y auditoría
- [ ] Pantallas responsivas (monitor y tableta) usando variables de tema
- [ ] Reglas clínicas del módulo con pruebas
- [ ] Pruebas de integración de la API
- [ ] Sección actualizada en `docs/02_ARQUITECTURA.md`
