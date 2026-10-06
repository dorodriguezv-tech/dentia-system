# Manual técnico — DentalCare

Para quien instala, despliega o mantiene el sistema (no es un manual de usuario — ese
es [`docs/MANUAL_USUARIO.md`](./MANUAL_USUARIO.md), ni el diseño detallado del sistema —
eso es [`docs/02_ARQUITECTURA.md`](./02_ARQUITECTURA.md)). Resume en un solo lugar lo que
alguien necesita para poner el sistema a correr, configurarlo y diagnosticar un
problema. Los pasos completos de instalación están en el [`README`](../README.md) — aquí
solo el resumen y lo que el README no cubre: variables de entorno, checklist de
despliegue y solución de problemas.

## 1. Arquitectura en una pantalla

```
Frontend (React + Vite, puerto 5174)  ──HTTP/JSON──>  Backend (FastAPI, puerto 8001)
                                                            │
                                                            ├─> PostgreSQL 16 (puerto 5432)
                                                            ├─> storage/ (archivos locales)
                                                            └─> Ollama (11434) + faster-whisper, opcionales
```

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x async, Alembic. Un paquete por módulo
  en `backend/app/modules/` (vertical slice: `models.py`, `schemas.py`, `service.py`,
  `router.py`, `rules.py`). Detalle completo en `docs/02_ARQUITECTURA.md`.
- Frontend: React 18 + TypeScript + Vite, React Router, TanStack Query, Zustand. CSS
  Modules con variables de tema (nunca colores fijos).
- Todo corre en la misma máquina/red de la clínica; el asistente de IA (Ollama +
  faster-whisper) es 100 % local, sin llamadas a servicios externos.

### Módulos del backend

| Módulo | Qué cubre |
|---|---|
| `iam` | Usuarios, roles, permisos, sucursales, sesiones (login, MFA, refresh token) |
| `branding` | Nombre, logo y colores configurables por sucursal |
| `patients` | Alta, búsqueda y expediente administrativo del paciente |
| `records` | Antecedentes, alergias, medicamentos, signos vitales |
| `encounters` | Atención y nota clínica SOAP versionada |
| `odontogram` | Hallazgos por pieza/superficie, como eventos históricos |
| `agenda` | Profesionales, gabinetes, citas y su máquina de estados |
| `diagnosis` | Diagnósticos clínicos |
| `treatment` | Planes de tratamiento, presupuestos, procedimientos planificados/realizados |
| `documents` | Plantillas de consentimiento y consentimientos firmados |
| `imaging` | Fotografías y radiografías |
| `billing` | Cargos, pagos, cortes de caja |
| `reports` | Reportes de solo lectura y el tablero de inicio por rol |
| `ai` | Transcripción (Whisper), interpretación (Ollama) y `AiSuggestion` |
| `audit` | Bitácora de auditoría append-only, usada por todos los módulos anteriores |

Agregar un módulo nuevo sigue siempre el mismo patrón (CLAUDE.md sec. 7): migración
Alembic + API + UI + pruebas unitarias e integración + sección nueva en
`docs/02_ARQUITECTURA.md`, un "vertical slice" a la vez.

## 2. Puesta en marcha rápida

Ver el [`README`](../README.md) para el paso a paso completo (base de datos, backend,
frontend, IA opcional). Resumen:

```bash
# Base de datos (Docker) u otra instancia de PostgreSQL 16 nativa
docker compose up -d db

# Backend
cd backend && pip install -r requirements.txt
copy .env.example .env   # Windows; cp en Linux/Mac
alembic upgrade head
python -m app.seed       # datos ficticios, idempotente
uvicorn app.main:app --reload --port 8001

# Frontend
cd frontend && npm install
copy .env.example .env
npm run dev               # http://localhost:5174
```

## 3. Variables de entorno

