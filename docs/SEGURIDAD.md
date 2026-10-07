# Seguridad

Revisión de seguridad hecha en la Fase 12 (CLAUDE.md sec. 7, "endurecimiento"), más las
medidas que ya existían desde fases anteriores. No sustituye una auditoría externa antes
de manejar datos reales de pacientes — ver "Alcance y límites" al final.

## 1. OWASP Top 10 — qué aplica y qué se hizo

| Categoría OWASP | Situación en DentalCare |
|---|---|
| A01 Control de acceso roto | RBAC + ABAC por sucursal desde la Fase 1 (`require_permission`, `X-Clinic-Id`); catálogo en `docs/MATRIZ_PERMISOS.md`. El superadmin no tiene acceso automático a contenido clínico (CLAUDE.md sec. 5). Probado con pruebas de integración por módulo (p. ej. `tests/integration/*/test_*.py` con un usuario sin el permiso esperado). |
| A02 Fallas criptográficas | Contraseñas con Argon2id (`argon2-cffi`), JWT de corta duración + refresh token (`app/core/security.py`). Fase 12: `Settings` ya **no arranca** con `ENVIRONMENT=production` si `JWT_SECRET` se quedó en el valor de ejemplo (`change-me`) — antes era posible desplegar firmando tokens con un secreto público (este mismo repositorio). |
| A03 Inyección | Toda consulta pasa por el ORM (SQLAlchemy) o está parametrizada; toda entrada se valida con Pydantic v2. No se encontró SQL armado por concatenación de strings. |
| A04 Diseño inseguro | Reglas clínicas inviolables (CLAUDE.md sec. 4) con pruebas unitarias por módulo (estados de nota, no-borrado-físico, planificado≠realizado, etc.). |
| A05 Configuración de seguridad incorrecta | Fase 12: nuevas cabeceras de seguridad (sección 2) y documentación interactiva de la API (Swagger/Redoc) deshabilitada fuera de desarrollo (sección 3). |
| A06 Componentes vulnerables | Fase 12: `pip-audit` (backend) y `npm audit` (frontend, `e2e/`) — ver sección 4. |
| A07 Identificación y autenticación | MFA TOTP para `admin_clinica` (**deshabilitada temporalmente**, ver nota abajo), *rate limiting* en el login desde la Fase 1 (`app/modules/iam/service.py`/`rules.py`). |
| A08 Integridad de software y datos | Documentos firmados con hash SHA-256 inmutable (regla 7); notas clínicas `FINAL` no se modifican (regla 1). |
| A09 Fallas de registro y monitoreo | `AuditEvent` append-only: lecturas de expediente, exportaciones, firmas, cambios clínicos, accesos denegados (`AccessDeniedAuditMiddleware`) y uso de IA (CLAUDE.md sec. 5). |
| A10 SSRF | Sin llamadas salientes a servicios externos controlables por el usuario; Ollama/Whisper corren en local y sus URLs vienen de configuración del servidor, no de la petición. |

> **MFA deshabilitada temporalmente (2026-10-06):** a petición del dueño del proyecto,
> `rules.MFA_REQUIRED_ROLES` (`backend/app/modules/iam/rules.py`) está vacío por ahora —
> ningún rol, incluido `admin_clinica`, exige configurar ni verificar MFA al entrar.
> CLAUDE.md sec. 5 sigue pidiendo MFA para `admin_clinica`; para reactivarla solo hay
> que regresar esa constante a `frozenset({"admin_clinica"})` y reiniciar el backend
> (no toca la base de datos).

## 2. Cabeceras de seguridad (`app/core/security_headers.py`)

`SecurityHeadersMiddleware` agrega a toda respuesta de la API:

