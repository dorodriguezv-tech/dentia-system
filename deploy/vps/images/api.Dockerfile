# Imagen de la API (Fase "Publicacion en Hostinger" sec. 10). Se construye en
# GitHub Actions al crear una etiqueta (ver .github/workflows/release.yml);
# nadie construye esta imagen de produccion en su propia computadora.
#
# El contexto de build debe ser la raiz del repositorio (no backend/), para
# poder copiar tanto backend/ como alembic.ini -- ver scripts/ci-build-push.sh.
FROM python:3.12-slim AS base

# Dependencias de sistema que requieren paquetes Python nativos usados aqui
# (Pillow/reportlab para imagenes/PDF, asyncpg/psycopg para Postgres): libjpeg
# y zlib para Pillow; el resto ya viene en la imagen slim o es puro Python.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
# Las herramientas de desarrollo (pytest, ruff, black, mypy, pip-audit) ya
# corrieron en CI (ci-test.sh) antes de llegar aqui -- no hace falta
# instalarlas de nuevo en la imagen de produccion.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pytest pytest-asyncio pytest-cov ruff black mypy pip-audit \
    || true

COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini

# Usuario sin privilegios (sec. 5, capa "Contenedores": imagenes sin root).
RUN groupadd -r dentia && useradd -r -g dentia -d /app dentia \
    && mkdir -p /data/storage && chown -R dentia:dentia /app /data
USER dentia

EXPOSE 8001

# --proxy-headers --forwarded-allow-ips='*': seguro aqui porque la red "app"
# de docker-compose.yml es `internal: true` (sin salida a internet) y el
# unico otro contenedor que puede alcanzar a "api" es "caddy" -- no hay forma
# de que una peticion externa llegue directo a este puerto. Caddy es quien ya
# valida el origen real (CF-Connecting-IP, solo detras de Cloudflare).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", \
     "--proxy-headers", "--forwarded-allow-ips=*"]