### Backend (`backend/.env`, ver `backend/.env.example`)

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `ENVIRONMENT` | `development` | `production` activa `Strict-Transport-Security`, exige un `JWT_SECRET` propio y desactiva `/docs`, `/redoc` y `/openapi.json` (ver sección 5 y `docs/SEGURIDAD.md`) |
| `DATABASE_URL` | `postgresql+asyncpg://dentia:dentia@localhost:5432/dentia` | cadena de conexión async a PostgreSQL |
| `JWT_SECRET` | `change-me-to-a-long-random-value` | firma los tokens de acceso/refresh — **obligatorio cambiarlo en producción**, el arranque falla si no lo haces |
| `JWT_ALGORITHM` | `HS256` | algoritmo de firma del JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | vigencia del token de acceso |
| `REFRESH_TOKEN_EXPIRE_HOURS` | `8` | vigencia del refresh token |
| `CORS_ORIGINS` | `["http://localhost:5174"]` | lista blanca de orígenes permitidos (JSON) — nunca usar `["*"]` |
| `STORAGE_DIR` | `../storage` | carpeta de archivos locales (fotos, PDF, radiografías) |
| `AI_ENABLED` | `true` | apaga por completo el asistente de IA si es `false` |
| `OLLAMA_URL` | `http://localhost:11434` | dirección del servidor Ollama local |
| `OLLAMA_MODEL` | `qwen2.5:7b` | modelo usado para interpretar el dictado |
| `OLLAMA_TIMEOUT_S` | `120` | tiempo máximo de espera a Ollama |
| `WHISPER_MODEL` | `small` | tamaño del modelo de transcripción (`faster-whisper`) |
| `WHISPER_DEVICE` | `cpu` | `cpu` o `cuda` si hay GPU disponible |
| `WHISPER_COMPUTE_TYPE` | `int8` | precisión de cómputo de Whisper |
| `AI_STORE_AUDIO` | `false` | si es `true`, guarda el audio del dictado (por defecto no se guarda — CLAUDE.md sec. 5) |
| `AI_SUGGESTION_TTL_HOURS` | `24` | horas antes de que una `AiSuggestion` sin revisar expire |
| `AI_FAKE_MODE` | `false` | **solo para Playwright** (`e2e/`): respuestas deterministas sin Ollama/Whisper reales — nunca en `true` fuera de E2E |

### Frontend (`frontend/.env`, ver `frontend/.env.example`)

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8001/api/v1` | URL base de la API que consume el frontend |

## 4. Comandos de prueba y calidad

```bash
# Backend (desde backend/, con el entorno virtual activo)
pytest                      # 298 pruebas (unitarias + integración)
ruff check app tests
black --check app tests
mypy app                    # modo estricto en app/
pip-audit -r requirements.txt   # dependencias vulnerables

# Frontend (desde frontend/)
npm run test
npm run lint                # eslint + verifica que no haya colores #hex fuera de theme/
npm run build
npm audit

