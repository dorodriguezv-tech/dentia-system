# Flujo de trabajo: de Visual Studio Code a producción

Guía de referencia para hacer un cambio en DENT-IA, probarlo en tu máquina,
subirlo a GitHub, y finalmente llevarlo al servidor. Complementa a
`deploy/vps/INSTALACION_VPS.md` (que cubre la instalación inicial del VPS y
el detalle de cada script) — este documento se enfoca en el día a día:
"edité algo, ¿ahora qué?".

---

## Resumen del camino completo

```
1. Editar en VS Code (tu PC)
        │
2. Verificar en local (localhost) ──► si falla algo, se corrige aquí, nunca
        │                              se sube a git con pruebas rotas
        ▼
3. git add / commit / push a GitHub (rama main)
        │
4. git tag vX.Y.Z / git push --tags ──► esto DISPARA el pipeline automático
        │                               (GitHub Actions): pruebas, auditoría,
        │                               construye y firma las imágenes,
        │                               publica el release
        ▼
5. Conectarse al VPS (ssh) y correr deploy.sh ──► primero en
        │                                          demo.dentia.digital,
        │                                          nunca directo a producción
        ▼
6. Probar en demo.dentia.digital ──► si todo bien, repetir el paso 5
                                       para dentia-prod (app.dentia.digital)
```

Nada llega al servidor automáticamente. Tú decides cuándo pasar del paso 4
al 5 — pueden pasar días entre "ya hay una versión publicada en GitHub" y
"ya la instalé en el servidor".

---

## 1. Editar en Visual Studio Code

Trabajas como siempre: abres `C:\workspace\dentia-system` en VS Code, editas
archivos de `backend/` (Python) o `frontend/` (TypeScript/React), o
`backend/alembic/versions/` si el cambio necesita una migración de base de
datos.

Nada de esto toca el servidor ni GitHub todavía — es solo tu copia local.

---

## 2. Verificar en local antes de subir nada

**Regla de oro: nunca subas (`git push`) un cambio con pruebas rotas.** El
pipeline automático (paso 4) va a correr exactamente las mismas pruebas y lo
va a rechazar de todas formas — correrlas en tu máquina primero es más
rápido que esperar ~10 minutos a que falle en GitHub.

### 2.1 Arrancar todo para probar manualmente

Desde PowerShell, parado en `C:\workspace\dentia-system`:

```powershell
.\scripts\start-dentia.ps1
```

Levanta la base de datos (si no estaba corriendo), abre una ventana nueva
con el backend (`uvicorn`, puerto 8001) y otra con el frontend (`npm run
dev`, puerto 5174). Abre `http://localhost:5174` en el navegador y prueba
el cambio a mano.

Para apagar todo al terminar:

```powershell
.\scripts\stop-dentia.ps1
```

⚠️ **No cierres las ventanas de uvicorn/npm a mano ni mates el proceso
por PID** — `uvicorn --reload` levanta un proceso "worker" aparte, y
matarlo directamente puede dejarlo huérfano consumiendo ~400% de CPU. Usa
siempre `stop-dentia.ps1`.

### 2.1.1 Atajo rápido: verificar solo lo que cambió

Para el día a día (iterar sobre un cambio concreto, no un release), correr
la suite completa cada vez es lento y, si lo hace un agente, consume
muchos tokens de más revisando módulos que ni se tocaron. `scripts\verify-changed.ps1`
traduce `git diff` contra el último tag (o el que le indiques) a qué
módulos de backend y qué archivos de frontend cambiaron, y corre SOLO esas
pruebas:

```powershell
.\scripts\verify-changed.ps1              # compara contra el ultimo tag alcanzable
.\scripts\verify-changed.ps1 -Base v1.0.5 # compara contra una version especifica
.\scripts\verify-changed.ps1 -Full        # suite completa de siempre (ver 2.2/2.3)
```

Esto NO reemplaza una corrida completa antes de publicar un release real
(el pipeline de CI, paso 4, siempre corre todo sin acotar de todas
formas) — es para no pagar ese costo completo en cada iteración local.

### 2.2 Backend — pruebas automáticas

