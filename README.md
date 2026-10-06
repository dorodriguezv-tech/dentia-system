# DentalCare — Sistema Clínico Dental

Plataforma web para clínicas dentales en México. Expediente clínico, odontograma,
agenda y un asistente de IA por voz que corre 100 % en local (Ollama + faster-whisper).

Las reglas de negocio, el stack y las convenciones viven en [`CLAUDE.md`](./CLAUDE.md).
El diseño detallado está en [`docs/`](./docs).

## Requisitos
- Python 3.12+ (se probó también con 3.13)
- Node.js 20 LTS o superior
- PostgreSQL 16 (nativo o vía Docker; también se probó contra una instalación nativa de
  PostgreSQL 18, compatible por protocolo)
- [Ollama](https://ollama.com) y un modelo descargado (`ollama pull qwen2.5:7b`) — solo
  necesario para el asistente de IA (Fase 8)
- Opcional: Docker y Docker Compose

## Estructura
```
backend/   API FastAPI (Python)
frontend/  Interfaz React + TypeScript (Vite)
docs/      Especificación y arquitectura
storage/   Archivos locales (ignorado en git)
e2e/       Pruebas Playwright (se agregan en fases posteriores)
```

## Puesta en marcha

### 1. Base de datos
**Con Docker:**
```bash
cp backend/.env.example backend/.env   # ajusta los valores si lo necesitas
docker compose up -d db
```

**Sin Docker (PostgreSQL nativo, 16 o 18):** crea un rol y una base que coincidan con
`DATABASE_URL` en `backend/.env` (valores por defecto: usuario y base `dentia`), conectándote
como superusuario (`psql -U postgres`):
```sql
CREATE ROLE dentia WITH LOGIN PASSWORD 'dentia';
CREATE DATABASE dentia OWNER dentia;
CREATE DATABASE dentia_test OWNER dentia;  -- usada solo por las pruebas de integracion (pytest)
```

### 2. Backend
**Windows (PowerShell):**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8001
```

**Linux / macOS:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8001
```

Verifica: `curl http://localhost:8001/api/v1/health` → `{"status":"ok"}`.

`python -m app.seed` crea datos ficticios (Faker es_MX) de arranque: una clínica demo con un
`admin_clinica` (`admin@dentalcare-demo.mx` / `Dentia2025!`, debe configurar MFA al entrar), un
`odontologo` (`odontologo@dentalcare-demo.mx` / `Dentia2025!`), 50 pacientes ficticios, 3
atenciones de ejemplo (una nota finalizada con alergia/medicamento/antecedente que disparan
alertas, una nota en borrador y una nota corregida con dos versiones), un odontograma de muestra
(caries tratada con resina en la pieza 36 —con su historial—, caries activa en 36 y 46, pieza 18
ausente), una agenda de muestra (1 profesional, 1 gabinete, horario laboral de lunes a viernes,
una cita reservada y otra confirmada para mañana, una mas en 7 días) y un plan de tratamiento de
muestra (catálogo de 5 procedimientos, 1 diagnóstico, plan de 2 fases en la pieza 46: la primera
ya aceptada y realizada —con su cargo sugerido—, la segunda solo planificada). Es idempotente.

Pruebas y calidad (las pruebas de integración de `iam`/`audit` necesitan la base `dentia_test`
del paso 1):
```bash
pytest
ruff check app tests
black --check app tests
mypy app
```

### 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev       # http://localhost:5174
```

Pruebas y calidad:
```bash
npm run test
npm run lint   # eslint + script que verifica que no haya colores #hex fuera de src/theme/
npm run build
```

### 4. Asistente de IA (opcional, local)
```bash
ollama pull qwen2.5:7b
ollama serve
```
Ver [`docs/03_AGENTE_IA_VOZ.md`](./docs/03_AGENTE_IA_VOZ.md). Si Ollama no está disponible,
el resto del sistema funciona sin cambios (la transcripción sigue funcionando; solo
`/ai/interpret` responde 503 y el frontend ofrece insertar el dictado como texto libre).

`faster-whisper` descarga el modelo (`WHISPER_MODEL`, por defecto `small`, ~500 MB) de
Hugging Face la primera vez que se usa, no al instalar. En Windows, si la red tiene un
proxy con inspección TLS, esa descarga puede fallar con `CERTIFICATE_VERIFY_FAILED` aunque
`curl`/el navegador sí funcionen: `pip-system-certs` (ya en `requirements.txt` para
`sys_platform == "win32"`) lo resuelve haciendo que Python confíe en el mismo almacén de
certificados que ya usa el sistema.

`python -m app.ai.eval` mide la precisión del modelo configurado contra
`tests/ai/corpus.jsonl` (50 dictados de ejemplo) llamando al Ollama real — a diferencia de
las pruebas automatizadas (`pytest`), que usan un `FakeOllama` y no necesitan Ollama
instalado.

## Decisiones de arquitectura
Ver [`docs/adr/`](./docs/adr). La primera decisión (ruta de implementación y stack) está en
[`docs/adr/ADR-001-ruta-b-stack.md`](./docs/adr/ADR-001-ruta-b-stack.md).

## Estado del proyecto
Se construye por fases (vertical slices), ver [`prompts/PROMPTS_CLAUDE_CODE.md`](./prompts/PROMPTS_CLAUDE_CODE.md).
Completadas: **Fase 0 — Base del proyecto**, **Fase 1 — IAM, sucursales y auditoría**
(ver [`docs/MATRIZ_PERMISOS.md`](./docs/MATRIZ_PERMISOS.md) para el catálogo de roles y permisos),
**Fase 2 — Tema y marca configurables** (Configuración → Apariencia), **Fase 3 — Pacientes**
(búsqueda global `Ctrl+K`, alta con detección de duplicados, expediente, contactos, foto) y
**Fase 4 — Expediente clínico y atención** (antecedentes/alergias/medicamentos/signos vitales,
alertas críticas derivadas, nota clínica SOAP versionada con autoguardado, finalizar/corregir/
cancelar; ver [`docs/02_ARQUITECTURA.md`](./docs/02_ARQUITECTURA.md#54-expediente-atención-y-notas-fase-4)),
**Fase 5 — Odontograma** (SVG propio por pieza y superficie, historial por eventos que nunca se
sobrescribe, reconstrucción a una fecha pasada, vistas permanente/temporal/mixta; ver
[`docs/02_ARQUITECTURA.md`](./docs/02_ARQUITECTURA.md#55-odontograma-fase-5)),
**Fase 6 — Agenda** (citas con máquina de estados, traslapes validados en el backend y respaldados
por una restricción `EXCLUDE` de Postgres, calendario propio con arrastrar-para-reprogramar, botón
"Iniciar atención"; ver [`docs/02_ARQUITECTURA.md`](./docs/02_ARQUITECTURA.md#56-agenda-fase-6)) y
**Fase 7 — Diagnóstico y tratamiento** (plan por fases con presupuesto, planificado/realizado como
entidades separadas que se reflejan en el odontograma, PDF del presupuesto con el logo de la
clínica, cargo sugerido al registrar un procedimiento realizado; ver
[`docs/02_ARQUITECTURA.md`](./docs/02_ARQUITECTURA.md#57-diagnóstico-y-tratamiento-fase-7)) y
**Fase 8 — Asistente de IA por voz** (dictado → transcripción local con faster-whisper → propuestas
de acción interpretadas por Ollama, validadas contra los catálogos reales de la clínica y aceptadas/
editadas/rechazadas una por una — la IA nunca escribe directo en el expediente; ver
[`docs/02_ARQUITECTURA.md`](./docs/02_ARQUITECTURA.md#58-agente-de-ia-por-voz-fase-8)) y
**Fase 9 — Consentimientos e imagenología** (plantillas HTML versionadas, firma en pantalla táctil
con `<canvas>`, PDF generado con hash SHA-256 e inmutable una vez firmado, carga múltiple de
imágenes/radiografías con miniaturas y visor con zoom/brillo/contraste, lectura auditada; ver
[`docs/02_ARQUITECTURA.md`](./docs/02_ARQUITECTURA.md#59-consentimientos-e-imagenología-fase-9)) y
**Fase 10 — Cobranza** (pagos en efectivo/tarjeta/transferencia con aplicación total o parcial a
uno o varios cargos o como anticipo, saldo y estado de cada cargo calculados contra los pagos
activos y nunca guardados —regla 4—, cancelación de cargos/pagos con motivo, recibo en PDF, corte
de caja por sesión; la cobranza se puede desactivar por sucursal para clínicas universitarias de
práctica sin dejar de generar el cargo sugerido; ver
[`docs/02_ARQUITECTURA.md`](./docs/02_ARQUITECTURA.md#510-cobranza-fase-10)) y
**Fase 11 — Reportes, respaldos y continuidad** (seis reportes de solo lectura con exportación CSV
auditada — pacientes, citas y tasa de no-show, producción por profesional, planes de tratamiento,
cuentas por cobrar, uso del asistente de IA —, tablero de inicio por rol que arma cada sección
según el permiso propio del usuario en vez de exigir `reports.read`, y `scripts/backup.ps1`/`.sh` +
`scripts/restore_test.ps1`/`.sh` para respaldar la base de datos y `storage/` cifrados, con prueba
automática de restauración en una base desechable; ver
[`docs/02_ARQUITECTURA.md`](./docs/02_ARQUITECTURA.md#511-reportes-y-tablero-fase-11) y
[`docs/OPERACION.md`](./docs/OPERACION.md)).
