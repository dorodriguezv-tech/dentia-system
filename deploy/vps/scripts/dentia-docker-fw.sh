#!/usr/bin/env bash
# Filtra el puerto 443 que publica Docker (ufw no ve los puertos que Docker
# publica -- los inserta directo en iptables) para que solo acepte conexiones
# de los rangos de IP de Cloudflare. Fase "Publicacion en Hostinger" sec. 4.1,
# paso E.3. Lo ejecuta dentia-docker-fw.service, DESPUES de docker.service
# (si corriera antes, la cadena DOCKER-USER todavia no existiria).
set -euo pipefail

IFACE=$(ip route show default | awk '{print $5; exit}') # normalmente eth0

iptables -N DENTIA-CF 2>/dev/null || iptables -F DENTIA-CF
for r in $(curl -fsS https://www.cloudflare.com/ips-v4); do
    iptables -A DENTIA-CF -s "$r" -j RETURN
done
iptables -A DENTIA-CF -j DROP

iptables -C DOCKER-USER -i "$IFACE" -p tcp -m conntrack --ctorigdstport 443 -j DENTIA-CF 2>/dev/null \
    || iptables -I DOCKER-USER -i "$IFACE" -p tcp -m conntrack --ctorigdstport 443 -j DENTIA-CF
