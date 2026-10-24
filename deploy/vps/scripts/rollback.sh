#!/usr/bin/env bash
# Revierte a una version anterior (Fase "Publicacion en Hostinger" sec. 13):
# vuelve a las imagenes anteriores y, si hubo migracion desde entonces, baja
# el esquema hasta la revision que esa version esperaba (CLAUDE.md sec. 9:
# todas las migraciones son reversibles).
#
# Uso:
#   sudo ./scripts/rollback.sh <version-anterior> <proyecto>
#   sudo ./scripts/rollback.sh 1.0.0 dentia-prod
#
# Si la migracion de la version actual altero datos (no solo el esquema) y el
# downgrade no basta para recuperarlos, restaurar en su lugar el respaldo
# cifrado mas reciente -- ver scripts/restore-test.sh para probarlo primero.
set -euo pipefail

TARGET_VERSION="${1:?Uso: $0 <version-anterior> <proyecto>}"
PROJECT_NAME="${2:?Uso: $0 <version-anterior> <proyecto>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$SCRIPT_DIR/../compose"
ENV_FILE="$COMPOSE_DIR/.env"

log() { echo "[$(date '+%H:%M:%S')] $*"; }
compose() { docker compose --project-name "$PROJECT_NAME" --project-directory "$COMPOSE_DIR" "$@"; }

GHCR_NAMESPACE="$(grep -E '^GHCR_NAMESPACE=' "$ENV_FILE" | cut -d= -f2)"
TARGET_IMAGE="ghcr.io/${GHCR_NAMESPACE}/dentia-api:${TARGET_VERSION}"

log "1/4 Descargando dentia-api:${TARGET_VERSION} (para conocer el esquema que esperaba)..."
docker pull "$TARGET_IMAGE" >/dev/null

# El esquema de la version anterior es el que describen SUS PROPIOS archivos
# de migracion -- se le pregunta a su propia imagen cual era su "head", en
# vez de asumir un numero de revision a mano.
OLD_HEAD_REVISION=$(docker run --rm --entrypoint python "$TARGET_IMAGE" \
    -m alembic heads 2>/dev/null | awk '{print $1; exit}')
if [ -z "$OLD_HEAD_REVISION" ]; then
    echo "No se pudo determinar la revision de ${TARGET_VERSION}. Revertir el esquema a mano:" >&2
    echo "  sudo ./scripts/backup.sh ${PROJECT_NAME}  # respaldo antes de tocar nada" >&2
    echo "  docker compose ... run --rm api python -m alembic downgrade <revision>" >&2
    exit 1
fi
log "   ${TARGET_VERSION} esperaba el esquema en la revision ${OLD_HEAD_REVISION}."

log "2/4 Bajando el esquema a ${OLD_HEAD_REVISION}..."
compose run --rm --no-deps api python -m alembic downgrade "$OLD_HEAD_REVISION"

sed -i "s/^VERSION=.*/VERSION=${TARGET_VERSION}/" "$ENV_FILE"

log "3/4 Reiniciando con las imagenes de ${TARGET_VERSION}..."
compose pull
compose up -d

log "4/4 Verificando /api/v1/health..."
for _ in $(seq 1 20); do
    if compose exec -T api python -c "
import urllib.request
urllib.request.urlopen('http://127.0.0.1:8001/api/v1/health', timeout=5)
" >/dev/null 2>&1; then
        log "=== Revertido a ${TARGET_VERSION} en ${PROJECT_NAME} ==="
        exit 0
    fi
    sleep 3
done

echo "FALLO: la API no respondio sana tras revertir a ${TARGET_VERSION}." >&2
echo "Ultimo recurso: restaurar el respaldo cifrado mas reciente (restore-test.sh)." >&2
exit 1
