# Instalación de producción — Clínica EMO

Instructivo para publicar DENT-IA en internet para una clínica real, con el
paquete de instalación/actualización de este repositorio
(`scripts/install-dentia.ps1`, `scripts/update-dentia.ps1`,
`backend/app/bootstrap_clinic.py`). Basado en
`DENT-IA — Guía de publicación en ambiente web (Internet).pdf` (@omar,
23-oct-2026); aquí se adapta a esta clínica en concreto y se documenta lo que
ya quedó automatizado en scripts.

**No se cargan pacientes reales hasta terminar el checklist de la sección 10.**

> **Nota de seguridad:** este documento se versiona en un repositorio
> público, así que las contraseñas reales de esta clínica (PostgreSQL,
> cuentas iniciales) **no se escriben aquí en texto plano** — se referencian
> como `<contraseña real, ver gestor de contraseñas>`. Quien instale de
> verdad ya las tiene guardadas (eran las acordadas al planear este
> despliegue); si no las tienes, pídeselas a quien las generó o genera unas
> nuevas y actualízalas en el servidor real.

## 0. Resumen de lo que se va a tener

| Dato | Valor |
|---|---|
| Dominio público | `https://app.clinica.emo` |
| Usuarios iniciales | 3 (ver sección 6) |
| Dominio de correo | `@clinica.emo` |
| Asistente de IA / app móvil | Deshabilitados en esta fase |
| Autenticación de doble factor (MFA) | Deshabilitada por ahora (decisión explícita de la clínica) |
| Protección del login | Captcha (Cloudflare Turnstile) + límite de 5 intentos fallidos / 15 min por correo |

> **Nota sobre el dominio:** `.emo` no es un dominio de internet público
> (TLD) real, por lo que **no se puede registrar ni usar en el DNS público de
> Cloudflare** tal cual. Antes de activar el túnel (sección 7), la clínica
> necesita uno de estos dos caminos:
>
> 1. **Dominio real propio** (recomendado si de verdad se va a publicar en
>    internet): registrar un dominio válido (p. ej. `clinica-emo.mx`) y usar
>    `app.<ese dominio>` en vez de `app.clinica.emo` en todos los archivos de
>    esta guía (Caddyfile ya no depende del dominio, pero si cambia hay que
>    ajustar `CORS_ORIGINS` en `backend\.env` y `VITE_API_URL` en
>    `frontend\.env.production`).
> 2. **Solo uso interno/privado** (sin salir a internet real): resolver
>    `app.clinica.emo` dentro de la red de la clínica con una entrada en
>    `C:\Windows\System32\drivers\etc\hosts` de cada equipo, y usar Caddy con
>    un certificado local en vez de Cloudflare Tunnel (fuera del alcance de
>    este instructivo, que sigue el diseño con túnel del PDF).
>
> El correo `@clinica.emo` de los 3 usuarios (sección 6) es solo un
> **identificador de login dentro del sistema** — no necesita recibir correo
> real para funcionar, así que no depende de resolver este problema.

## 1. Arquitectura

```
Internet
  │
  ▼
Cloudflare (HTTPS, Access, límite de login) — app.clinica.emo
  │  túnel saliente (cloudflared, servicio de Windows)
  ▼
Servidor Windows de la clínica
  ├── cloudflared (servicio)
  ├── Caddy :8080 (solo 127.0.0.1) — sirve el frontend y reenvía /api
  ├── API FastAPI (Uvicorn, :8001, solo 127.0.0.1)
  ├── PostgreSQL 16 (solo localhost)
  └── C:\DentiaData (storage, backups, logs)
```

Nada queda expuesto a la red Wi-Fi de la clínica ni a internet directamente;
todo el tráfico entra por el túnel saliente de Cloudflare. Agente de IA y app
móvil no se instalan en esta fase.

## 2. Software necesario

Instalar en el servidor Windows dedicado (no la computadora de recepción ni
de uso diario), como Administrador, en este orden:

