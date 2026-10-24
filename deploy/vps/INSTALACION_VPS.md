# DENT-IA en Hostinger — guía del paquete `dentia-vps`

Guía operativa para instalar, actualizar y operar DENT-IA en el VPS de
Hostinger (`srv2091418`, `179.236.83.142`, Ubuntu 26.04), dominio
`dentia.digital`, usando este paquete. Basada en
`docs/DENT-IA — Instalación segura en la nube (2).pdf` (@omar, 23-oct-2026);
aquí se documenta en detalle lo que ya quedó automatizado en los scripts y
los pasos manuales que le corresponden a una persona.

**No se cargan pacientes reales hasta terminar el checklist de la
sección 14.** Primero se instala `demo.dentia.digital` con datos ficticios,
se recorre el checklist completo ahí, y solo entonces se repite para
`app.dentia.digital`.

## Dónde se ejecuta cada cosa — leer esto primero

Esta guía mezcla comandos que corren en **tres computadoras distintas** y
pasos que se hacen en **páginas web**. Cada bloque de comandos de aquí en
adelante empieza con una etiqueta en negritas que dice exactamente dónde:

| Etiqueta | Qué es | Cómo se ve |
|---|---|---|
| **Tu computadora (PowerShell)** | La PC Windows donde tienes instalado y abierto este proyecto (donde está Claude Code ahora mismo). Se abre con la app "Windows PowerShell" o la terminal de este editor. | `PS C:\workspace\dentia-system>` |
| **Dentro del servidor (sesión SSH)** | El VPS de Hostinger, **después** de haber corrido `ssh -p 2222 deploy@179.236.83.142` desde tu PowerShell y haber entrado. Es una computadora Linux (Ubuntu) distinta a la tuya — todo lo que escribas aquí se ejecuta allá, no en tu PC. | `deploy@srv2091418:~$` |
| **Panel web — hPanel** | El panel de administración de Hostinger, en tu navegador: `hpanel.hostinger.com` | — |
| **Panel web — Cloudflare** | El panel de Cloudflare, en tu navegador: `dash.cloudflare.com` | — |
| **Panel web — GitHub** | GitHub, en tu navegador: `github.com` | — |
| **Dentro de DENT-IA** | La propia aplicación, ya con sesión iniciada como `admin_clinica`, en `https://demo.dentia.digital` o `https://app.dentia.digital` | — |

**Cómo saber en qué computadora estás en un momento dado:** cuando corres
`ssh -p 2222 deploy@179.236.83.142` desde tu PowerShell, tu terminal
**cambia de computadora** — deja de estar en tu PC y pasa a estar "dentro"
del servidor, aunque la ventana sea la misma. Se nota porque el *prompt*
(el texto antes del cursor) cambia de algo como `PS C:\...>` a algo como
`deploy@srv2091418:~$`. Para volver a tu PC, escribe `exit` y presiona
Enter — el prompt vuelve a verse como el de PowerShell.

> **Nota para quien use Git Bash en vez de PowerShell:** los comandos
> `ssh`, `scp`, `tar`, `gh` funcionan igual en ambos. Donde se indica un
> comando específico de PowerShell (como `Get-FileHash`), Git Bash tiene su
> propio equivalente de Linux (`sha256sum`) que también funciona — se
> menciona como alternativa en cada caso.

---

## Índice

