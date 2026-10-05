# DentalCare — Sistema Clínico Dental

Plataforma web para clínicas dentales en México. Expediente clínico, odontograma,
agenda y un asistente de IA por voz que corre 100 % en local (Ollama + faster-whisper).

Las reglas de negocio, el stack y las convenciones viven en [`CLAUDE.md`](./CLAUDE.md).
El diseño detallado está en [`docs/`](./docs).

## Requisitos
- Python 3.12+ (se probó también con 3.13)
- Node.js 20 LTS o superior
- PostgreSQL 16 (nativo o vía Docker)
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

**Sin Docker (PostgreSQL 16 nativo):** crea una base y un usuario que coincidan con
`DATABASE_URL` en `backend/.env`.

### 2. Backend
**Windows (PowerShell):**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Linux / macOS:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Verifica: `curl http://localhost:8000/api/v1/health` → `{"status":"ok"}`.

Pruebas y calidad:
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
npm run dev       # http://localhost:5173
```

Pruebas y calidad:
```bash
npm run test
npm run lint
npm run build
```

### 4. Asistente de IA (opcional, local)
```bash
ollama pull qwen2.5:7b
ollama serve
```
Ver [`docs/03_AGENTE_IA_VOZ.md`](./docs/03_AGENTE_IA_VOZ.md). Si Ollama no está disponible,
el resto del sistema funciona sin cambios.

## Decisiones de arquitectura
Ver [`docs/adr/`](./docs/adr). La primera decisión (ruta de implementación y stack) está en
[`docs/adr/ADR-001-ruta-b-stack.md`](./docs/adr/ADR-001-ruta-b-stack.md).

## Estado del proyecto
Se construye por fases (vertical slices), ver [`prompts/PROMPTS_CLAUDE_CODE.md`](./prompts/PROMPTS_CLAUDE_CODE.md).
Completada: **Fase 0 — Base del proyecto**.