| # | Software | De dónde | Notas |
|---|---|---|---|
| 1 | **Windows 11 Pro** (64 bits) o Windows Server 2022/2025 | — | Ya instalado en el servidor |
| 2 | **PostgreSQL 16** | Instalador oficial para Windows (postgresql.org/download/windows) | Durante la instalación te pide la contraseña del superusuario `postgres` — usa `<contraseña real, ver gestor de contraseñas>` (ver sección 4) |
| 3 | **Python 3.12** | python.org/downloads | Marcar **"Add python.exe to PATH"** en el instalador |
| 4 | **Node.js 20 LTS** | nodejs.org | Solo se usa para compilar el frontend, no corre como servicio |
| 5 | **Git** | git-scm.com/download/win | |
| 6 | **Caddy** (`caddy.exe`) | caddyserver.com/download (build para Windows/amd64) | Copiar el `.exe` a `C:\Dentia\tools\caddy.exe` |
| 7 | **NSSM** (`nssm.exe`) | nssm.cc/download | Copiar el `.exe` de la carpeta `win64` a `C:\Dentia\tools\nssm.exe` |
| 8 | **cloudflared** | Panel de Cloudflare Zero Trust al crear el túnel (sección 7) te da el instalador MSI | No hace falta descargarlo aparte |

Verificar cada instalación en una terminal nueva de PowerShell:

```powershell
psql --version
python --version
node --version
git --version
```

## 3. Preparar Windows y clonar el repositorio

Seguir la sección 4 del PDF de referencia (energía, Wi-Fi, BitLocker, cuenta
`dentia-svc`, firewall) — resumen de lo imprescindible:

```powershell
# Plan de energía: nunca suspender/hibernar
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0

# Carpetas
New-Item -ItemType Directory -Force -Path C:\Dentia, C:\DentiaData

# Clonar el repositorio (sustituir por la URL real)
git clone <url-del-repositorio> C:\Dentia\app
cd C:\Dentia\app
git checkout v1.0.0   # la etiqueta que se vaya a publicar (sección 8)
```

Firewall de Windows: perfil **Privada** para la red de la clínica, **sin**
reglas de entrada para los puertos 5432, 8001 ni 8080 (nadie de la red debe
poder llegar directo a ellos; solo Cloudflare, vía el túnel saliente, llega a
8080).

## 4. PostgreSQL — contraseñas de esta clínica

| Cuenta | Uso | Contraseña |
|---|---|---|
| `postgres` (superusuario) | Solo para crear el rol de la app y las extensiones; no la usa el sistema en el día a día | `<contraseña real, ver gestor de contraseñas>` |
| `dentia` (rol de la aplicación) | La que usa el backend para conectarse (en `DATABASE_URL`) | `<contraseña real, ver gestor de contraseñas>` |

Guardar ambas en un gestor de contraseñas del responsable técnico — **no
quedan en ningún archivo de este repositorio** (`backend\.env` tampoco se
versiona).

`scripts\install-dentia.ps1` (sección 5) puede crear el rol y la base por ti,
pidiendo estas dos contraseñas de forma segura (sin mostrarlas en pantalla).
Si prefieres hacerlo a mano primero:

```powershell
$env:PGPASSWORD = "<contraseña real, ver gestor de contraseñas>"
psql -U postgres -h localhost -c "CREATE ROLE dentia LOGIN PASSWORD '<contraseña real, ver gestor de contraseñas>';"
psql -U postgres -h localhost -c "CREATE DATABASE dentia OWNER dentia;"
psql -U postgres -h localhost -d dentia -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
psql -U postgres -h localhost -d dentia -c "CREATE EXTENSION IF NOT EXISTS unaccent;"
psql -U postgres -h localhost -d dentia -c "CREATE EXTENSION IF NOT EXISTS btree_gist;"
Remove-Item Env:\PGPASSWORD
```

En `postgresql.conf`, confirmar `listen_addresses = 'localhost'` (valor por
defecto en la mayoría de instalaciones de Windows — no debe escuchar en la
red).

## 5. Instalación del sistema (`install-dentia.ps1`)

Parado en `C:\Dentia\app`, como Administrador:

```powershell
.\scripts\install-dentia.ps1
```

Qué hace (ver el script para el detalle completo, está comentado):

1. Crea `C:\DentiaData\{storage,backups,logs}`.
2. Crea el rol y la base de PostgreSQL (puedes saltarlo con `-SkipPostgres`
   si ya lo hiciste a mano en la sección 4).
