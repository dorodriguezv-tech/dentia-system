#!/usr/bin/env bash
# Fase "Publicacion en Hostinger" sec. 11, paso 7: empaqueta deploy/vps/ como
# dentia-vps-<version>.tar.gz con SHA256SUMS y un release.json que fija los
# digest de las dos imagenes (de ci-build-push.sh) -- release.json es lo que
# install.sh/deploy.sh usan para no tener que confiar en el tag mutable
# "latest" ni volver a resolver el digest despues.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
VERSION="${GITHUB_REF_NAME#v}"
DIST_DIR="$REPO_ROOT/dist"
PKG_NAME="dentia-vps-${VERSION}"

mkdir -p "$DIST_DIR"
# shellcheck disable=SC1091
source "$DIST_DIR/digests.env" # API_DIGEST, WEB_DIGEST (de ci-build-push.sh)

cat > "$REPO_ROOT/deploy/vps/VERSION" <<EOF
${VERSION}
EOF

python3 - "$VERSION" "$API_DIGEST" "$WEB_DIGEST" "$DIST_DIR/release.json" <<'PYEOF'
import json
import sys

version, api_digest, web_digest, out_path = sys.argv[1:5]
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(
        {"version": version, "api_image": api_digest, "web_image": web_digest},
        f,
        indent=2,
    )
    f.write("\n")
PYEOF
cp "$DIST_DIR/release.json" "$REPO_ROOT/deploy/vps/release.json"

tar czf "$DIST_DIR/${PKG_NAME}.tar.gz" -C "$REPO_ROOT/deploy" vps

cd "$DIST_DIR"
sha256sum "${PKG_NAME}.tar.gz" "release.json" > SHA256SUMS

echo "=== ci-package.sh: $DIST_DIR/${PKG_NAME}.tar.gz listo ==="
cat SHA256SUMS
