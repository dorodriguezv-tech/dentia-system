# Imagen del frontend: Caddy (con el modulo de rangos de Cloudflare
# compilado) sirviendo el build de Vite como archivos estaticos. Fase
# "Publicacion en Hostinger" sec. 10/10.2 -- contexto de build: raiz del repo.

# --- Etapa 1: compilar el frontend -------------------------------------
FROM node:20-slim AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
# VITE_API_URL y VITE_TURNSTILE_SITE_KEY (si se usa) se fijan en build time --
# ver scripts/ci-build-push.sh, que pasa --build-arg con el dominio real.
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# --- Etapa 2: compilar Caddy con el modulo de rangos de Cloudflare ------
# `trusted_proxies cloudflare` (Caddyfile) necesita este modulo -- sin el,
# habria que listar los rangos de cloudflare.com/ips a mano con
# `trusted_proxies static` y mantenerlos actualizados por separado.
FROM caddy:2-builder AS caddy-build
RUN xcaddy build --with github.com/WeidiDeng/caddy-cloudflare-ip

# --- Etapa 3: imagen final -----------------------------------------------
FROM caddy:2-alpine
# El pipeline escanea la imagen final con Trivy y detiene la publicacion si
# encuentra una CVE CRITICAL -- `caddy:2-alpine` es un tag flotante, asi que
# puede traer paquetes de Alpine ya parchados en el repositorio pero
# todavia no reflejados en la imagen base subida por upstream. Se actualiza
# explicitamente aqui (no depende de cuando upstream vuelva a publicar su
# imagen) para no quedar bloqueados esperando un rebuild ajeno.
RUN apk update && apk upgrade --no-cache
COPY --from=caddy-build /usr/bin/caddy /usr/bin/caddy
COPY --from=frontend-build /app/dist /srv
# El Caddyfile real se monta como volumen de solo lectura (docker-compose.yml)
# -- esta copia es solo para que `caddy run` tenga un archivo valido si se
# ejecuta el contenedor sin ese volumen (p. ej. para depurar).
COPY deploy/vps/compose/Caddyfile /etc/caddy/Caddyfile