3. Crea el entorno virtual de Python, instala dependencias.
4. Si no existe `backend\.env`, lo crea desde
   `backend\.env.production.example` y **pausa** para que lo edites (JWT
   secreto, contraseña de PostgreSQL, Turnstile — sección 7.3) antes de
   continuar.
5. Corre las migraciones (`alembic upgrade head`).
6. Registra la API como servicio de Windows **`DentiaAPI`** (NSSM), sin
   `--reload`, con `--workers 2` y las cabeceras de proxy que hacen que
   `AuditEvent.ip` registre la IP real del cliente en vez de `127.0.0.1`
   (necesario porque todo pasa por Caddy).
7. Compila el frontend (`npm ci && npm run build`) y lo publica en
   `C:\Dentia\www`.
8. Registra Caddy como servicio **`DentiaWeb`** (NSSM), usando
   `deploy\caddy\Caddyfile` de este repositorio.
9. Arranca ambos servicios y prueba `http://127.0.0.1:8001/api/v1/health` y
   `http://127.0.0.1:8080`.

Al terminar, genera el `JWT_SECRET` real (si no lo hiciste al editar `.env`):

```powershell
python -c "import secrets; print(secrets.token_hex(48))"
```

### Cuenta de servicio `dentia-svc` (recomendado)

El script deja `DentiaAPI` corriendo con la cuenta con la que lo instalaste.
Para usar una cuenta local sin permisos de administrador (más seguro):

```powershell
net user dentia-svc <password-robusta> /add
# Dar permiso de "Iniciar sesión como servicio" vía secpol.msc si Windows lo pide
nssm set DentiaAPI ObjectName ".\dentia-svc" "<password-robusta>"
nssm restart DentiaAPI
```

Dar permisos NTFS de `C:\DentiaData` y `backend\.env` solo a Administradores
y a `dentia-svc`.

## 6. Alta de los 3 usuarios (`bootstrap_clinic.py`)

**Nunca correr `python -m app.seed` en producción** — crea 50 pacientes
ficticios y usuarios con una contraseña de ejemplo conocida
(`DEMO_PASSWORD`). Para esta clínica se usa un comando de alta controlado,
`app.bootstrap_clinic`, que no toca pacientes ni citas: solo crea la
organización, la sucursal, y exactamente estas 3 cuentas:

| Correo | Rol en el sistema | Qué puede hacer |
|---|---|---|
| `agenda@clinica.emo` | `recepcion` | Agenda, pacientes (alta, datos generales) |
| `admin@clinica.emo` | `admin_clinica` | Administración de la clínica, usuarios, apariencia, catálogos |
| `odontologo@clinica.emo` | `odontologo` | Expediente clínico, odontograma, notas, diagnóstico, plan |

Contraseña inicial para las 3: `<contraseña real, ver gestor de contraseñas>`.

```powershell
cd C:\Dentia\app\backend
.\.venv\Scripts\Activate.ps1
$env:BOOTSTRAP_PASSWORD = "<contraseña real, ver gestor de contraseñas>"
python -m app.bootstrap_clinic --clinic-name "Clinica EMO" --email-domain clinica.emo
Remove-Item Env:\BOOTSTRAP_PASSWORD
```

Es idempotente (se puede volver a correr sin duplicar nada): si una cuenta ya
existe, la deja tal cual y lo reporta. Para ver qué haría sin escribir nada,
agregar `-DryRun`... en realidad el flag es `--dry-run`:

```powershell
python -m app.bootstrap_clinic --clinic-name "Clinica EMO" --email-domain clinica.emo --dry-run
```

**Importante — contraseña compartida:** las 3 cuentas arrancan con la misma
contraseña solo para el primer ingreso. Pide a cada persona que la cambie de
inmediato (**Salir del menú → próximamente "Mi perfil" → Cambiar
contraseña**, o desde *Usuarios* si lo hace `admin_clinica` por ella) antes
de usar el sistema con pacientes reales — una contraseña compartida y
conocida en un sistema expuesto a internet es el riesgo de seguridad más
grande de este arranque inicial, incluso con captcha y límite de intentos.

## 7. Publicar en internet (Cloudflare)

Todo esto se hace en el panel de Cloudflare (cuenta propia de la clínica,
**no la puede crear ni operar este asistente** — son pasos para que los haga
una persona de la clínica con acceso al panel):

