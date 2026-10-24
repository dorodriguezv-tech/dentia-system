#!/usr/bin/env bash
# Fase "Publicacion en Hostinger" sec. 11, pasos 3-6: construye las imagenes,
# las escanea con Trivy, las publica en GHCR y las firma con cosign (firma
# "keyless", via el OIDC de GitHub Actions -- sin llaves que administrar).
# Corre en GitHub Actions, despues de ci-test.sh; requiere GITHUB_TOKEN (ya
# disponible en el job) y estar autenticado contra ghcr.io.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
VERSION="${GITHUB_REF_NAME#v}" # el workflow dispara con tags "v*"
GHCR_NAMESPACE="${GHCR_NAMESPACE:?Falta GHCR_NAMESPACE}"
API_IMAGE="ghcr.io/${GHCR_NAMESPACE}/dentia-api"
WEB_IMAGE="ghcr.io/${GHCR_NAMESPACE}/dentia-web"

echo "=== Construyendo ${API_IMAGE}:${VERSION} ==="
docker build -f "$REPO_ROOT/deploy/vps/images/api.Dockerfile" -t "${API_IMAGE}:${VERSION}" "$REPO_ROOT"

echo "=== Construyendo ${WEB_IMAGE}:${VERSION} ==="
docker build -f "$REPO_ROOT/deploy/vps/images/web.Dockerfile" \
    --build-arg "VITE_API_URL=https://\${DOMAIN}/api/v1" \
    -t "${WEB_IMAGE}:${VERSION}" "$REPO_ROOT"

echo "=== Escaneando con Trivy (vulnerabilidades CRITICAL detienen la publicacion) ==="
trivy image --exit-code 1 --severity CRITICAL --ignore-unfixed "${API_IMAGE}:${VERSION}"
trivy image --exit-code 1 --severity CRITICAL --ignore-unfixed "${WEB_IMAGE}:${VERSION}"

echo "=== Publicando en GHCR ==="
docker push "${API_IMAGE}:${VERSION}"
docker push "${WEB_IMAGE}:${VERSION}"

API_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "${API_IMAGE}:${VERSION}")
WEB_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "${WEB_IMAGE}:${VERSION}")

echo "=== Firmando por digest (cosign, keyless via OIDC) ==="
cosign sign --yes "$API_DIGEST"
cosign sign --yes "$WEB_DIGEST"

echo "=== Generando SBOM ==="
mkdir -p "$REPO_ROOT/dist"
trivy image --format cyclonedx --output "$REPO_ROOT/dist/dentia-api-${VERSION}.sbom.json" "${API_IMAGE}:${VERSION}"
trivy image --format cyclonedx --output "$REPO_ROOT/dist/dentia-web-${VERSION}.sbom.json" "${WEB_IMAGE}:${VERSION}"

echo "API_DIGEST=${API_DIGEST}" >> "$REPO_ROOT/dist/digests.env"
echo "WEB_DIGEST=${WEB_DIGEST}" >> "$REPO_ROOT/dist/digests.env"

echo "=== ci-build-push.sh: ${API_IMAGE}:${VERSION} y ${WEB_IMAGE}:${VERSION} publicadas y firmadas ==="
