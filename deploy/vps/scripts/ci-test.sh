#!/usr/bin/env bash
# Fase "Publicacion en Hostinger" sec. 11, paso 1-2: pruebas, calidad y
# auditoria de dependencias. Cualquier fallo detiene la publicacion (set -e).
# Corre en GitHub Actions (.github/workflows/release.yml) contra un
# PostgreSQL temporal (servicio del job); tambien sirve en local para probar
# el pipeline antes de etiquetar.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

echo "=== Backend: pytest, ruff, mypy, pip-audit ==="
cd "$REPO_ROOT/backend"
python -m pytest -q
python -m ruff check .
python -m mypy app
python -m pip_audit --strict

echo "=== Frontend: lint, test, build ==="
cd "$REPO_ROOT/frontend"
npm run lint
npm run test
npm run build
npm audit --omit=dev --audit-level=high

echo "=== E2E (Playwright) ==="
# playwright.config.ts arranca su propio backend/frontend (webServer) contra
# la base de datos "normal" (DATABASE_URL), DISTINTA de la base de pruebas de
# pytest (que ya corrio sus propias migraciones aparte, ver
# backend/tests/conftest.py) -- esta necesita sus migraciones tambien.
cd "$REPO_ROOT/backend"
python -m alembic upgrade head
cd "$REPO_ROOT/e2e"
npx playwright test

echo "=== ci-test.sh: todo en verde ==="