### 7.1 Túnel

1. Cloudflare Zero Trust → Networks → Tunnels → **Create a tunnel** → tipo
   `cloudflared` → nombre `dentia-clinica-emo`.
2. Elegir Windows; copiar el comando con el token y correrlo en el servidor
   como Administrador: `cloudflared.exe service install <TOKEN>`. Queda
   como servicio de Windows que arranca solo.
3. **Public hostname:** `app.clinica.emo` (o el dominio real que se haya
   decidido usar, ver la nota de la sección 0) → servicio HTTP →
   `localhost:8080`. No publicar ninguna otra ruta ni puerto.
4. Guardar el token del túnel en el gestor de contraseñas — nunca en este
   repositorio.

### 7.2 Access (control de acceso adicional)

Zero Trust → Access → Applications → aplicación para el dominio público:
política *Allow* solo para los 3 correos `@clinica.emo` del personal (o los
correos reales donde reciban el código, si se decide usar otros para
Access); método: código de un solo uso por correo; sesión 24 h. Así un
atacante no llega ni a la pantalla de login de DENT-IA sin estar en la
lista.

### 7.3 Turnstile (captcha del login)

1. Cloudflare → Turnstile → **Add widget** → dominio `app.clinica.emo` →
   modo "Managed".
2. Copiar la **Site Key** (pública) a `frontend\.env.production` →
   `VITE_TURNSTILE_SITE_KEY`.
3. Copiar la **Secret Key** a `backend\.env` → `TURNSTILE_SECRET_KEY`.
4. Recompilar el frontend y reiniciar la API:
   ```powershell
   cd C:\Dentia\app\frontend; npm run build
   robocopy dist C:\Dentia\www /MIR
   nssm restart DentiaAPI
   nssm restart DentiaWeb
   ```
5. Probar: el formulario de login debe mostrar el widget de Turnstile antes
   de poder enviar. Protege las 3 cuentas (no se puede limitar solo a
   `admin`: el rol no se conoce hasta después de autenticar).

### 7.4 Límite de intentos de login y HTTPS

| Ajuste | Dónde | Valor |
|---|---|---|
| Límite de login por IP | Security → WAF → Rate limiting rules | Ruta `/api/v1/auth/login`, 10 peticiones/min por IP, bloqueo 10 min |
| HTTPS | SSL/TLS → Edge Certificates | Always Use HTTPS: activado; TLS mínimo 1.2 |
| Caché | Caching → Cache Rules | Omitir caché (*bypass*) para `/api/*` |

Esto es **además** del captcha y del límite de 5 intentos/15 min por correo
que ya trae el sistema (`app/modules/iam/rules.py`).

### 7.5 Probar desde fuera

Desde un celular con datos móviles (fuera del Wi-Fi de la clínica), abrir
`https://app.clinica.emo`: debe pedir primero el código de Cloudflare
Access y después el login de DENT-IA con captcha.

## 8. Actualizaciones (`update-dentia.ps1`)

Cada versión nueva se etiqueta en git y se publica con un solo comando. En el
equipo de desarrollo:

```bash
git tag v1.1.0
git push --tags
```

En el servidor, como Administrador:

```powershell
.\scripts\update-dentia.ps1 -Tag v1.1.0
```

Hace, en orden: respaldo (`scripts\backup.ps1`), detener `DentiaAPI`, `git
fetch --tags` + `git checkout v1.1.0`, instalar dependencias, migrar,
reiniciar `DentiaAPI`, recompilar el frontend, reiniciar `DentiaWeb`, y probar
`/api/v1/health`. Si la API no responde después de actualizar, el script
avisa cómo revertir (`update-dentia.ps1 -Tag <version-anterior>`); si una
migración alteró datos y el *downgrade* no basta, restaurar el respaldo del
paso 1 con `pg_restore` (ver `docs/OPERACION.md`).

Antes de cada versión mayor: `pip-audit` y `npm audit` sin hallazgos nuevos
(ver sección 11 del PDF de referencia).

## 9. Respaldos

Ya cubierto en `docs/OPERACION.md` — usar los mismos scripts
(`scripts\backup.ps1`, `scripts\restore_test.ps1`), con estos ajustes para
producción:

