#!/usr/bin/env bash
# Instalador del paquete dentia-vps (Fase "Publicacion en Hostinger" sec. 10,
# 12). Deja Docker, el firewall DOCKER-USER, los secretos y los servicios de
# systemd listos para desplegar una version con deploy.sh.
#
# REQUISITO PREVIO, hecho a mano por el operador (sec. 4.1, pasos A-D): llave
# SSH, usuario deploy, PermitRootLogin no, puerto SSH no estandar. Este script
# NO toca sshd_config ni crea usuarios del sistema -- cambiar el acceso SSH
# de forma desatendida es demasiado facil de hacer mal y dejar el servidor
# inaccesible; esa parte siempre la hace una persona, a mano, probando en una
# segunda ventana antes de cerrar la original.
#
# Uso (como root o con sudo, en el VPS, parado en deploy/vps):
#   sudo ./scripts/install.sh --domain app.dentia.digital --project dentia-prod \
#     --admin-ip 203.0.113.10 --ssh-port 2222
#
# Es idempotente: se puede correr de nuevo sin duplicar reglas de firewall ni
# regenerar secretos que ya existen.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VPS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DOMAIN=""
PROJECT_NAME=""
ADMIN_IP=""
SSH_PORT="2222"

while [ $# -gt 0 ]; do
    case "$1" in
        --domain) DOMAIN="$2"; shift 2 ;;
        --project) PROJECT_NAME="$2"; shift 2 ;;
        --admin-ip) ADMIN_IP="$2"; shift 2 ;;
        --ssh-port) SSH_PORT="$2"; shift 2 ;;
        *) echo "Argumento desconocido: $1" >&2; exit 1 ;;
    esac
done

if [ -z "$DOMAIN" ] || [ -z "$PROJECT_NAME" ]; then
    echo "Uso: $0 --domain <dominio> --project <nombre> [--admin-ip <ip>] [--ssh-port <puerto>]" >&2
    exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "Corre este script como root (sudo)." >&2
    exit 1
fi

log() { echo "[$(date '+%H:%M:%S')] $*"; }

SECRETS_DIR="/etc/dentia/${PROJECT_NAME}/secrets"
TLS_DIR="/etc/dentia/${PROJECT_NAME}/tls"

# 1. Zona horaria y paquetes base (idempotente: apt/timedatectl no duplican nada).
log "Zona horaria y paquetes base..."
timedatectl set-timezone America/Mexico_City
apt-get update -qq
apt-get install -y -qq ufw fail2ban unattended-upgrades auditd curl ca-certificates jq >/dev/null

# 2. Actualizaciones automaticas con reinicio de madrugada (sec. 4.1, paso F).
if [ ! -f /etc/apt/apt.conf.d/52dentia ]; then
    printf 'Unattended-Upgrade::Automatic-Reboot "true";\nUnattended-Upgrade::Automatic-Reboot-Time "03:30";\n' \
        > /etc/apt/apt.conf.d/52dentia
    log "unattended-upgrades: reinicio automatico 03:30 configurado."
fi
systemctl enable --now fail2ban auditd >/dev/null 2>&1 || true

# 3. ufw: SSH solo desde la IP de administracion (si se dio) -- 443 lo filtra
# DOCKER-USER (paso 5), no ufw, porque Docker publica el puerto por fuera de
# las reglas de ufw.
if [ -n "$ADMIN_IP" ]; then
    ufw allow from "$ADMIN_IP" to any port "$SSH_PORT" proto tcp comment "dentia-admin-ssh" || true
fi
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw --force enable >/dev/null
log "ufw activo: $(ufw status | head -1)"

# 4. Docker Engine (repositorio oficial) -- idempotente: si ya esta instalado
# con la version correcta, apt no hace nada.
if ! command -v docker >/dev/null 2>&1; then
    log "Instalando Docker Engine..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    . /etc/os-release
    tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${VERSION_CODENAME}
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null
    log "Docker instalado: $(docker --version)"
else
    log "Docker ya estaba instalado: $(docker --version)"
fi

# 5. Cadena DOCKER-USER: filtra el 443 que publica Docker (ufw no lo ve) para
# que solo entre trafico de las IPs de Cloudflare -- sec. 4.1, paso E.
install -m 0755 "$VPS_ROOT/scripts/dentia-docker-fw.sh" /usr/local/sbin/dentia-docker-fw.sh
install -m 0644 "$VPS_ROOT/systemd/dentia-docker-fw.service" /etc/systemd/system/dentia-docker-fw.service
systemctl daemon-reload
systemctl enable --now dentia-docker-fw.service
log "Regla DOCKER-USER (solo Cloudflare en 443) instalada y aplicada."