# E2E (desde e2e/, levanta backend+frontend solos)
npx playwright test                              # flujo completo + accesibilidad + rendimiento
CAPTURE_SCREENSHOTS=1 npx playwright test tests/manual-capture.spec.ts   # regenerar docs/manual/*.png
```

## 5. Checklist antes de desplegar en producción

Ninguno de estos pasos es automático todavía — revísalos a mano antes de exponer el
sistema fuera de `localhost`:

- [ ] `ENVIRONMENT=production` en `backend/.env`.
- [ ] `JWT_SECRET` propio, largo y aleatorio (el arranque falla si se queda en el valor
      de ejemplo — ver `docs/SEGURIDAD.md` sec. 2).
- [ ] `CORS_ORIGINS` con el dominio real del frontend, nunca un comodín.
- [ ] Servir detrás de HTTPS (la cabecera `Strict-Transport-Security` que agrega
      `SecurityHeadersMiddleware` solo tiene sentido si de verdad hay HTTPS delante).
- [ ] `backend/.env` y `frontend/.env` fuera de git (ya lo están por `.gitignore`;
      confirma que nadie los subió a mano).
- [ ] `scripts/backup.ps1`/`.sh` programado (Programador de tareas en Windows, cron en
      Linux) con `BACKUP_PASSPHRASE` configurado — ver `docs/OPERACION.md`.
- [ ] `python -m app.seed` **no** se corre contra una base con pacientes reales (crea
      50 pacientes ficticios) — solo para desarrollo/demos.
- [ ] Datos reales de pacientes: confirma que de verdad se requieren (CLAUDE.md sec. 5
      prohíbe usar datos reales durante el desarrollo) y que el servidor de IA, si se
      usa, corre en la misma red local de la clínica (el audio/transcripción nunca debe
      salir a internet).
- [ ] `pip-audit`/`npm audit` sin hallazgos nuevos desde la última revisión
      (`docs/SEGURIDAD.md` sec. 4) antes de cada despliegue mayor.

## 6. Solución de problemas comunes

**`alembic upgrade head` falla o pytest no encuentra la base de datos de pruebas**
Falta crear `dentia_test` (solo para `pytest`, no para desarrollo normal):
```sql
CREATE DATABASE dentia_test OWNER dentia;
```

**El puerto 8000/5173 ya está en uso**
Es intencional: este proyecto usa 8001 (backend) y 5174 (frontend) porque 8000/5173
suelen estar ocupados por otro sistema en la máquina de desarrollo (ver CLAUDE.md sec. 8).
Si tu máquina no tiene ese conflicto, puedes usar los puertos por defecto de FastAPI/Vite
ajustando `VITE_API_URL` y el comando de `uvicorn`.

**Windows: `CERTIFICATE_VERIFY_FAILED` al descargar el modelo de Whisper**
Pasa detrás de un proxy corporativo con inspección TLS. `pip-system-certs` (ya en
`requirements.txt` para `sys_platform == "win32"`) hace que Python confíe en el mismo
almacén de certificados que ya usa Windows. Si persiste, descarga el modelo manualmente
y colócalo donde `faster-whisper` lo busque, o usa una red sin ese proxy la primera vez.

**El asistente de IA responde 503 en `/ai/interpret`**
Ollama no está corriendo o no tiene el modelo descargado (`ollama pull qwen2.5:7b`,
`ollama serve`). El resto del sistema sigue funcionando: la transcripción de voz a texto
no depende de Ollama, solo la interpretación de acciones.

**`mypy` falla después de actualizar Pillow**
Pillow tipa `Image.open()` como `ImageFile` pero sus métodos (`.convert()`, etc.)
regresan el tipo base `Image` — guarda el resultado en una variable **nueva** en vez de
reasignar la original (ver `imaging/service.py`/`branding/service.py` para el patrón ya
usado).

**Playwright no encuentra el backend/frontend al correr `npx playwright test`**
`e2e/playwright.config.ts` los levanta solo (`webServer`) contra la base de datos de
desarrollo — confirma que esa base ya tiene las migraciones aplicadas y, si quieres un
estado conocido, que corriste `python -m app.seed` antes. Si un backend/frontend ya
estaba corriendo en esos puertos, Playwright lo reutiliza (`reuseExistingServer`) en vez
de levantar uno nuevo — fuera de CI.

**`npx playwright test` tarda mucho o un test de rendimiento falla por poco**
`performance.spec.ts` corre contra `npm run dev` (sin build de producción), así que el
presupuesto de 2 s es pesimista a propósito; una falla aislada casi siempre es ruido de
la máquina donde corres la prueba (otro proceso pesado al mismo tiempo), no una
regresión real — vuelve a correr esa prueba sola antes de investigar más.

**`ollama serve` falla con `listen tcp 127.0.0.1:11434: bind: Only one usage...`**
No es una falla: Ollama ya está corriendo. El instalador de Windows deja una app en la
bandeja del sistema que arranca sola con Windows y ya escucha en ese puerto — confirma
con `curl http://localhost:11434/api/version` antes de correr `ollama serve` (ver
`docs/INICIO_RAPIDO.md` sec. 4).

**El log del backend muestra `POST /api/v1/auth/refresh ... 401 Unauthorized`**
Normal si el refresh token guardado en el navegador ya venció (`REFRESH_TOKEN_EXPIRE_HOURS`,
8 horas por defecto) o si abres el frontend con una sesión vieja de otra corrida — el
frontend simplemente manda al usuario de vuelta al login, no hay sesión que recuperar.
Si en desarrollo veías **dos** 401 idénticos seguidos en cada carga de página, era un bug
ya corregido: `AppProviders` llamaba `bootstrap()` (que dispara `/auth/refresh`) dentro de
un `useEffect` sin protección, y `<StrictMode>` (`main.tsx`) lo invoca dos veces en
desarrollo para detectar efectos sin limpieza — ahora un `useRef` evita la segunda llamada
(`frontend/src/app/providers.tsx`).

## 7. Dónde seguir leyendo

| Documento | Para qué |
|---|---|
| `docs/02_ARQUITECTURA.md` | Modelo de datos, API y diseño de cada módulo |
| `docs/03_AGENTE_IA_VOZ.md` | Diseño del asistente de voz |
| `docs/04_TEMAS_Y_MARCA.md` | Sistema de temas y marca |
| `docs/MATRIZ_PERMISOS.md` | Catálogo completo de roles y permisos |
| `docs/SEGURIDAD.md` | Revisión de seguridad (Fase 12) |
| `docs/OPERACION.md` | Respaldos, restauración y continuidad |
| `docs/PENDIENTES_CLINICOS.md` | Decisiones clínicas provisionales a validar |
| `docs/adr/` | Decisiones de arquitectura |