- `-BackupDir C:\DentiaData\backups` (coincide con la carpeta que crea
  `install-dentia.ps1`).
- Programar diario 2:00 a.m. con la cuenta `dentia-svc` y
  `restore_test.ps1` semanal, como describe `docs/OPERACION.md` sec. 5.
- Copiar `C:\DentiaData\backups\*.enc` fuera del consultorio (nube o disco
  externo rotado) — un robo o incendio en la clínica se lleva el servidor
  *y* un respaldo que solo vive ahí mismo.
- Guardar `BACKUP_PASSPHRASE` fuera del servidor (gestor de contraseñas);
  sin ella los respaldos cifrados no sirven.

## 10. Checklist final antes de cargar pacientes reales

No marcar nada como listo con una casilla fallando.

**Seguridad**
- [ ] `ENVIRONMENT=production`, `JWT_SECRET` propio (no `change-me`),
      `AI_ENABLED=false`, `AI_FAKE_MODE=false`, `CORS_ORIGINS` con el
      dominio real.
- [ ] `https://app.clinica.emo/api/v1/docs` responde 404.
- [ ] Desde otra computadora del Wi-Fi, `http://<IP-servidor>:8001`,
      `:8080` y `:5432` **no** responden.
- [ ] Cloudflare Access pide código antes de mostrar el login; un correo no
      autorizado no entra.
- [ ] El login muestra el captcha de Turnstile y lo exige para entrar.
- [ ] 6 intentos de login fallidos seguidos para el mismo correo quedan
      bloqueados 15 min (límite propio del sistema); 11 intentos en un
      minuto desde la misma IP quedan bloqueados por Cloudflare.
- [ ] `AuditEvent` registra la IP real del cliente, no `127.0.0.1`.
- [ ] Un `UPDATE` directo sobre `audit_events` falla.
- [ ] BitLocker activo; `dentia-svc` sin permisos de administrador; red de
      invitados separada de la del servidor.
- [ ] `pip-audit` y `npm audit` sin hallazgos nuevos.
- [ ] No existe ningún usuario del `seed` ni la contraseña `DEMO_PASSWORD`.
- [ ] Las 3 cuentas de la clínica cambiaron su contraseña inicial
      compartida.

**Funcionalidad**
- [ ] Acceso desde fuera (celular con datos móviles) y desde dentro de la
      clínica.
- [ ] Flujo completo con un paciente **ficticio**: alta, cita, atención,
      nota SOAP, odontograma, plan, consentimiento firmado, pago y recibo
      PDF.
- [ ] Ninguna opción de IA visible y `/api/v1/ai/` responde 404; el
      navegador no pide micrófono.
- [ ] Carga de una imagen/radiografía sin error (límite actual: 15 MB por
      archivo).
- [ ] Marca DENT-IA visible en login, sistema y PDFs.

**Operación**
- [ ] Tras reiniciar Windows, PostgreSQL, `DentiaAPI`, `DentiaWeb` y
      `cloudflared` arrancan solos sin iniciar sesión.
- [ ] Cambiar la IP del servidor (renovar DHCP) no afecta el acceso por
      `https://app.clinica.emo`.
- [ ] Suspensión desactivada; no-break probado con un corte simulado.
- [ ] Respaldo diario cifrado copiándose fuera del consultorio.
- [ ] `restore_test.ps1` con resultado PASS sobre un respaldo descargado de
      la nube.
- [ ] Monitor externo de disponibilidad (UptimeRobot/Healthchecks.io) y
      alerta de túnel desconectado configurados.
- [ ] Token del túnel, frase de paso de respaldos y las 3 contraseñas
      guardadas fuera del servidor (gestor de contraseñas).

**Cumplimiento** (México — LFPDPPP, NOM-004-SSA3-2012, NOM-024-SSA3-2012;
esto es un resumen técnico, no asesoría legal — validar con un abogado
especialista antes de cargar pacientes reales)
- [ ] Aviso de privacidad publicado en `https://app.clinica.emo/privacidad`
      y consentimiento expreso en el alta de pacientes.
- [ ] Términos de tratamiento de datos de Cloudflare y del proveedor de
      respaldos en la nube archivados.
- [ ] Revisión legal del aviso y del tratamiento de datos sensibles de
      salud.