# 6. Secretos: se generan solo si no existen -- nunca se pisan en una
# reinstalacion (perderia el acceso a la base ya cifrada con el anterior).
mkdir -p "$SECRETS_DIR"
chmod 700 "/etc/dentia/${PROJECT_NAME}"
if [ ! -f "$SECRETS_DIR/jwt_secret" ]; then
    python3 -c "import secrets; print(secrets.token_hex(48))" > "$SECRETS_DIR/jwt_secret"
    chmod 600 "$SECRETS_DIR/jwt_secret"
    log "jwt_secret generado."
fi
if [ ! -f "$SECRETS_DIR/db_password" ]; then
    python3 -c "import secrets; print(secrets.token_urlsafe(32))" > "$SECRETS_DIR/db_password"
    chmod 600 "$SECRETS_DIR/db_password"
    log "db_password generado."
fi
chown -R root:root "/etc/dentia/${PROJECT_NAME}"

# 7. Certificado de origen de Cloudflare: el operador ya lo descargo a mano
# (sec. 4.1, paso H.5) y lo copio junto con este paquete -- aqui solo se
# instala con los permisos correctos.
mkdir -p "$TLS_DIR"
for f in origin.pem origin.key cloudflare-origin-pull-ca.pem; do
    if [ -f "$VPS_ROOT/$f" ]; then
        install -m 600 -o root -g root "$VPS_ROOT/$f" "$TLS_DIR/$f"
    elif [ ! -f "$TLS_DIR/$f" ]; then
        echo "ADVERTENCIA: falta $TLS_DIR/$f -- Caddy no arrancara sin el. Copialo desde" \
             "Cloudflare (SSL/TLS -> Origin Server) antes de desplegar." >&2
    fi
done

# 8. Token de lectura de GHCR (para docker pull de las imagenes privadas) --
# se pide una sola vez, interactivo; si ya existe no se vuelve a pedir.
if [ ! -f "$SECRETS_DIR/ghcr_token" ]; then
    read -rsp "Token de GitHub (solo lectura de paquetes, scope read:packages): " GHCR_TOKEN
    echo
    echo "$GHCR_TOKEN" > "$SECRETS_DIR/ghcr_token"
    chmod 600 "$SECRETS_DIR/ghcr_token"
fi

# 9. .env del proyecto (compose/.env): a partir del ejemplo, si no existe ya.
ENV_FILE="$VPS_ROOT/compose/.env"
if [ ! -f "$ENV_FILE" ]; then
    cp "$VPS_ROOT/compose/.env.example" "$ENV_FILE"
    sed -i "s/^DOMAIN=.*/DOMAIN=${DOMAIN}/" "$ENV_FILE"
    sed -i "s/^COMPOSE_PROJECT_NAME=.*/COMPOSE_PROJECT_NAME=${PROJECT_NAME}/" "$ENV_FILE"
    sed -i "s/^PROJECT_NAME=.*/PROJECT_NAME=${PROJECT_NAME}/" "$ENV_FILE"
    log "compose/.env creado para ${DOMAIN} (proyecto ${PROJECT_NAME})."
fi

# 10. Servicios de systemd: arrancan Docker Compose al encender el VPS y el
# respaldo diario (sec. 10, systemd/).
sed -e "s#__VPS_ROOT__#${VPS_ROOT}#g" -e "s#__PROJECT_NAME__#${PROJECT_NAME}#g" \
    "$VPS_ROOT/systemd/dentia.service" > "/etc/systemd/system/dentia@${PROJECT_NAME}.service"
sed -e "s#__VPS_ROOT__#${VPS_ROOT}#g" -e "s#__PROJECT_NAME__#${PROJECT_NAME}#g" \
    "$VPS_ROOT/systemd/dentia-backup.service" > "/etc/systemd/system/dentia-backup@${PROJECT_NAME}.service"
install -m 644 "$VPS_ROOT/systemd/dentia-backup.timer" "/etc/systemd/system/dentia-backup@.timer"
systemctl daemon-reload
systemctl enable "dentia@${PROJECT_NAME}.service"
systemctl enable "dentia-backup@${PROJECT_NAME}.timer"
log "Servicios dentia@${PROJECT_NAME} y dentia-backup@${PROJECT_NAME}.timer habilitados."

echo ""
echo "Instalacion lista para ${DOMAIN} (proyecto ${PROJECT_NAME})."
echo "Siguiente paso: sudo ./scripts/deploy.sh <version> ${PROJECT_NAME}"