| Cabecera | Valor | Motivo |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | evita que el navegador adivine un tipo de contenido distinto al declarado |
| `X-Frame-Options` | `DENY` | evita *clickjacking* embebiendo la API en un `<iframe>` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | no filtra la ruta completa al navegar a otro origen |
| `Permissions-Policy` | `camera=(), geolocation=(), microphone=(), payment=(), usb=()` | la API en sí no usa estas capacidades (el micrófono lo usa la página del frontend, otro origen, no afectado por esta cabecera) |
| `Content-Security-Policy` | `default-src 'none'` (excepto `/docs`, `/redoc`, `/openapi.json`) | la API no sirve HTML/JS propio fuera de la documentación interactiva |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains`, solo si `ENVIRONMENT=production` | fuerza HTTPS en producción; se omite en desarrollo porque ahí se sirve por HTTP |

Prueba: `backend/tests/integration/test_security_headers.py`.

## 3. Documentación interactiva de la API

`/docs`, `/redoc` y `/openapi.json` (Swagger UI, Redoc, el esquema OpenAPI completo) solo
existen cuando `ENVIRONMENT` no es `production` (`app/core/config.py::docs_urls`,
`app/main.py`). En producción no tiene sentido exponer el esquema completo de la API ni
cargar un bundle de un CDN externo. Prueba: `test_docs_routes_not_csp_restricted_in_development`
y `tests/unit/core/test_config.py`.

## 4. Dependencias vulnerables (`pip-audit` / `npm audit`)

Corrida el 2026-10-06. Resultado y correcciones:

| Paquete | Antes | Ahora | Resultado |
|---|---|---|---|
| `fastapi` (y `starlette`, transitiva) | 0.115.6 | 0.142.2 | corregido |
| `pyjwt` | 2.10.1 | 2.15.0 | corregido |
| `python-multipart` | 0.0.20 | 0.0.31 | corregido |
| `python-dotenv` | 1.0.1 | 1.2.2 | corregido |
| `pillow` | 11.0.0 | 12.3.0 | corregido |
| `black` (herramienta de desarrollo) | 24.10.0 | 26.3.1 | corregido |
| `pytest`/`pytest-asyncio` (herramientas de desarrollo) | 8.3.4 / 0.25.0 | 9.0.3 / 1.4.0 | corregido |
| `xhtml2pdf` | 0.2.16 | 0.2.16 | **sin corregir** (ver abajo) |

Después de cada cambio se corrió la suite completa (`pytest`, 298 pruebas), `ruff`, `black
--check` y `mypy` (estricto) sin errores. Dos ajustes de tipos fueron necesarios por el
salto de versión de Pillow (`imaging/service.py`, `branding/service.py`): `Image.convert()`
ahora se guarda en una variable nueva en vez de reasignar la original, para que `mypy` no
confunda el tipo base `Image` con el subtipo `ImageFile` que abre `Image.open()`.

**Riesgo aceptado — `xhtml2pdf==0.2.16`:** [CVE-2024-25885](https://github.com/advisories/GHSA-jj5c-hhrg-vv5h),
ReDoS (denegación de servicio por expresión regular) en `getcolor()` al parsear un color
CSS malformado. Sin versión corregida publicada todavía. Se usa solo para generar el PDF
de un consentimiento a partir de una `DocumentTemplate` (Fase 9) — el HTML de entrada
**siempre lo escribe personal autenticado con el permiso `documents.write`** (odontólogo o
especialista), nunca un paciente ni una petición anónima, así que el vector de ataque
requiere una cuenta ya comprometida con ese permiso. Se revisará de nuevo cuando el
proyecto publique una versión corregida o al migrar el generador de PDF.

`npm audit` en `frontend/` y `e2e/`: **0 vulnerabilidades** en ambos.

## 5. CORS y *rate limiting* (ya existían, se confirmaron en esta fase)

- CORS (`app/main.py`, `CORSMiddleware`): una sola lista blanca de orígenes
  (`cors_origins` en `.env`, por defecto solo `http://localhost:5174`), nunca un comodín
  (`*`) — estricto desde la Fase 0.
- *Rate limiting* en el login: `app/modules/iam/service.py`/`rules.py`, desde la Fase 1.

## 6. Secretos

- `.env` nunca se sube a git (`.gitignore`); `backend/.env.example` se mantiene
  actualizado (incluye `AI_FAKE_MODE`, solo para Playwright — CLAUDE.md sec. 5).
- Revisión del código fuente: no se encontraron secretos reales. El único valor
  parecido a una contraseña es `DEMO_PASSWORD` en `backend/app/seed.py`
  (`Dentia2025!`), la contraseña de las cuentas ficticias que crea el seed —
  documentada como tal, nunca usada contra datos reales (CLAUDE.md sec. 5: "prohibido
  usar datos reales de pacientes").
- `jwt_secret` tiene un valor de ejemplo (`change-me`) solo para desarrollo; Fase 12 lo
  bloquea en producción (sección 2).

## Alcance y límites

Esta revisión es una pasada de un desarrollador con herramientas automáticas
(`pip-audit`, `npm audit`, lectura del código), no una auditoría de un tercero ni una
prueba de penetración. Antes de manejar datos reales de pacientes, CLAUDE.md ya exige no
hacerlo (sec. 5) — esta revisión no cambia esa regla, solo reduce el riesgo de la
superficie que ya existe (cabeceras, dependencias, documentación expuesta, secreto por
defecto).
