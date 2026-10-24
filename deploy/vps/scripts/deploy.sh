#!/usr/bin/env bash
# Despliega una version (Fase "Publicacion en Hostinger" sec. 12/13): respaldo
# inmediato, descarga y verifica las imagenes firmadas, aplica las
# migraciones y reinicia la API y Caddy.
#
# Uso:
#   sudo ./scripts/deploy.sh <version> <proyecto>
#   sudo ./scripts/deploy.sh 1.1.0 dentia-prod
set -euo pipefail

VERSION="${1:?Uso: $0 <version> <proyecto>}"
PROJECT_NAME="${2:?Uso: $0 <version> <proyecto>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VPS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_DIR="$VPS_ROOT/compose"
SECRETS_DIR="/etc/dentia/${PROJECT_NAME}/secrets"
ENV_FILE="$COMPOSE_DIR/.env"

log() { echo "[$(date '+%H:%M:%S')] $*"; }
compose() { docker compose --project-name "$PROJECT_NAME" --project-directory "$COMPOSE_DIR" "$@"; }

if [ ! -f "$ENV_FILE" ]; then
    echo "Falta $ENV_FILE -- corre install.sh primero." >&2
    exit 1
fi
GHCR_NAMESPACE="$(grep -E '^GHCR_NAMESPACE=' "$ENV_FILE" | cut -d= -f2)"

log "1/6 Respaldo inmediato antes de actualizar..."
if [ ! -f "$SECRETS_DIR/restic.env" ]; then
    log "   ADVERTENCIA: no existe $SECRETS_DIR/restic.env -- se omite el respaldo." \
        "Configurarlo (sec. 'Respaldos' de INSTALACION_VPS.md) antes de cargar datos" \
        "reales: sin esto, un fallo del servidor pierde todo lo que haya en esta" \
        "instalacion sin forma de recuperarlo."
elif [ -n "$(compose ps -q)" ]; then
    "$SCRIPT_DIR/backup.sh" "$PROJECT_NAME"
else
    log "   Primer despliegue (todavia no hay contenedores de ${PROJECT_NAME}) -- nada que" \
        "respaldar, se omite."
fi

log "2/6 Autenticando con GitHub Container Registry..."
if ! cat "$SECRETS_DIR/ghcr_token" | docker login ghcr.io -u "$GHCR_NAMESPACE" --password-stdin; then
    log "   ADVERTENCIA: no se pudo autenticar con GHCR. Si dentia-api/dentia-web son" \
        "publicas esto no importa -- el docker pull de abajo funciona igual sin login;" \
        "si son privadas, ese paso fallara a continuacion con un error claro."
fi

log "3/6 Descargando dentia-api:${VERSION} y dentia-web:${VERSION}..."
docker pull "ghcr.io/${GHCR_NAMESPACE}/dentia-api:${VERSION}"
docker pull "ghcr.io/${GHCR_NAMESPACE}/dentia-web:${VERSION}"

if command -v cosign >/dev/null 2>&1; then
    log "   Verificando firma (cosign)..."
    cosign verify --certificate-identity-regexp "https://github.com/" \
        --certificate-oidc-issuer https://token.actions.githubusercontent.com \
        "ghcr.io/${GHCR_NAMESPACE}/dentia-api:${VERSION}" >/dev/null
    cosign verify --certificate-identity-regexp "https://github.com/" \
        --certificate-oidc-issuer https://token.actions.githubusercontent.com \
        "ghcr.io/${GHCR_NAMESPACE}/dentia-web:${VERSION}" >/dev/null
    log "   Firma verificada."
else
    echo "ADVERTENCIA: cosign no esta instalado -- no se pudo verificar la firma de las" \
         "imagenes. Instalar: https://docs.sigstore.dev/cosign/installation" >&2
fi

sed -i "s/^VERSION=.*/VERSION=${VERSION}/" "$ENV_FILE"

log "4/6 Aplicando migraciones (alembic upgrade head)..."
# Sin --no-deps a proposito: en el primer despliegue "db" todavia no esta
# corriendo, y el depends_on (service_healthy) de docker-compose.yml es
# justo lo que lo arranca y espera a que este listo antes de migrar.
compose run --rm api python -m alembic upgrade head

log "5/6 Reiniciando la API y Caddy..."
compose up -d

log "6/6 Verificando /api/v1/health..."
for _ in $(seq 1 20); do
    if compose exec -T api python -c "
import urllib.request
urllib.request.urlopen('http://127.0.0.1:8001/api/v1/health', timeout=5)
" >/dev/null 2>&1; then
        log "=== Desplegado ${VERSION} en ${PROJECT_NAME} ==="
        exit 0
    fi
    sleep 3
done

echo "FALLO: la API no respondio sana tras desplegar ${VERSION}." >&2
echo "Para revertir: sudo ./scripts/rollback.sh <version-anterior> ${PROJECT_NAME}" >&2
exit 1