Desde PowerShell, en `backend/` (con el entorno virtual activado):

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m pytest -q          # pruebas unitarias e integración
python -m ruff check .       # estilo y errores comunes
python -m mypy app           # tipos
```

Si tocaste dependencias (`requirements.txt`), corre también:

```powershell
python -m pip_audit --strict
```

### 2.3 Frontend — pruebas automáticas

```powershell
cd frontend
npm run lint
npm run test
npm run build
```

### 2.4 Si tu cambio incluye una migración de Alembic

Aplícala en tu base local y confirma que no truena:

```powershell
cd backend
alembic upgrade head
```

Si quieres el nivel de rigor que se usa antes de publicar una versión real
(simular una instalación nueva desde cero, no solo "ya traía datos de
antes"), puedes vaciar una base de pruebas y volver a migrar — pero para el
trabajo diario, `alembic upgrade head` sobre tu base de desarrollo normal
es suficiente.

### 2.5 ¿Y si cambié algo en `deploy/vps/` (scripts, `docker-compose.yml`, el `Caddyfile`)?

Esos archivos no tienen una prueba automática que los ejecute de verdad
(no hay un VPS de prueba en CI) — revísalos a mano con cuidado, y ten en
cuenta que vas a tener que copiarlos al servidor por separado la primera
vez que despliegues ese cambio (sección 5.2 más abajo).

---

## 3. Subir el cambio a GitHub

Con todo en verde localmente:

```powershell
git add <archivos que cambiaste>
git commit -m "Explica brevemente el QUÉ y, si no es obvio, el POR QUÉ"
git push origin main
```

Nunca subas (y de hecho ya están en `.gitignore`):
- `backend/.env` / `frontend/.env` (contienen secretos locales).
- `docs/DENT-IA — Instalación segura en la nube*.pdf` (tiene la IP real del
  servidor y la cuenta de administración).
- Contraseñas reales de la clínica, en cualquier archivo.

**Esto todavía no toca el servidor ni publica nada instalable** — solo
actualiza el código en GitHub. El servidor sigue corriendo exactamente la
versión que ya tenía.

---

## 4. Publicar una versión (esto sí dispara el pipeline automático)

Antes o inmediatamente después de taggear, agrega la entrada de esta
versión en `docs/CONTROL_DE_CAMBIOS.md` (fecha, commits incluidos,
síntesis breve) -- es el historial de qué se publicó y cuándo, para no
tener que releer commits viejos para saber qué trae cada versión instalada.

Cuando tengas uno o varios commits listos para convertirse en una versión
instalable, créale una etiqueta de git y súbela:

```powershell
git tag v1.1.0
git push --tags
```

**Esto dispara automáticamente** `.github/workflows/release.yml` en
GitHub Actions. El pipeline corre, en este orden, y se detiene en el
primer paso que falle:

1. **Backend**: `pytest`, `ruff check`, `mypy`, `pip-audit`.
2. **Frontend**: `eslint`, `vitest`, `build`, `npm audit`.
3. **E2E**: Playwright contra un backend+frontend reales levantados en el
   propio runner de GitHub (login, flujo de paciente completo, etc.).
4. Si todo lo anterior pasó: construye las imágenes Docker
   (`dentia-api`, `dentia-web`), las escanea con Trivy, las firma con
   `cosign` (firma "keyless", sin llaves que administrar) y las publica en
   GHCR (`ghcr.io/dorodriguezv-tech/...`).
5. Publica un **GitHub Release** con el paquete
   `dentia-vps-<version>.tar.gz`, su `SHA256SUMS` y los SBOM de cada imagen.

Tarda aproximadamente **8-10 minutos**. Si cualquier paso falla, **no se
publica nada** — el servidor nunca ve una versión a medias.

### Cómo ver el avance

**Panel web — GitHub**: pestaña "Actions" del repositorio.

**O desde PowerShell**, con `gh` (ya instalado y autenticado en esta
máquina):

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" run list --repo dorodriguezv-tech/dentia-system --workflow release.yml --limit 3
& "C:\Program Files\GitHub CLI\gh.exe" run view <id-del-run> --repo dorodriguezv-tech/dentia-system
```

