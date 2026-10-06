#!/usr/bin/env bash
# Prueba de restauracion de DentalCare (CLAUDE.md Fase 11): restaura el respaldo mas
# reciente (o uno especifico) en una base de datos TEMPORAL, la verifica y registra
# el resultado. Nunca toca la base de datos real de la aplicacion. Equivalente
# Linux/Mac de scripts/restore_test.ps1 -- ver ahi la descripcion completa.
#
# Crear/borrar una base de datos requiere un rol con CREATEDB (el rol de la
# aplicacion, "dentia", no lo tiene a proposito). Por eso este script necesita
# credenciales de administrador de PostgreSQL, que NUNCA se escriben en un archivo:
# se leen de las variables de entorno estandar de psql/pg_restore justo antes de
# usarlas. Antes de correr este script:
#   export PGPASSWORD='<password del superusuario>'
# (y opcionalmente PGADMIN_USER si no es "postgres", BACKUP_PASSPHRASE si el
# respaldo esta cifrado). La variable solo vive en la sesion de shell actual.
#
# Uso:
#   ./scripts/restore_test.sh [backup_file] [backup_dir] [test_db_name]

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_FILE="${1:-}"
BACKUP_DIR="${2:-$REPO_ROOT/backups}"
TEST_DB_NAME="${3:-dentalcare_restore_test}"
ADMIN_USER="${PGADMIN_USER:-postgres}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$BACKUP_DIR/restore_test.log"
TEMP_DIR="$(mktemp -d)"

log() {
    local line
    line="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$line"
    echo "$line" >> "$LOG_FILE"
}

cleanup() {
    dropdb --host=localhost --username="$ADMIN_USER" --if-exists "$TEST_DB_NAME" 2>/dev/null || true
    log "Base de datos temporal $TEST_DB_NAME eliminada."
    rm -rf "$TEMP_DIR"
    unset PGPASSWORD
}
trap cleanup EXIT

mkdir -p "$BACKUP_DIR"

if [ -z "${PGPASSWORD:-}" ]; then
    echo "Define PGPASSWORD con la contrasena del rol \$ADMIN_USER ($ADMIN_USER) antes de llamar a este script." >&2
    exit 1
fi

RESULT="FAIL"
DETAIL=""

log "=== Iniciando prueba de restauracion $TIMESTAMP ==="

if [ -z "$BACKUP_FILE" ]; then
    BACKUP_FILE="$(find "$BACKUP_DIR" -maxdepth 1 -name 'dentalcare_*_db.dump*' -type f -print0 \
        | xargs -0 ls -t 2>/dev/null | head -n1)"
fi
if [ -z "$BACKUP_FILE" ]; then
    log "ERROR: no hay respaldos en $BACKUP_DIR (dentalcare_*_db.dump*)."
    log "=== Resultado: FAIL -- sin respaldos ==="
    exit 1
fi
log "Respaldo a restaurar: $BACKUP_FILE"

DUMP_TO_RESTORE="$BACKUP_FILE"
if [[ "$BACKUP_FILE" == *.enc ]]; then
    if [ -z "${BACKUP_PASSPHRASE:-}" ]; then
        log "ERROR: el respaldo esta cifrado; define BACKUP_PASSPHRASE."
        exit 1
    fi
    DUMP_TO_RESTORE="$TEMP_DIR/db.dump"
    if ! openssl enc -d -aes-256-cbc -pbkdf2 -pass "pass:$BACKUP_PASSPHRASE" \
        -in "$BACKUP_FILE" -out "$DUMP_TO_RESTORE"; then
        log "ERROR: no se pudo descifrar $BACKUP_FILE (¿passphrase incorrecta?)."
        exit 1
    fi
    log "Descifrado a archivo temporal: $DUMP_TO_RESTORE"
fi

if dropdb --host=localhost --username="$ADMIN_USER" --if-exists "$TEST_DB_NAME" \
    && createdb --host=localhost --username="$ADMIN_USER" "$TEST_DB_NAME"; then
    log "Base de datos temporal creada: $TEST_DB_NAME"
else
    log "ERROR: no se pudo crear la base de datos temporal."
    exit 1
fi

if pg_restore --host=localhost --username="$ADMIN_USER" --dbname="$TEST_DB_NAME" \
    --no-owner --exit-on-error "$DUMP_TO_RESTORE"; then
    log "pg_restore completado sin errores."
else
    log "ERROR: pg_restore fallo."
    log "=== Resultado: FAIL -- pg_restore fallo ==="
    exit 1
fi

VERIFY_OUTPUT="$(psql --host=localhost --username="$ADMIN_USER" --dbname="$TEST_DB_NAME" \
    --tuples-only --no-align --command="select (select count(*) from organizations) as organizations, (select count(*) from clinics) as clinics, (select count(*) from users) as users;")"
log "Verificacion (organizations|clinics|users): $VERIFY_OUTPUT"

STORAGE_ZIP="${BACKUP_FILE/_db.dump/_storage.zip}"
if [ -f "$STORAGE_ZIP" ]; then
    ZIP_TO_EXTRACT="$STORAGE_ZIP"
    if [[ "$STORAGE_ZIP" == *.enc ]]; then
        if [ -n "${BACKUP_PASSPHRASE:-}" ]; then
            ZIP_TO_EXTRACT="$TEMP_DIR/storage.zip"
            openssl enc -d -aes-256-cbc -pbkdf2 -pass "pass:$BACKUP_PASSPHRASE" \
                -in "$STORAGE_ZIP" -out "$ZIP_TO_EXTRACT" || ZIP_TO_EXTRACT=""
        else
            log "ADVERTENCIA: no se pudo descifrar $STORAGE_ZIP para verificarlo (sin BACKUP_PASSPHRASE)."
            ZIP_TO_EXTRACT=""
        fi
    fi
    if [ -n "$ZIP_TO_EXTRACT" ]; then
        EXTRACT_DIR="$TEMP_DIR/storage"
        mkdir -p "$EXTRACT_DIR"
        unzip -q "$ZIP_TO_EXTRACT" -d "$EXTRACT_DIR"
        FILE_COUNT="$(find "$EXTRACT_DIR" -type f | wc -l)"
        log "Archivo de storage/ verificado: $FILE_COUNT archivo(s) extraidos sin error."
    fi
else
    log "No se encontro un .zip de storage/ para este respaldo (puede no haberse generado)."
fi

RESULT="PASS"
DETAIL="organizations/clinics/users: $VERIFY_OUTPUT"
log "=== Resultado: $RESULT -- $DETAIL ==="
