#!/usr/bin/env bash
# Prueba de restauracion (Fase "Publicacion en Hostinger" sec. 8 y 13):
# descarga el ultimo respaldo de restic, lo restaura en una base de
# verificacion TEMPORAL (nunca pisa la base real) y confirma que tiene tablas
# y filas -- equivalente al restore_test de docs/OPERACION.md, pero contra el
# almacenamiento externo cifrado en vez de un respaldo local.
#
# Uso:
#   sudo ./scripts/restore-test.sh <proyecto>
#
# Requiere /etc/dentia/<proyecto>/secrets/restic.env (ver backup.sh).
set -euo pipefail

PROJECT_NAME="${1:?Uso: $0 <proyecto>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VPS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SECRETS_DIR="/etc/dentia/${PROJECT_NAME}/secrets"
RESTIC_ENV="$SECRETS_DIR/restic.env"
WORK_DIR="$(mktemp -d)"
TEST_DB_CONTAINER="dentia-restore-test-${PROJECT_NAME}"

cleanup() {
    docker rm -f "$TEST_DB_CONTAINER" >/dev/null 2>&1 || true
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [ ! -f "$RESTIC_ENV" ]; then
    echo "Falta $RESTIC_ENV -- ver INSTALACION_VPS.md seccion 'Respaldos'." >&2
    exit 1
fi
# shellcheck disable=SC1090
source "$RESTIC_ENV"

log "=== Prueba de restauracion ${PROJECT_NAME} ==="

LATEST_DUMP=$(restic ls latest --tag "$PROJECT_NAME" 2>/dev/null | grep -E '\.dump$' | tail -1)
if [ -z "$LATEST_DUMP" ]; then
    echo "No se encontro ningun respaldo con el tag '${PROJECT_NAME}' en el repositorio restic." >&2
    exit 1
fi
restic restore latest --tag "$PROJECT_NAME" --target "$WORK_DIR" --include "$LATEST_DUMP"
DUMP_PATH="$WORK_DIR$LATEST_DUMP"
log "Respaldo descargado: $DUMP_PATH"

TEST_DB_PASSWORD="restore-test-$(date +%s)"
docker run -d --name "$TEST_DB_CONTAINER" \
    -e POSTGRES_PASSWORD="$TEST_DB_PASSWORD" -e POSTGRES_DB=dentia_restore_test \
    postgres:16 >/dev/null
log "Base de verificacion temporal arrancada ($TEST_DB_CONTAINER)..."

for _ in $(seq 1 30); do
    if docker exec "$TEST_DB_CONTAINER" pg_isready -U postgres >/dev/null 2>&1; then break; fi
    sleep 1
done

docker cp "$DUMP_PATH" "$TEST_DB_CONTAINER:/tmp/restore.dump"
docker exec "$TEST_DB_CONTAINER" pg_restore -U postgres -d dentia_restore_test --no-owner /tmp/restore.dump

TABLE_COUNT=$(docker exec "$TEST_DB_CONTAINER" psql -U postgres -d dentia_restore_test -tAc \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
PATIENT_COUNT=$(docker exec "$TEST_DB_CONTAINER" psql -U postgres -d dentia_restore_test -tAc \
    "SELECT count(*) FROM patients" 2>/dev/null || echo "0")

log "Tablas restauradas: $TABLE_COUNT"
log "Filas en patients: $PATIENT_COUNT"

if [ "$TABLE_COUNT" -lt 10 ]; then
    echo "FALLO: se esperaban al menos 10 tablas, se restauraron $TABLE_COUNT." >&2
    exit 1
fi

log "=== PASS: la restauracion del ultimo respaldo de ${PROJECT_NAME} es valida ==="
