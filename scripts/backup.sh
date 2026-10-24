#!/usr/bin/env bash
# Respaldo de DentalCare (CLAUDE.md Fase 11): pg_dump de la base de datos + storage/
# (archivos subidos), ambos cifrados si hay OpenSSL disponible, con retencion
# automatica de respaldos antiguos. Equivalente Linux/Mac de scripts/backup.ps1 --
# ver ahi la descripcion completa del formato y del cifrado.
#
# Uso:
#   ./scripts/backup.sh [backup_dir] [retention_days]
#
# Variables de entorno:
#   BACKUP_PASSPHRASE  frase de paso para cifrar con OpenSSL (opcional; sin ella
#                       el respaldo se guarda SIN CIFRAR con una advertencia clara)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${1:-$REPO_ROOT/backups}"
RETENTION_DAYS="${2:-30}"
ENV_FILE="$REPO_ROOT/backend/.env"
STORAGE_DIR="$REPO_ROOT/storage"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$BACKUP_DIR/backup.log"

mkdir -p "$BACKUP_DIR"

log() {
    local line
    line="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$line"
    echo "$line" >> "$LOG_FILE"
}

read_env_value() {
    local key="$1"
    local value
    value="$(grep -E "^\s*${key}\s*=" "$ENV_FILE" | head -n1 | cut -d'=' -f2- | xargs)"
    if [ -z "$value" ]; then
        echo "La variable $key no esta definida en $ENV_FILE" >&2
        exit 1
    fi
    echo "$value"
}

if [ ! -f "$ENV_FILE" ]; then
    echo "No se encontro $ENV_FILE -- copia backend/.env.example a backend/.env primero." >&2
    exit 1
fi

log "=== Iniciando respaldo $TIMESTAMP ==="

PG_USER="$(read_env_value POSTGRES_USER)"
PG_PASSWORD="$(read_env_value POSTGRES_PASSWORD)"
PG_DATABASE="$(read_env_value POSTGRES_DB)"

DB_DUMP_PATH="$BACKUP_DIR/dentalcare_${TIMESTAMP}_db.dump"
STORAGE_ZIP_PATH="$BACKUP_DIR/dentalcare_${TIMESTAMP}_storage.zip"

PGPASSWORD="$PG_PASSWORD" pg_dump --host=localhost --username="$PG_USER" \
    --format=custom --file="$DB_DUMP_PATH" "$PG_DATABASE"
log "Volcado de base de datos creado: $DB_DUMP_PATH ($(stat -c%s "$DB_DUMP_PATH" 2>/dev/null || stat -f%z "$DB_DUMP_PATH") bytes)"

if [ -d "$STORAGE_DIR" ]; then
    (cd "$STORAGE_DIR" && zip -rq "$STORAGE_ZIP_PATH" .)
    log "Archivo de storage/ creado: $STORAGE_ZIP_PATH ($(stat -c%s "$STORAGE_ZIP_PATH" 2>/dev/null || stat -f%z "$STORAGE_ZIP_PATH") bytes)"
else
    log "ADVERTENCIA: $STORAGE_DIR no existe, se omite el respaldo de archivos."
fi

if command -v openssl >/dev/null 2>&1 && [ -n "${BACKUP_PASSPHRASE:-}" ]; then
    for plain_path in "$DB_DUMP_PATH" "$STORAGE_ZIP_PATH"; do
        [ -f "$plain_path" ] || continue
        enc_path="${plain_path}.enc"
        if openssl enc -aes-256-cbc -pbkdf2 -salt -pass "pass:$BACKUP_PASSPHRASE" \
            -in "$plain_path" -out "$enc_path"; then
            rm -f "$plain_path"
            log "Cifrado: $enc_path"
        else
            log "ADVERTENCIA: fallo el cifrado de $plain_path, se conserva sin cifrar."
        fi
    done
else
    if ! command -v openssl >/dev/null 2>&1; then
        reason="no se encontro OpenSSL"
    else
        reason="falta la variable de entorno BACKUP_PASSPHRASE"
    fi
    log "ADVERTENCIA: respaldo guardado SIN CIFRAR ($reason). Ver docs/OPERACION.md seccion de cifrado."
fi

removed=0
while IFS= read -r -d '' old_file; do
    rm -f "$old_file"
    removed=$((removed + 1))
done < <(find "$BACKUP_DIR" -maxdepth 1 -name "dentalcare_*" -type f -mtime "+${RETENTION_DAYS}" -print0)
if [ "$removed" -gt 0 ]; then
    log "Retencion: $removed archivo(s) de mas de $RETENTION_DAYS dias eliminado(s)."
fi

log "=== Respaldo $TIMESTAMP terminado ==="