0. [Fundamentos ya completados](#0-fundamentos-ya-completados)
1. [Arquitectura](#1-arquitectura)
2. [Capas de seguridad](#2-capas-de-seguridad)
3. [Primera instalación — demo](#3-primera-instalación--demo)
4. [Primera instalación — producción](#4-primera-instalación--producción)
5. [Respaldos](#5-respaldos)
6. [Monitoreo y alertas](#6-monitoreo-y-alertas)
7. [Actualizar una versión](#7-actualizar-una-versión)
8. [Revertir una actualización](#8-revertir-una-actualización)
9. [Comandos del día a día](#9-comandos-del-día-a-día)
10. [Respuesta a incidentes](#10-respuesta-a-incidentes)
11. [Mantenimiento mensual](#11-mantenimiento-mensual)
12. [Costo mensual estimado](#12-costo-mensual-estimado)
13. [Cumplimiento normativo en México](#13-cumplimiento-normativo-en-méxico)
14. [Checklist final de salida a producción](#14-checklist-final-de-salida-a-producción)

---

## 0. Fundamentos ya completados

Estos cinco puntos (PDF sec. 4 y 4.1, pasos A-D y H) **ya están hechos**,
confirmados tal cual los describe el documento. Se listan aquí para que
quede constancia de qué protege al servidor desde antes de que este paquete
toque nada, y con el comando de verificación de cada uno — si algún día algo
deja de funcionar, esto dice qué revisar primero.

Las verificaciones de la tabla se corren **en tu computadora (PowerShell)**,
no dentro del servidor — es justamente lo que confirma que, desde afuera,
el servidor se comporta como debe.

| # | Qué quedó hecho | Verificación (PowerShell, en tu PC) |
|---|---|---|
| 1 | Llave SSH del administrador agregada en hPanel; usuario `deploy` con `sudo` creado en el servidor | `ssh -p 2222 deploy@179.236.83.142 "sudo whoami"` → responde `root` |
| 2 | `sshd` endurecido: `PermitRootLogin no`, `PasswordAuthentication no`, solo el usuario `deploy`, puerto `2222` | `ssh root@179.236.83.142` **debe fallar**; `ssh -p 22 deploy@179.236.83.142` **debe fallar**; `ssh -p 2222 deploy@179.236.83.142` **debe entrar** |
| 3 | Firewall de hPanel (`dentia-fw`): TCP 2222 solo desde la IP del administrador, TCP 443 solo desde los rangos de Cloudflare, todo lo demás descartado | **Panel web — hPanel**: VPS → Seguridad → Firewall → confirmar que `dentia-fw` está **activo** |
| 4 | Dominio `dentia.digital` con nameservers de Cloudflare, DNSSEC activo, bloqueo de transferencia | `Resolve-DnsName -Name dentia.digital -Type NS` → muestra nameservers `*.ns.cloudflare.com` |
| 5 | Certificado de origen de Cloudflare (`origin.pem`, `origin.key`, `cloudflare-origin-pull-ca.pem`) generado y disponible para copiar al servidor | Los tres archivos existen en tu computadora (o en el gestor de contraseñas), listos para copiarlos en la sección 3 |

Dado por completado: **no hace falta repetir nada de esto** antes de seguir.
Si en algún momento una de estas verificaciones falla, ese es el punto a
corregir antes de continuar — los pasos de abajo asumen que las cinco siguen
en pie.

> **Hallazgo real (24-oct-2026), por si el servidor se reaprovisiona algún
> día:** el punto 2 de la tabla estaba marcado como completado, pero
> `PasswordAuthentication` seguía efectivamente en `yes` en la práctica, por
> dos causas independientes:
> 1. `/etc/ssh/sshd_config.d/50-cloud-init.conf` (artefacto del
>    aprovisionamiento inicial del VPS) forzaba `PasswordAuthentication yes`
>    con más prioridad que cualquier otro archivo de configuración — en
>    OpenSSH, dentro de un mismo `Include`, el archivo que se procesa
>    **primero** (orden alfabético) es el que vale para cada directiva; los
>    que vienen después se ignoran silenciosamente para esa misma directiva.
>    Se eliminó ese archivo.
> 2. `/home/deploy/.ssh/authorized_keys` era propiedad de `root:root`.
>    `sshd` lee ese archivo actuando **temporalmente como el propio usuario**
>    (protección estándar para que un proceso root no pueda ser engañado a
>    leer archivos arbitrarios) — con ese propietario, `deploy` no podía leer
>    su propia llave autorizada, así que la autenticación por llave fallaba
>    siempre y caía a contraseña sin ningún aviso explícito en los logs
>    normales (solo aparece con `LogLevel DEBUG3`). Se corrigió con
>    `chown -R deploy:deploy ~/.ssh && chmod 700 ~/.ssh && chmod 600
>    ~/.ssh/authorized_keys` — el patrón estándar correcto.
>
> La verificación de la tabla (`ssh -p 2222 deploy@...` debe entrar,
> probar) no detecta este problema porque usa `ssh` por defecto, que
> intenta la llave y, si falla, cae a contraseña sin que el usuario lo
> note. Para detectar esto en una reinstalación futura, forzar sin llave:
> `ssh -p 2222 -o PubkeyAuthentication=no -o BatchMode=yes deploy@<ip> echo ok`
> — debe fallar con `Permission denied (publickey)`, nunca pedir
> contraseña.

> **Nota sobre `<TU_IP>`:** en los comandos de este documento, `<TU_IP>` es
> la IP pública de donde te conectas en ese momento (oficina o casa del
> administrador) — se usa en comandos que corren **en tu computadora** o
> **dentro del servidor** (nunca es una IP del servidor mismo). Para
> averiguarla, **en tu computadora (PowerShell)**:
> ```powershell
> (Invoke-WebRequest -Uri "https://ifconfig.me/ip" -UseBasicParsing).Content.Trim()
> ```
> o, más simple, abre `https://ifconfig.me` en el navegador y copia el
> número que muestra. No es un valor fijo: si cambias de red (otra oficina,
> otro ISP, datos móviles), el firewall de hPanel y las reglas de `ufw` que
> usan `<TU_IP>` dejan de reconocerte hasta que se actualicen con la IP
> nueva.

---

## 1. Arquitectura

```
Internet
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ Cloudflare (plan Free) — app.dentia.digital              │
│ WAF, límite de login, protección DDoS, IP del VPS oculta │
└─────────────────────────────────────────────────────────┘
  │ HTTPS (Full strict, Authenticated Origin Pulls)
  ▼
┌─────────────────────────────────────────────────────────┐
│ Firewall de hPanel: solo 443 (desde Cloudflare) y        │
│ 2222 (desde <TU_IP>) — todo lo demás descartado          │
└─────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ VPS Hostinger KVM 2 · srv2091418 · Ubuntu 26.04           │
│                                                            │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Cadena DOCKER-USER (iptables): 443 solo desde      │   │
│  │ rangos IPv4 de Cloudflare -- Docker publica ese    │   │
│  │ puerto por fuera de ufw, por eso esta capa extra   │   │
│  └──────────────────────────────────────────────────┘    │
│                        │                                  │
│  ┌─────────────────────▼────────────────────────────┐    │
│  │ Contenedores Docker (red "edge")                  │    │
│  │                                                     │   │
│  │  Caddy :443 ── TLS de origen, frontend, /api       │   │
│  │       │                                             │  │
│  │  ┌────▼──────────────────────────────────────┐    │   │
│  │  │ red "app" (internal: true, SIN salida a    │    │   │
│  │  │ internet)                                   │    │  │
│  │  │                                              │    │  │
│  │  │   API FastAPI :8001 ──► PostgreSQL 16        │    │  │
│  │  │   (sin puerto publicado, nunca en "ports:")  │    │  │
│  │  │                                              │    │  │
│  │  │   Volumen storage/ (imágenes, PDF firmados)  │    │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────┘  │
│                        │                                   │
│         scripts/backup.sh (diario, 2:00 a.m.)               │
└────────────────────────┼────────────────────────────────┘
                          ▼
              ┌───────────────────────────┐
              │ Backblaze B2 / GCS         │
              │ Respaldo cifrado (restic)  │
              │ + Object Lock 30 días      │
              └───────────────────────────┘
```

**Todo el tráfico entra por Cloudflare.** La API y PostgreSQL viven en la
red `app`, marcada `internal: true` en `docker-compose.yml`: no tiene salida
a internet, así que si alguien comprometiera la API no podría abrir una
conexión hacia afuera desde ese contenedor (exfiltrar datos, descargar
herramientas, etc.). El único puerto publicado hacia la red es el 443 de
Caddy, y ni siquiera ese es alcanzable directamente — la cadena
`DOCKER-USER` lo filtra a solo los rangos de IP de Cloudflare.

El agente de IA por voz (Dentia) y la app móvil **no se instalan** en esta
fase — `AI_ENABLED=false` en `docker-compose.yml` y Caddy responde 404 en
`/api/v1/ai/*` sin siquiera llegar a la API.

---

## 2. Capas de seguridad

Resumen de qué protege cada capa y dónde se configura — útil para saber
dónde mirar si algo falla o si se necesita ajustar un control:

| Capa | Medida | Dónde se configura |
|---|---|---|
| Perímetro | HTTPS obligatorio (TLS 1.2+), WAF con reglas administradas, límite de login por IP, protección DDoS, IP del servidor oculta | **Panel web — Cloudflare** |
| Perímetro | Bloqueo o desafío de tráfico fuera de México; `demo` solo desde la IP de la oficina | **Panel web — Cloudflare** (WAF, reglas personalizadas) |
| Origen | Certificado de origen + Authenticated Origin Pulls: el servidor rechaza conexiones que no vengan de Cloudflare | Cloudflare + Caddy (dentro del servidor) |
| Red | Solo 443 desde IPs de Cloudflare y SSH desde `<TU_IP>`; todo lo demás bloqueado, en **dos** capas independientes | **Panel web — hPanel** (firewall) + dentro del servidor (cadena `DOCKER-USER`) |
| Red interna | PostgreSQL y la API solo en la red interna de Docker; ningún puerto publicado excepto el 443 de Caddy | `docker-compose.yml`, dentro del servidor |
| Acceso de administración | Llave SSH, sin contraseña ni root, `fail2ban`, puerto no estándar; 2FA en hPanel y Cloudflare | Dentro del servidor + paneles web |
| Sistema operativo | Ubuntu 26.04 LTS mínimo, parches de seguridad automáticos (`unattended-upgrades`), `auditd`, escáner de malware de hPanel | Dentro del servidor + **panel web — hPanel** |
| Contenedores | Imágenes sin root, sistema de archivos de solo lectura, `no-new-privileges`, sin capacidades extra, límites de memoria | `docker-compose.yml`, dentro del servidor |
| Secretos | `JWT_SECRET`, contraseña de BD y certificado de origen como *Docker secrets*/bind mounts en archivos `644` propiedad de root (legibles por el contenedor sin privilegios que los usa; `docker compose`, a diferencia de Swarm, monta el archivo del host tal cual, sin volver a asignarle permisos), fuera del repositorio. El directorio que los contiene (`700`, solo root) es lo que impide que otros usuarios del host los lean; `ghcr_token` y `restic.env` (que solo lee el host, nunca un contenedor) siguen en `600` | Dentro del servidor (`/etc/dentia/<proyecto>/secrets/`) |
| Base de datos | PostgreSQL 16, `scram-sha-256`, sin puerto publicado, `pg_dump` cifrado diario | Contenedor `db`, dentro del servidor |
| Cifrado en reposo | Respaldos cifrados con `restic` (AES-256) antes de salir del servidor | Dentro del servidor (`scripts/backup.sh`) |
| Aplicación | Política de contraseñas robustas (mín. 12 caracteres, rechazo de comunes), límite de 5 intentos/15 min por correo + 10/min por IP en Cloudflare, `/docs` apagado, auditoría append-only | DENT-IA (ya implementado) + **panel web — Cloudflare** |

**Decisión del proyecto: sin doble autenticación (MFA).** DENT-IA se publica
solo con usuario y contraseña. El riesgo se compensa con las capas de arriba
(sobre todo: política de contraseñas fuerte, límite de intentos en dos
niveles, y restricción geográfica). La MFA se puede reactivar en cualquier
momento en el código (`MFA_ENABLED = True` en
`backend/app/modules/iam/rules.py`, editado **en tu computadora** y
publicado como una versión nueva — sección 7) sin tocar la base de datos.

**Limitaciones de un VPS que se aceptan conscientemente:** el proveedor
(Hostinger) tiene acceso físico al disco — por eso los respaldos van
cifrados. No hay alta disponibilidad automática: si el servidor falla, se
restaura en uno nuevo (objetivo: menos de 4 horas, ver sección 10). Los
parches de PostgreSQL y Docker los aplica el operador, no un proveedor
administrado.

---

## 3. Primera instalación — demo

> **Requisito previo — debe existir un release real en GitHub.** Este
> paquete (`dentia-vps-1.0.0.tar.gz`) no se descarga de la nada: lo publica
> `.github/workflows/release.yml` cuando se crea una etiqueta de git y el
> *pipeline* de pruebas termina en verde (ver sección 7 para el detalle del
> procedimiento). Si nunca se ha publicado nada todavía:
>
> **Tu computadora (PowerShell)**, parado dentro de la carpeta del
> repositorio clonado:
> ```powershell
> cd C:\workspace\dentia-system
> git remote -v   # si no muestra nada, el repo aun no esta conectado a GitHub
> ```
> Si no hay remoto: crear el repositorio vacío en
> **panel web — GitHub** (`github.com/new`, bajo la cuenta
> `dorodriguezv-tech`) y conectarlo.
>
> **Antes de cualquier `git push` a GitHub**, autenticar la terminal — GitHub
> ya no acepta usuario/contraseña para operaciones de git (el error
> `Invalid username or token. Password authentication is not supported`
> significa exactamente eso: algo intentó usar una contraseña en vez de un
> token). La forma más simple, con `gh` ya instalado:
> ```powershell
> gh auth login
> ```
> Elegir: `GitHub.com` → `HTTPS` → `Login with a web browser` (abre el
> navegador, pides el código que te muestra la terminal, y confirmas ahí).
> Cuando pregunte *"Authenticate Git with your GitHub credentials?"*,
> responder **Yes** — eso configura el *credential helper* de `gh` para que
> `git push`/`git pull` normales, de ahí en adelante, nunca vuelvan a pedir
> usuario ni contraseña. Si ya habías hecho `gh auth login` antes mismo sin
> ese paso, basta con:
> ```powershell
> gh auth setup-git
> ```
>
> Ahora sí, conectar el remoto y publicar:
> ```powershell
> git remote add origin https://github.com/dorodriguezv-tech/dentia-system.git
> git push -u origin main
> git tag v1.0.0
> git push --tags
> ```
> Esperar a que el *workflow* termine en verde — **panel web — GitHub**:
> pestaña "Actions" del repositorio. Solo entonces existe un release
> `v1.0.0` real para descargar con el paso 3.1 de abajo.

### 3.1 Descargar, verificar y copiar el paquete al servidor

**Tu computadora (PowerShell)** — puede ser cualquier carpeta donde tengas
permisos de escritura normales (tu usuario, no una carpeta de Windows);
**nunca una ventana de PowerShell "Ejecutar como administrador"**, que por
defecto arranca en `C:\Windows\System32` y no te pertenece — si ya tienes
una así abierta, cierra esa y abre una normal (sin "Ejecutar como
administrador"), o simplemente cambia de carpeta primero:

```powershell
cd $env:USERPROFILE\Downloads
```

Descargar el paquete, indicando el repositorio explícitamente con `--repo`
para que el comando funcione sin importar en qué carpeta estés parado:

```powershell
gh release download v1.0.0 --repo dorodriguezv-tech/dentia-system `
    -p 'dentia-vps-1.0.0.tar.gz' -p 'SHA256SUMS'
```

```powershell
# Verificar que el archivo no se corrompio ni fue alterado (compara el hash
# con el que esta en SHA256SUMS):
Get-FileHash .\dentia-vps-1.0.0.tar.gz -Algorithm SHA256
Get-Content .\SHA256SUMS
# El primer valor (Hash) debe coincidir, letra por letra (sin importar
# mayusculas/minusculas), con el que aparece junto al nombre del archivo en
# SHA256SUMS. Si tienes Git Bash, el equivalente de un solo comando es:
#   sha256sum -c SHA256SUMS
```

> **Si el error de este paso fue "detected dubious ownership in
> repository..."**: significa que PowerShell estaba parado en una carpeta
> que no te pertenece (típicamente `C:\Windows\System32`, el valor por
> defecto de una ventana abierta como administrador). La solución es
> cambiar a una carpeta normal tuya (`cd $env:USERPROFILE\Downloads`, como
> arriba) — **no** hace falta (ni conviene) correr el
> `git config --global --add safe.directory ...` que sugiere el mensaje de
> error: eso solo le dice a git que confíe en esa carpeta del sistema, sin
> arreglar la causa real.

Copiar el paquete y los tres certificados de Cloudflare (sección 0, punto 5
— deben estar ya en esta misma carpeta o indicar su ruta completa) al
servidor:

```powershell
scp -P 2222 .\dentia-vps-1.0.0.tar.gz .\origin.pem .\origin.key `
    .\cloudflare-origin-pull-ca.pem deploy@179.236.83.142:~/
```

(El backtick `` ` `` al final de la primera línea es el "continúa en la
siguiente línea" de PowerShell — si prefieres, escribe todo en una sola
línea sin él.)

Ahora sí, conectarse al servidor — **a partir de aquí, el prompt cambia y
todo lo que sigue corre dentro del VPS, no en tu PC**:

```powershell
ssh -p 2222 deploy@179.236.83.142
```

### 3.2 Descomprimir y preparar — dentro del servidor

**Dentro del servidor (sesión SSH ya abierta):**

```bash
tar xzf dentia-vps-1.0.0.tar.gz
cp ~/origin.pem ~/origin.key ~/cloudflare-origin-pull-ca.pem vps/
cd vps
chmod +x scripts/*.sh
```

### 3.3 Instalar (endurecimiento del sistema + Docker)

**Dentro del servidor**, sustituyendo `<TU_IP>` por la IP real (sección 0):

```bash
sudo ./scripts/install.sh --domain demo.dentia.digital --project dentia-demo \
    --admin-ip <TU_IP> --ssh-port 2222
```

Qué hace, en orden (revisar `scripts/install.sh` para el detalle exacto de
cada paso — todo corre dentro del servidor, nada de esto toca tu PC):

1. Zona horaria `America/Mexico_City`, paquetes base (`ufw`, `fail2ban`,
   `unattended-upgrades`, `auditd`).
2. Reinicio automático de madrugada (3:30 a.m.) tras parches de seguridad.
3. `ufw`: SSH solo desde `<TU_IP>` (443 lo filtra el siguiente paso, no
   `ufw` — Docker publica sus puertos por fuera de `ufw`).
4. Docker Engine (repositorio oficial) — se salta si ya está instalado.
5. Cadena `DOCKER-USER`: instala y activa el filtro que deja pasar el 443
   solo desde IPs de Cloudflare (se vuelve a calcular cada vez que arranca
   el servidor, por si Cloudflare publica rangos nuevos).
6. Secretos (`jwt_secret`, `db_password`): se generan **solo si no
   existen** — nunca se pisan en una reinstalación.
7. Certificados de Cloudflare: se copian a `/etc/dentia/dentia-demo/tls/`
   con permisos `644` (legibles por el contenedor `caddy`, que corre con
   capacidades reducidas -- ver sección 2).
8. **Pide una vez, de forma interactiva, ahí mismo en la terminal:** el
   token de GitHub de solo lectura de paquetes (para descargar las
   imágenes de GHCR). Crearlo de antemano en **panel web — GitHub**:
   Settings → Developer settings → Personal access tokens → Fine-grained →
   permiso `read:packages` únicamente — y pegarlo cuando el script lo pida.
9. Crea `compose/.env` con el dominio y nombre de proyecto correctos.
10. Instala y habilita los servicios de `systemd`
    (`dentia@dentia-demo.service`, `dentia-backup@dentia-demo.timer`).

Es **idempotente**: si algo falla a la mitad, correrlo de nuevo (dentro del
servidor) no duplica reglas de firewall ni regenera secretos ya creados.

### 3.4 Desplegar la primera versión

**Dentro del servidor:**

```bash
sudo ./scripts/deploy.sh 1.0.0 dentia-demo
```

Descarga las imágenes `dentia-api:1.0.0` y `dentia-web:1.0.0` de GHCR,
verifica su firma (`cosign`), aplica las migraciones
(`alembic upgrade head`) y levanta los contenedores. Termina verificando
`/api/v1/health` — si no responde sano en ~60 s, el script avisa y no deja
el sistema a medias.

### 3.5 Crear el primer administrador

**Dentro del servidor:**

```bash
sudo ./scripts/create-admin.sh dentia-demo admin@dentia.digital
```

Pide la contraseña **sin mostrarla en pantalla**, dos veces (confirmación),
ahí mismo en la terminal del servidor, y la valida contra la política de
contraseñas (mínimo 12 caracteres, no debe ser una contraseña común) antes
de aceptarla.

Para cargar datos ficticios de prueba en demo (**nunca en producción**),
también **dentro del servidor**:

```bash
sudo docker compose --project-name dentia-demo --project-directory compose \
    run --rm --no-deps api python -m app.seed
```

### 3.6 Verificar desde fuera

Desde un **celular con datos móviles** (nunca en la misma Wi-Fi que el
servidor, para probar de verdad el camino por internet) — esto es en el
**navegador del celular**, ni en tu PC ni en el servidor:

1. `https://demo.dentia.digital` → debe pedir primero el código de
   Cloudflare Access, y después el login de DENT-IA.
2. **Dentro de DENT-IA**, ya con sesión iniciada: probar el flujo completo
   con un paciente ficticio — alta, cita, atención, nota SOAP, odontograma,
   plan, consentimiento firmado, pago y recibo PDF.
3. `https://179.236.83.142` (la IP directa) → no debe responder nada.

Cuando `demo.dentia.digital` pase el checklist completo de la sección 14,
se repite el proceso para producción.

---

## 4. Primera instalación — producción

Mismo VPS, **segundo proyecto independiente** de Docker Compose (su propia
base de datos, sus propios secretos, su propio respaldo). Todo lo de esta
sección corre **dentro del servidor** — si ya cerraste la sesión SSH,
reconéctate primero desde tu PowerShell: `ssh -p 2222 deploy@179.236.83.142`.

**Dentro del servidor**, parado en `~/vps` (donde ya quedaste tras la
sección 3):

```bash
sudo ./scripts/install.sh --domain app.dentia.digital --project dentia-prod \
    --admin-ip <TU_IP> --ssh-port 2222
sudo ./scripts/deploy.sh 1.0.0 dentia-prod
sudo ./scripts/create-admin.sh dentia-prod admin@dentia.digital
```

Con `dentia-demo` y `dentia-prod` corriendo a la vez, revisar que el KVM 2
(8 GB RAM) alcance para ambos — **dentro del servidor**:

```bash
free -h
sudo docker stats --no-stream
```

Si falta memoria, retirar el demo una vez que ya cumplió su propósito —
**dentro del servidor**:

```bash
sudo systemctl disable --now dentia@dentia-demo.service
sudo systemctl disable --now dentia-backup@dentia-demo.timer
```

(Esto detiene los contenedores pero **no borra** los volúmenes de datos ni
los secretos — para borrar de verdad, `docker compose ... down -v` y
`sudo rm -rf /etc/dentia/dentia-demo`, solo cuando se esté seguro de que ya
no hace falta.)

En Caddy, cuando conviven dos proyectos (`dentia-demo` y `dentia-prod`) en
el mismo VPS, cada uno trae su **propio** contenedor `caddy` escuchando en
el mismo puerto 443 del host — Docker no permite publicar el mismo puerto
dos veces desde dos proyectos distintos. Antes de desplegar el segundo
proyecto, revisar que solo uno de los dos tenga el `caddy` activo
publicando 443 (normalmente producción), o separar Caddy en un proyecto
`dentia-edge` compartido que reparta ambos dominios — ver los comentarios
de `compose/docker-compose.yml` si se necesita este escenario.

---

## 5. Respaldos

**Objetivo:** perder como máximo 24 horas de datos (RPO) y volver a operar
en menos de 4 horas (RTO) restaurando en un VPS nuevo.

### 5.1 Configuración única (antes del primer respaldo)

**Dentro del servidor:**

```bash
sudo mkdir -p /etc/dentia/dentia-prod/secrets
sudo nano /etc/dentia/dentia-prod/secrets/restic.env
```

(`nano` es un editor de texto que corre directo en la terminal del
servidor — escribe el contenido de abajo, y para guardar y salir:
`Ctrl+O`, Enter, `Ctrl+X`.)

```ini
RESTIC_REPOSITORY=b2:nombre-del-bucket:dentia-prod
RESTIC_PASSWORD=<frase de paso larga -- guardarla TAMBIEN en un gestor de contrasenas>
B2_ACCOUNT_ID=...
B2_ACCOUNT_KEY=...
HEALTHCHECK_URL=https://hc-ping.com/<uuid>
```

(O las variables de Google Cloud Storage si se prefiere `gs:` en vez de
`b2:` — por ejemplo, un bucket en Querétaro para que los respaldos, aunque
el servidor esté en EUA, queden dentro de México; ver sección 13. El bucket
mismo y sus credenciales se crean de antemano en el **panel web** de
Backblaze o Google Cloud, antes de pegar sus valores aquí.)

**Dentro del servidor**, seguir:

```bash
sudo chmod 600 /etc/dentia/dentia-prod/secrets/restic.env
sudo apt-get install -y restic
sudo ./scripts/backup.sh dentia-prod          # primer respaldo manual
sudo ./scripts/restore-test.sh dentia-prod    # confirma que SI se puede restaurar
```

En el **panel web** del proveedor de almacenamiento (Backblaze B2 o Google
Cloud Storage), activar **Object Lock** (B2) o **Bucket Lock** (GCS) de
**30 días** — así, aunque alguien comprometa el servidor y obtenga las
credenciales de `restic`, no puede borrar los respaldos ya subidos (solo
puede agregar nuevos).

El timer de `systemd` (`dentia-backup@dentia-prod.timer`, instalado por
`install.sh`) corre esto solo, **dentro del servidor**, todos los días a
las 2:00 a.m. (con hasta 5 minutos de variación aleatoria, para no coincidir
exactamente con otros procesos programados) — no requiere que dejes una
sesión SSH abierta ni tu computadora encendida.

### 5.2 Qué se respalda y cómo

| Elemento | Cómo | Retención |
|---|---|---|
| Base de datos PostgreSQL | `pg_dump --format=custom` dentro del contenedor `db`, copiado al host | 30 copias diarias, 12 mensuales (`restic forget`) |
| `storage/` (imágenes, PDF firmados) | `tar` del volumen Docker completo | Igual que la base |
| Cifrado | `restic` (AES-256) antes de salir del servidor | — |
| Fuera del servidor | Backblaze B2 o Google Cloud Storage | — |

**Respaldos de Hostinger** (semanales automáticos + snapshot manual antes de
cada actualización, ya incluidos en el plan VPS, administrados desde el
**panel web — hPanel**): sirven para revertir el servidor **completo**
rápido, pero viven en el mismo proveedor — no sustituyen al respaldo
cifrado externo de arriba. Crear un snapshot manual en hPanel antes de cada
`deploy.sh`/`rollback.sh` importante es gratis y rápido.

### 5.3 Probar la restauración (mensual, obligatorio)

**Dentro del servidor:**

```bash
sudo ./scripts/restore-test.sh dentia-prod
```

Descarga el último respaldo de `restic`, lo restaura en una base de datos
**temporal** (nunca toca la base real), cuenta las tablas restauradas y las
filas en `patients`, y falla con código de salida distinto de cero si algo
sale mal. Es seguro correrlo en cualquier momento, incluso con el sistema
en uso — no afecta la base de producción.

### 5.4 Conservación legal

El expediente clínico exige conservación mínima de 5 años desde la última
atención (NOM-004-SSA3-2012, sección 13). Los datos viven en la base y el
historial nunca se borra físicamente (regla del proyecto), así que la
retención de respaldos de arriba (30 días + 12 meses) cubre
**recuperación ante desastre**, no archivo legal de 5 años — ese archivo lo
garantiza la base de datos en sí, no los respaldos.

---

## 6. Monitoreo y alertas

Toda esta configuración se hace una sola vez, en **páginas web externas**
(no dentro del servidor ni en tu PC):

| Qué vigilar | Cómo | Dónde se configura | Avisa a |
|---|---|---|---|
| El sistema responde | Monitor externo contra `https://app.dentia.digital/api/v1/health` cada 5 min | **Panel web** de UptimeRobot o Better Stack (cuenta gratuita aparte) | Correo + celular |
| El respaldo diario se hizo | `backup.sh` (dentro del servidor) envía un *heartbeat* al terminar | **Panel web** de Healthchecks.io (`HEALTHCHECK_URL` se pega en `restic.env`, sección 5.1) | Correo |
| Uso de CPU/RAM/disco | Alerta cuando el disco pasa de 80 % (`storage/` crece con radiografías) | **Panel web — hPanel** → VPS → Resumen/Monitoreo | Correo |
| Ataques/picos de tráfico | Picos de bloqueos del WAF, protección DDoS activada | **Panel web — Cloudflare** → Notifications | Correo |
| El túnel/servicio sigue arriba | Cloudflare avisa si un health check falla | **Panel web — Cloudflare** → Notifications | Correo |
| `fail2ban`, `auditd`, escáner de malware | Revisión manual semanal | Dentro del servidor (comandos en sección 11) | — |

**Configurar el monitor externo:** como Cloudflare Access protege todo el
dominio (incluido `/api/v1/health`), hay que excluir esa ruta específica de
Access (**panel web — Cloudflare** → Zero Trust → Access → Applications →
excepción de ruta) o crear un *service token* dedicado para el monitor — si
no, UptimeRobot vería siempre el código de Cloudflare Access en vez de la
respuesta real de DENT-IA, y nunca sabría si la API está realmente sana.

---

## 7. Actualizar una versión

Primero en `dentia-demo`, luego en `dentia-prod`, **fuera del horario de
consulta**.

**Tu computadora (PowerShell)**, parado en la carpeta del repositorio
(`C:\workspace\dentia-system` o donde lo tengas clonado):

```powershell
git tag v1.1.0
git push --tags
```

Esperar a que el *workflow* de GitHub Actions termine en verde — **panel
web — GitHub**: pestaña "Actions" del repositorio
(`.github/workflows/release.yml` corre las pruebas, la auditoría, construye
y firma las imágenes, y publica el release automáticamente).

**Dentro del servidor** (conectarse si no tienes ya una sesión abierta:
`ssh -p 2222 deploy@179.236.83.142`, y entrar a `~/vps`):

```bash
sudo ./scripts/deploy.sh 1.1.0 dentia-demo
# ... probar, recorrer el checklist relevante ...
sudo ./scripts/deploy.sh 1.1.0 dentia-prod
```

`deploy.sh` hace, en este orden, y se detiene si cualquier paso falla:

1. **Respaldo inmediato** (`backup.sh`) — la red de seguridad antes de
   tocar nada.
2. Autentica con GHCR usando el token guardado en la instalación.
3. Descarga las imágenes nuevas por etiqueta.
4. Verifica su firma con `cosign` (si está instalado — avisa si no, pero no
   bloquea; instalarlo es muy recomendable, ver sección 11).
5. Aplica `alembic upgrade head`.
6. Reinicia la API y Caddy con las imágenes nuevas.
7. Prueba `/api/v1/health` hasta 20 veces (cada 3 s) antes de darse por
   vencido.

**Prueba rápida después de cada actualización** (navegador, cualquier
dispositivo): `/api/v1/health`, login, abrir un paciente ficticio,
odontograma, un PDF.

---

## 8. Revertir una actualización

**Dentro del servidor:**

```bash
sudo ./scripts/rollback.sh 1.0.0 dentia-prod
```

1. Descarga la imagen de la versión anterior y le pregunta a **sus propios**
   archivos de migración cuál era su revisión de esquema esperada (no asume
   un número de revisión a mano).
2. Baja el esquema (`alembic downgrade`) hasta esa revisión.
3. Vuelve a las imágenes de esa versión y reinicia.
4. Prueba `/api/v1/health`.

Si la migración de la versión que se revierte **alteró datos** (no solo el
esquema) y el *downgrade* no basta para recuperarlos, el último recurso es
restaurar el respaldo cifrado más reciente — **dentro del servidor**:

```bash
sudo ./scripts/restore-test.sh dentia-prod   # confirmar primero que sirve
# luego restaurarlo de verdad con restic restore (ver su documentacion)
```

---

## 9. Comandos del día a día

Todos estos corren **dentro del servidor** (conectarse primero con
`ssh -p 2222 deploy@179.236.83.142` desde tu PowerShell):

```bash
# Que esta corriendo
sudo docker compose --project-name dentia-prod --project-directory compose ps

# Logs en vivo de un servicio (Ctrl+C para salir, no detiene nada)
sudo docker compose --project-name dentia-prod --project-directory compose logs -f api
sudo docker compose --project-name dentia-prod --project-directory compose logs -f caddy
sudo docker compose --project-name dentia-prod --project-directory compose logs -f db

# Entrar a un contenedor (depuracion) -- "exit" para salir del contenedor,
# sin cerrar tu sesion SSH del servidor
sudo docker compose --project-name dentia-prod --project-directory compose exec api bash
sudo docker compose --project-name dentia-prod --project-directory compose exec db psql -U dentia -d dentia

# Reiniciar sin cambiar de version
sudo systemctl restart dentia@dentia-prod.service

# Parar / arrancar todo el proyecto
sudo systemctl stop dentia@dentia-prod.service
sudo systemctl start dentia@dentia-prod.service

# Estado de los respaldos automaticos
sudo systemctl status dentia-backup@dentia-prod.timer
sudo systemctl list-timers dentia-backup@dentia-prod.timer

# Espacio en disco
df -h
sudo docker system df

# Verificar que el firewall sigue como se espera
sudo ufw status verbose
sudo fail2ban-client status sshd
sudo ss -tlnp
```

Para salir del servidor y volver a tu PowerShell: `exit`.

---

## 10. Respuesta a incidentes

Si se sospecha un acceso indebido, fuga de datos, o el sistema se comporta
de forma anómala — esta sección mezcla pasos en distintos lugares, cada uno
etiquetado:

1. **Contener.**
   - **Panel web — Cloudflare**: activar *Under Attack Mode* (Overview →
     panel superior).
   - **Panel web — Cloudflare**: bloquear la IP o el país sospechoso en WAF.
   - **Dentro del servidor**: revocar todas las sesiones activas rotando
     `JWT_SECRET` y reiniciando la API — invalida todos los tokens de
     inmediato:
     ```bash
     sudo nano /etc/dentia/dentia-prod/secrets/jwt_secret
     # borrar el contenido, pegar uno nuevo generado con:
     python3 -c "import secrets; print(secrets.token_hex(48))"
     sudo systemctl restart dentia@dentia-prod.service
     ```
   - **Dentro de DENT-IA** (como `admin_clinica`): desactivar la cuenta del
     usuario afectado desde Usuarios → editar → inactivo — no requiere
     tocar el servidor.

2. **Si se sospecha que el servidor mismo está comprometido** (no solo una
   cuenta de usuario):
   - **Panel web — hPanel**: snapshot del VPS, para análisis forense
     posterior.
   - **Panel web — hPanel**: crear un VPS nuevo. Luego, **tu computadora**
     + **dentro del servidor nuevo**: reinstalar desde cero con este mismo
     paquete (sección 3, `install.sh` + `deploy.sh` con la última versión
     conocida buena).
   - Restaurar el último respaldo **limpio** (de antes del incidente) —
     dentro del servidor nuevo.
   - Rotar **todos** los secretos: `jwt_secret`, `db_password` (dentro del
     servidor), el token de GHCR (**panel web — GitHub**, revocar el viejo
     y crear uno nuevo), la frase de paso de `restic` (**panel web** del
     proveedor de almacenamiento).

3. **Investigar:**
   - **Dentro de DENT-IA**: `AuditEvent` de la aplicación (quién leyó o
     exportó qué expediente).
   - **Panel web — Cloudflare**: Security → Events (WAF) y Analytics.
   - **Dentro del servidor**: `auditd` — `sudo ausearch -ts today`.
   - **Dentro del servidor**: bitácoras de Docker —
     `sudo docker compose ... logs` de cada servicio.

4. **Notificar** a los titulares afectados si la vulneración compromete sus
   datos personales de forma significativa — obligación de la
   LFPDPPP 2025 (ver sección 13). Esto lo decide la clínica como
   responsable de los datos, idealmente con asesoría legal.

5. **Documentar** el incidente y las correcciones aplicadas (postmortem) —
   qué pasó, cómo se detectó, qué se hizo, qué cambia para que no se repita.

---

## 11. Mantenimiento mensual

Todo **dentro del servidor**, salvo donde se indica lo contrario:

- `sudo apt update && sudo apt upgrade` y reiniciar si lo pide el kernel
  (revisar con `test -f /var/run/reboot-required && echo "reinicio pendiente"`)
  — los parches de seguridad ya llegan solos con `unattended-upgrades`, esto
  es para el resto.
- Actualizar la imagen base `postgres:16` a la versión menor más reciente:
  esto se hace publicando un release nuevo (sección 7) después de que, **en
  tu computadora**, se reconstruya la imagen con `docker build --pull` en
  el pipeline de CI para que tome la versión más reciente de `postgres:16`
  disponible (no requiere cambiar nada a mano en el servidor).
- `sudo fail2ban-client status sshd` — revisar cuántas IPs están baneadas y
  si hay patrones sospechosos.
- `sudo ausearch -ts this-month | less` — revisar `auditd`.
- **Panel web — hPanel**: revisar el resultado del escáner de malware (VPS
  → Seguridad).
- `sudo ./scripts/restore-test.sh dentia-prod` — confirmar que el respaldo
  sigue siendo restaurable (no basta con que `backup.sh` "no falle").
- Antes de cada versión **mayor** (no cada parche menor): `pip-audit`,
  `npm audit` y Trivy sin hallazgos críticos nuevos — ya los corre
  automáticamente `ci-test.sh`/`ci-build-push.sh` en cada release, pero vale
  la pena revisar el resumen del *workflow* en **panel web — GitHub** →
  Actions.

---

## 12. Costo mensual estimado

Cifras de referencia (los precios de Hostinger cambian con frecuencia —
confirmar en hostinger.mx antes de renovar):

| Componente | Plan | US$/mes aprox. (promoción / renovación) |
|---|---|---|
| VPS producción | KVM 2 | 9–15 / 20–30 |
| VPS demo (si se mantiene aparte) | KVM 1 | 6–9 / 12–18 |
| Dominio `dentia.digital` | Ya contratado | ~1 (renovación anual prorrateada) |
| Cloudflare | Free | 0 |
| Almacenamiento de respaldos | Backblaze B2 o Cloud Storage, ~50 GB | 1–3 |
| Monitor externo | Plan gratuito | 0 |

**Total aproximado: US$17–28/mes con precios de promoción, US$35–55/mes al
renovar** — bastante menor que una nube administrada porque el operador
(quien sigue esta guía) hace el trabajo de mantenimiento que ahí vendría
incluido.

En este paquete, `dentia-demo` y `dentia-prod` comparten el **mismo** VPS
(sección 4), así que normalmente no hay un costo de VPS separado para demo
— solo si se decide tener un KVM 1 aparte para no competir por recursos con
producción.

---

## 13. Cumplimiento normativo en México

Resumen técnico, **no asesoría legal** — validar con un abogado
especialista antes de cargar pacientes reales, sobre todo por el punto de
"datos fuera de México".

### Datos fuera de México

El VPS `srv2091418` está fuera de México — confirmar en **panel web —
hPanel** → VPS → Resumen si es EUA o Brasil. Esto significa que los
expedientes clínicos se almacenan en el extranjero. Implicaciones
concretas:

- Declararlo en el aviso de privacidad: ubicación del servidor y los
  proveedores que tratan datos por cuenta de la clínica (Hostinger,
  Cloudflare, el proveedor de respaldos).
- Confirmar con el abogado que la figura de "encargado" (LFPDPPP) cubre
  este arreglo.
- Si la clínica **exige** que los datos permanezcan en México, Hostinger no
  es la opción adecuada para esta fase — se necesitaría una nube con región
  en Querétaro.
- Para reducir lo que sale del país sin cambiar de proveedor del VPS, los
  **respaldos** sí pueden guardarse en un bucket de Google Cloud Storage en
  Querétaro (cambiar `RESTIC_REPOSITORY` a `gs:...` en `restic.env`, dentro
  del servidor, sección 5.1).

### Normas aplicables

| Norma | Qué implica para DENT-IA en Hostinger |
|---|---|
| **LFPDPPP 2025** (vigente desde 21-mar-2025; autoridad: Secretaría Anticorrupción y Buen Gobierno, sustituyó al INAI) | Los datos de salud son **sensibles**: exigen consentimiento expreso y por escrito. Aviso de privacidad integral que identifique los datos sensibles. Hostinger, Cloudflare y el proveedor de respaldos actúan como **encargados** — archivar sus términos y acuerdos de tratamiento de datos. Medidas de seguridad documentadas (este documento sirve de base). Procedimiento para derechos ARCO. |
| **NOM-004-SSA3-2012** | Contenido mínimo del expediente clínico; conservación de al menos **5 años** desde la última atención — compatible con la regla de "no borrado físico" ya implementada en DENT-IA. |
| **NOM-024-SSA3-2012** (vigente) | Seguridad, integridad, trazabilidad e interoperabilidad de sistemas electrónicos de salud. DENT-IA ya cubre auditoría, hashes de documentos firmados y versionado de notas clínicas; falta evaluar interoperabilidad y, si el sistema se comercializa a otras clínicas, tramitar un dictamen de conformidad ante CENETEC. |

### Acciones pendientes antes de cargar pacientes reales

- [ ] Redactar y publicar el aviso de privacidad en
      `https://app.dentia.digital/privacidad`, incluyendo explícitamente la
      ubicación del servidor fuera de México.
- [ ] Agregar al alta del paciente la casilla y firma de consentimiento
      expreso para datos sensibles (reutilizar el módulo de consentimientos
      con `SignaturePad`, ya existente en DENT-IA).
- [ ] Revisar y archivar los términos de servicio / tratamiento de datos de
      Hostinger, Cloudflare y del proveedor de respaldos elegido.
- [ ] Documentar: inventario de datos, medidas de seguridad (este
      documento), y quién es el responsable interno de privacidad en la
      clínica.
- [ ] Definir el procedimiento de atención a vulneraciones (sección 10 ya
      da el flujo técnico; falta el flujo de **notificación** a pacientes
      afectados, que es una decisión de la clínica).
- [ ] Revisión legal del aviso de privacidad, del tratamiento de datos
      sensibles, y del almacenamiento fuera de México.

---

## 14. Checklist final de salida a producción

**No se cargan pacientes reales hasta marcar todo esto en
`app.dentia.digital`.**

### Cuentas y dominio

- [ ] 2FA activa en Hostinger, Cloudflare, GitHub y el almacenamiento de
      respaldos (**panel web** de cada uno).
- [ ] `dentia.digital` con nameservers de Cloudflare, DNSSEC y bloqueo de
      transferencia (sección 0, ya confirmado — re-verificar).
- [ ] Registros `app` y `demo` con proxy activado (la IP del VPS no aparece
      en el DNS público) — **panel web — Cloudflare** → DNS.

### Seguridad técnica

- [ ] Cloudflare en modo **Full (strict)** con certificado de origen y
      Authenticated Origin Pulls; TLS 1.2+; *Always Use HTTPS* — **panel
      web — Cloudflare**.
- [ ] Firewall de hPanel y `ufw`: 443 solo desde Cloudflare, SSH solo desde
      `<TU_IP>` — **panel web — hPanel** + dentro del servidor.
- [ ] `https://179.236.83.142` no responde (probar desde tu navegador).
      Opcional, más riguroso: instalar Nmap para Windows
      (nmap.org/download.html) y correr, **en tu computadora**,
      `nmap -Pn 179.236.83.142` — debe mostrar solo el puerto 2222.
- [ ] SSH solo con llave, sin root ni contraseña; `fail2ban` activo —
      verificar **en tu computadora** (sección 0) y **dentro del servidor**
      (`sudo fail2ban-client status sshd`).
- [ ] Regla de límite de intentos en el login de Cloudflare probada (11
      intentos en un minuto quedan bloqueados) — **panel web —
      Cloudflare** → Security → WAF → Rate limiting rules.
- [ ] Política de contraseñas activa y todos los usuarios con contraseñas
      que la cumplen.
- [ ] `ENVIRONMENT=production`, `AI_ENABLED=false`, `AI_FAKE_MODE=false`;
      `/api/v1/docs` responde 404 (probar en el navegador).
- [ ] `AuditEvent` registra la IP real del cliente, no `127.0.0.1` —
      **dentro de DENT-IA**.
- [ ] Secretos en `/etc/dentia/<proyecto>/secrets` y `/tls` con el directorio
      del proyecto en `700` (root); `jwt_secret`/`db_password`/certificado de
      origen en `644` (los lee un contenedor sin privilegios), `ghcr_token` y
      `restic.env` en `600` (solo los lee el host); sin ningún `.env` con
      contraseñas en texto plano — verificar dentro del servidor.
- [ ] Sin usuarios del `seed` ni `DEMO_PASSWORD` en `dentia-prod`.
- [ ] `pip-audit`, `npm audit` y Trivy sin hallazgos críticos — revisar el
      resumen del último *workflow* en **panel web — GitHub** → Actions.

### Funcionalidad

- [ ] Flujo completo con paciente **ficticio** probado en producción antes
      de cargar el primero real: alta, cita, atención, nota SOAP,
      odontograma, plan, consentimiento firmado, pago y recibo PDF —
      **dentro de DENT-IA**.
- [ ] Carga de una radiografía de 10 MB sin error (límite actual: 25 MB).
- [ ] Ninguna opción de IA visible en ningún rol; el navegador no pide
      permiso de micrófono.

### Operación

- [ ] Tras `sudo reboot` (**dentro del servidor**), todo arranca solo:
      PostgreSQL, la API, Caddy — reconectarse por SSH después de ~1 minuto
      y verificar con `sudo docker compose ... ps`.
- [ ] Respaldo diario cifrado llegando al almacenamiento externo con Object
      Lock — verificar en el **panel web** del proveedor de almacenamiento;
      *heartbeat* de Healthchecks.io llegando a tiempo — **panel web** de
      Healthchecks.io.
- [ ] `restore-test.sh` con resultado PASS, corrido en el mes en curso —
      dentro del servidor.
- [ ] Monitor externo y alertas de disco llegando de verdad al responsable
      (probarlo: provocar un fallo intencional y confirmar que avisa).
- [ ] Reversión (`rollback.sh`) probada al menos una vez en `dentia-demo` —
      dentro del servidor.

### Cumplimiento (sección 13)

- [ ] Aviso de privacidad publicado (incluye la ubicación del servidor
      fuera de México), consentimiento expreso en el alta de pacientes.
- [ ] Términos de tratamiento de datos de Hostinger, Cloudflare y el
      proveedor de respaldos archivados.
- [ ] Revisión legal del aviso de privacidad y del tratamiento de datos
      sensibles hecha.
