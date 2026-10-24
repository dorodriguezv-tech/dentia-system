#!/usr/bin/env bash
# Alta del primer administrador (Fase "Publicacion en Hostinger" sec. 10/12,
# paso 5): envoltorio delgado sobre python -m app.create_admin, corrido
# DENTRO del contenedor de la API ya desplegado (mismo codigo/entorno que la
# API en produccion, sin necesitar Python en el host).
#
# Uso:
#   sudo ./scripts/create-admin.sh <proyecto> <correo-del-administrador>
#   sudo ./scripts/create-admin.sh dentia-demo admin@dentia.digital
#
# Interactivo: pide la contrasena sin mostrarla en pantalla (la valida contra
# la politica de la sec. 5.1/6 antes de aceptarla). En demo se puede correr
# ademas "docker compose ... run --rm api python -m app.seed" para datos
# ficticios; en produccion NUNCA.
set -euo pipefail

PROJECT_NAME="${1:?Uso: $0 <proyecto> <correo>}"
EMAIL="${2:?Uso: $0 <proyecto> <correo>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$SCRIPT_DIR/../compose"
ENV_FILE="$COMPOSE_DIR/.env"

DOMAIN="$(grep -E '^DOMAIN=' "$ENV_FILE" | cut -d= -f2)"
CLINIC_NAME="${CLINIC_NAME:-$DOMAIN}"

# Sin --no-deps: ver el comentario equivalente en deploy.sh (deja que
# depends_on arranque "db" solo si hiciera falta).
docker compose --project-name "$PROJECT_NAME" --project-directory "$COMPOSE_DIR" \
    run --rm api python -m app.create_admin \
    --clinic-name "$CLINIC_NAME" --email "$EMAIL"
