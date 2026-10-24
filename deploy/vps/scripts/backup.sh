#!/usr/bin/env bash
# Respaldo diario cifrado (Fase "Publicacion en Hostinger" sec. 8 y 10):
# pg_dump de la base + storage/, subidos cifrados (restic, AES-256) a un
# almacenamiento externo (Backblaze B2 o Google Cloud Storage). Lo corre
# dentia-backup@<proyecto>.service (systemd timer, 2:00 a.m.) o a mano:
#
#   sudo ./scripts/backup.sh <proyecto>
#
# Requiere /etc/dentia/<proyecto>/secrets/restic.env (creado a mano una sola
# vez, NUNCA versionado -- ver INSTALACION_VPS.md "Respaldos"):
#   RESTIC_REPOSITORY=b2:nombre-del-bucket:dentia-prod
#   RESTIC_PASSWORD=<frase de paso, guardada aparte en un gestor de contrasenas>
#   B2_ACCOUNT_ID=... / B2_ACCOUNT_KEY=...   (o las variables del proveedor elegido)
#   HEALTHCHECK_URL=https://hc-ping.com/<uuid>   (opcional, avisa si el respaldo falla)
set -euo pipefail

PROJECT_NAME="${1:?Uso: $0 <proyecto>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VPS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SECRETS_DIR="/etc/dentia/${PROJECT_NAME}/secrets"
RESTIC_ENV="$SECRETS_DIR/restic.env"
WORK_DIR="$(mktemp -d)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

cleanup() { rm -rf "$WORK_DIR"; }
trap cleanup EXIT

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [ ! -f "$RESTIC_ENV" ]; then
    echo "Falta $RESTIC_ENV -- ver INSTALACION_VPS.md seccion 'Respaldos'." >&2
    exit 1
fi
# shellcheck disable=SC1090
source "$RESTIC_ENV"

if ! command -v restic >/dev/null 2>&1; then
    echo "Falta restic. Instalar: sudo apt-get install -y restic" >&2
    exit 1
fi

log "=== Respaldo ${PROJECT_NAME} ${TIMESTAMP} ==="

DB_PASSWORD="$(cat "$SECRETS_DIR/db_password")"
DB_DUMP="$WORK_DIR/dentia_${TIMESTAMP}.dump"

docker compose --project-name "$PROJECT_NAME" --project-directory "$VPS_ROOT/compose" \
    exec -T -e PGPASSWORD="$DB_PASSWORD" db \
    pg_dump -U dentia -d dentia --format=custom --file=/tmp/backup.dump
docker compose --project-name "$PROJECT_NAME" --project-directory "$VPS_ROOT/compose" \
    cp "db:/tmp/backup.dump" "$DB_DUMP"
docker compose --project-name "$PROJECT_NAME" --project-directory "$VPS_ROOT/compose" \
    exec -T db rm -f /tmp/backup.dump
log "pg_dump: $DB_DUMP ($(stat -c%s "$DB_DUMP") bytes)"

STORAGE_TAR="$WORK_DIR/storage_${TIMESTAMP}.tar.gz"
docker run --rm \
    -v "${PROJECT_NAME}_storage:/data:ro" \
    -v "$WORK_DIR:/backup" \
    alpine:3.20 tar czf "/backup/storage_${TIMESTAMP}.tar.gz" -C /data .
log "storage/: $STORAGE_TAR ($(stat -c%s "$STORAGE_TAR") bytes)"

restic snapshots >/dev/null 2>&1 || restic init
restic backup "$DB_DUMP" "$STORAGE_TAR" --tag "$PROJECT_NAME"
restic forget --keep-daily 30 --keep-monthly 12 --prune --tag "$PROJECT_NAME"
log "Subido y cifrado con restic; retencion aplicada (30 diarios, 12 mensuales)."

if [ -n "${HEALTHCHECK_URL:-}" ]; then
    curl -fsS -m 10 --retry 3 "$HEALTHCHECK_URL" >/dev/null 2>&1 \
        && log "Heartbeat enviado a Healthchecks.io." \
        || log "ADVERTENCIA: no se pudo avisar al heartbeat (el respaldo si se hizo)."
fi

log "=== Respaldo ${PROJECT_NAME} ${TIMESTAMP} terminado ==="