Si falla, ver el detalle del paso que truena:

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" run view <id-del-run> --repo dorodriguezv-tech/dentia-system --log-failed
```

### Si el release falla y necesitas corregir y reintentar

No se puede "editar" una etiqueta ya publicada. El patrón es: corregir el
código, hacer un commit nuevo, y volver a apuntar la misma etiqueta (o usar
una nueva, p. ej. `v1.1.1`) al commit corregido:

```powershell
git tag -d v1.1.0
git push origin :refs/tags/v1.1.0
git tag v1.1.0
git push origin v1.1.0
```

---

## 5. Desplegar en el servidor

Una vez que el release de GitHub terminó en verde, el servidor **sigue sin
enterarse** — hay que ir a buscarlo a propósito.

Conectarse primero:

```powershell
ssh -p 2222 deploy@179.236.83.142
```

### 5.1 Caso normal (solo cambió código de la app o hay una migración nueva)

El `~/vps` del servidor ya tiene los scripts y la configuración — solo
necesitas la versión nueva de las imágenes:

```bash
cd ~/vps
sudo ./scripts/deploy.sh <version> dentia-demo
```

`deploy.sh` hace, en orden (y se detiene si algo falla):
1. Respaldo inmediato (si ya existe `/etc/dentia/dentia-demo/secrets/restic.env`;
   si es la primerísima vez que se despliega ese proyecto, lo omite porque no
   hay nada que respaldar todavía).
2. Descarga las imágenes `dentia-api:<version>` y `dentia-web:<version>` de
   GHCR.
3. Aplica `alembic upgrade head` (las migraciones nuevas se aplican solas).
4. Reinicia `api` y `caddy` con las imágenes nuevas.
5. Verifica que `/api/v1/health` responda sano antes de darse por
   satisfecho.

### 5.2 Caso con cambios en `deploy/vps/scripts/`, `compose/docker-compose.yml`, el `Caddyfile`, o `systemd/`

Esos archivos **no se actualizan solos** en `~/vps` — el servidor sigue
usando la copia que quedó de la última vez que se descomprimió el paquete.
Dos formas de llevarlos:

**Opción A — descargar y re-extraer el paquete completo (más robusta, recomendada):**

```powershell
cd $env:USERPROFILE\Downloads
gh release download v1.1.0 --repo dorodriguezv-tech/dentia-system -p 'dentia-vps-1.1.0.tar.gz' -p 'SHA256SUMS'
sha256sum -c SHA256SUMS   # o Get-FileHash, ver INSTALACION_VPS.md sec. 3.1
scp -P 2222 .\dentia-vps-1.1.0.tar.gz deploy@179.236.83.142:~/
```

Y dentro del servidor:
```bash
cd ~
tar xzf dentia-vps-1.1.0.tar.gz
cp vps/compose/.env ~/vps_nuevo_env_backup 2>/dev/null  # por si acaso
rsync -a --exclude 'compose/.env' vps/ ~/vps/
sudo ./scripts/deploy.sh 1.1.0 dentia-demo
```

(El `.env` real de cada proyecto vive fuera del paquete, en
`compose/.env` dentro de `~/vps` — no lo pisa el paquete nuevo si usas
`rsync --exclude` como arriba; `install.sh` tampoco lo regenera si ya
existe.)

**Opción B — copiar solo el archivo puntual que cambió (más rápida para una corrección urgente):**

```powershell
scp -P 2222 C:\workspace\dentia-system\deploy\vps\scripts\deploy.sh deploy@179.236.83.142:~/vps/scripts/deploy.sh
```

Después de cualquiera de las dos, sigue igual que el caso normal:
`sudo ./scripts/deploy.sh <version> dentia-demo`.

### 5.3 Verificar que quedó bien

```bash
sudo docker compose --project-name dentia-demo --project-directory compose ps
```

Los tres contenedores (`api`, `caddy`, `db`) deben decir `Up`/`healthy`, sin
`Restarting`. Luego, desde el navegador (idealmente datos móviles, no la
misma red del servidor): entrar a `https://demo.dentia.digital`, iniciar
sesión, y probar el cambio de verdad.

Si algo no arranca, revisar los logs del servicio en cuestión:

```bash
sudo docker compose --project-name dentia-demo --project-directory compose logs -f caddy
sudo docker compose --project-name dentia-demo --project-directory compose logs -f api
```

---

## 6. Demo primero, producción después

**Nunca se despliega directo a `dentia-prod`.** El orden siempre es:

1. `sudo ./scripts/deploy.sh <version> dentia-demo`
2. Probar a fondo en `demo.dentia.digital` (con datos ficticios).
3. Solo si quedó bien: `sudo ./scripts/deploy.sh <version> dentia-prod`.

---

## 7. Si algo sale mal después de desplegar

Revertir a la versión anterior:

```bash
sudo ./scripts/rollback.sh <version-anterior> dentia-demo
```

Baja el esquema de la base de datos a la revisión que esa versión anterior
esperaba (lee las propias migraciones de la imagen vieja, no asume un
número a mano), vuelve a las imágenes de esa versión, y reinicia. Ver
`INSTALACION_VPS.md` sección 8 para el detalle, y sección 10 si se trata de
un incidente de seguridad (no solo un bug).

---

## Acordeón de comandos (una vez que ya conoces el flujo)

```powershell
# 1-2. Editar y verificar en local
cd backend; .venv\Scripts\Activate.ps1; python -m pytest -q; python -m ruff check .; python -m mypy app
cd ..\frontend; npm run lint; npm run test; npm run build

# 3. Subir a GitHub
git add <archivos>
git commit -m "mensaje"
git push origin main

# 4. Publicar version (dispara el pipeline)
git tag v1.1.0
git push --tags
# ... esperar ~10 min, revisar en GitHub Actions o con gh run view ...

# 5. Desplegar
ssh -p 2222 deploy@179.236.83.142
cd ~/vps
sudo ./scripts/deploy.sh 1.1.0 dentia-demo
sudo docker compose --project-name dentia-demo --project-directory compose ps
# probar en el navegador, datos moviles
# si ok:
sudo ./scripts/deploy.sh 1.1.0 dentia-prod
```
