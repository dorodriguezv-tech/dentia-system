<#
.SYNOPSIS
    Instalacion de produccion de DENT-IA en un servidor Windows (ver
    docs/INSTALACION_PRODUCCION.md). Deja la API y el frontend corriendo como
    servicios de Windows (NSSM), listos para que install-dentia-tunnel.ps1 (o el
    panel de Cloudflare, sec. 5 del instructivo) los publique por el tunel.

.DESCRIPTION
    Se corre UNA vez, como Administrador, parado dentro de C:\Dentia\app (el clon
    del repositorio ya hecho -- ver sec. 3 del instructivo). Es idempotente donde
    es razonable (no reinstala Postgres, no reescribe un .env que ya existe), pero
    no esta pensado para correrse dos veces sin revisar que hizo la primera.

    No crea la base de datos de PostgreSQL por ti si ya la creaste a mano (sec. 4
    del instructivo); con -SkipPostgres se salta ese paso por completo. Tampoco
    crea el tunel de Cloudflare ni los usuarios de la clinica -- eso es
    deliberadamente manual (requiere tu cuenta de Cloudflare) y
    app\bootstrap_clinic.py respectivamente, ver el instructivo.

.PARAMETER DentiaRoot
    Carpeta del codigo (C:\Dentia por defecto, ver docs/INSTALACION_PRODUCCION.md).

.PARAMETER DataRoot
    Carpeta de datos (C:\DentiaData por defecto).

.PARAMETER SkipPostgres
    No crea el rol ni la base de datos de PostgreSQL (si ya los creaste a mano).

.PARAMETER PostgresSuperPassword
    Contraseña del superusuario "postgres", SOLO para crear el rol de la app.
    Si se omite y no se da -SkipPostgres, se pide de forma segura (sin eco).

.PARAMETER DbPassword
    Contraseña del rol de la aplicacion ("dentia"). Si se omite, se pide de
    forma segura.

.EXAMPLE
    .\scripts\install-dentia.ps1
#>
param(
    [string]$DentiaRoot = "C:\Dentia",
    [string]$DataRoot = "C:\DentiaData",
    [switch]$SkipPostgres,
    [SecureString]$PostgresSuperPassword,
    [SecureString]$DbPassword
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor Cyan
}

$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
    throw "Corre este script como Administrador (clic derecho -> 'Ejecutar como administrador')."
}

$AppDir = Join-Path $DentiaRoot "app"
$BackendDir = Join-Path $AppDir "backend"
$FrontendDir = Join-Path $AppDir "frontend"
$ToolsDir = Join-Path $DentiaRoot "tools"
$WwwDir = Join-Path $DentiaRoot "www"

if (-not (Test-Path $AppDir)) {
    throw "No se encontro $AppDir. Clona el repositorio en $AppDir primero (sec. 3 del instructivo) y vuelve a correr este script parado ahi."
}

# 1. Carpetas de datos (fuera del clon de git: se respaldan y permisan aparte).
Write-Step "Creando carpetas de datos en $DataRoot..."
foreach ($dir in @("storage", "backups", "logs")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $DataRoot $dir) | Out-Null
}
New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null

# 2. PostgreSQL: rol y base de la aplicacion.
if ($SkipPostgres) {
    Write-Step "PostgreSQL: se omite (-SkipPostgres)."
} else {
    $psql = Get-Command psql.exe -ErrorAction SilentlyContinue
    if (-not $psql) {
        throw "No se encontro psql.exe en PATH. Instala PostgreSQL 16 primero (sec. 2 del instructivo) o usa -SkipPostgres si ya creaste el rol y la base a mano."
    }
    if (-not $PostgresSuperPassword) {
        $PostgresSuperPassword = Read-Host -AsSecureString "Contrasena del superusuario 'postgres'"
    }
    if (-not $DbPassword) {
        $DbPassword = Read-Host -AsSecureString "Contrasena para el rol de la app 'dentia'"
    }
    $superPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($PostgresSuperPassword))
    $dbPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($DbPassword))

    Write-Step "PostgreSQL: creando rol y base (si no existen)..."
    $env:PGPASSWORD = $superPlain
    # CREATE ROLE/DATABASE no tienen "IF NOT EXISTS" portable en todas las
    # versiones -- se checa antes para que el script sea seguro de repetir.
    $roleExists = (& psql -U postgres -h localhost -tAc "SELECT 1 FROM pg_roles WHERE rolname='dentia'") 2>$null
    if ($roleExists -ne "1") {
        $escaped = $dbPlain -replace "'", "''"
        & psql -U postgres -h localhost -c "CREATE ROLE dentia LOGIN PASSWORD '$escaped';"
    } else {
        Write-Host "  Rol 'dentia' ya existia."
    }
    $dbExists = (& psql -U postgres -h localhost -tAc "SELECT 1 FROM pg_database WHERE datname='dentia'") 2>$null
    if ($dbExists -ne "1") {
        & psql -U postgres -h localhost -c "CREATE DATABASE dentia OWNER dentia;"
    } else {
        Write-Host "  Base 'dentia' ya existia."
    }
    # Extensiones usadas por las migraciones (pg_trgm, unaccent, btree_gist):
    # las crea el superusuario porque el rol de la app no tiene permiso
    # (deliberado, sec. 5 del instructivo PDF: "el rol de la app sin CREATEDB
    # ni superusuario").
    foreach ($ext in @("pg_trgm", "unaccent", "btree_gist")) {
        & psql -U postgres -h localhost -d dentia -c "CREATE EXTENSION IF NOT EXISTS $ext;"
    }
    Remove-Item Env:\PGPASSWORD
}

# 3. Backend: venv, dependencias, .env, migraciones.
Write-Step "Backend: creando entorno virtual e instalando dependencias..."
Push-Location $BackendDir
try {
    if (-not (Test-Path ".venv")) { python -m venv .venv }
    & .\.venv\Scripts\pip.exe install -q -r requirements.txt

    if (-not (Test-Path ".env")) {
        Copy-Item ".env.production.example" ".env"
        Write-Warning "Se creo backend\.env desde la plantilla. EDITALO antes de continuar: JWT_SECRET, DATABASE_URL (contrasena), CORS_ORIGINS, TURNSTILE_SECRET_KEY (sec. 6 del instructivo). Presiona Enter cuando ya lo hayas guardado."
        Read-Host | Out-Null
    } else {
        Write-Host "  backend\.env ya existia, no se toco."
    }

    Write-Step "Backend: aplicando migraciones..."
    & .\.venv\Scripts\alembic.exe upgrade head
} finally {
    Pop-Location
}

# 4. Servicio de la API (NSSM) -- sin --reload, con --workers y cabeceras de
# proxy para que AuditEvent.ip registre la IP real detras de Caddy/Cloudflare
# (PDF sec. 5, bloqueante #3 y #4).
$nssm = Join-Path $ToolsDir "nssm.exe"
if (-not (Test-Path $nssm)) {
    throw "Falta $nssm. Descarga NSSM (https://nssm.cc) y copia nssm.exe ahi (sec. 2 del instructivo)."
}

Write-Step "Registrando el servicio DentiaAPI..."
$pythonExe = Join-Path $BackendDir ".venv\Scripts\python.exe"
& $nssm install DentiaAPI $pythonExe "-m uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 2 --proxy-headers --forwarded-allow-ips 127.0.0.1"
& $nssm set DentiaAPI AppDirectory $BackendDir
& $nssm set DentiaAPI AppStdout (Join-Path $DataRoot "logs\api.log")
& $nssm set DentiaAPI AppStderr (Join-Path $DataRoot "logs\api.log")
& $nssm set DentiaAPI AppRotateFiles 1
& $nssm set DentiaAPI AppRotateBytes 10485760
& $nssm set DentiaAPI Start SERVICE_AUTO_START
Write-Warning "DentiaAPI quedo registrado corriendo como el usuario que instalo el servicio. Para usar la cuenta dedicada dentia-svc (recomendado, sec. 2 del instructivo): nssm set DentiaAPI ObjectName '.\dentia-svc' '<password>'"

# 5. Frontend: compilar y publicar.
Write-Step "Frontend: compilando..."
Push-Location $FrontendDir
try {
    if (-not (Test-Path ".env.production")) {
        Copy-Item ".env.production.example" ".env.production"
        Write-Warning "Se creo frontend\.env.production desde la plantilla. Revisa VITE_API_URL y VITE_TURNSTILE_SITE_KEY antes de seguir. Presiona Enter cuando ya lo hayas guardado."
        Read-Host | Out-Null
    }
    npm ci
    npm run build
} finally {
    Pop-Location
}
robocopy (Join-Path $FrontendDir "dist") $WwwDir /MIR | Out-Null

# 6. Servicio web (Caddy, NSSM).
$caddy = Join-Path $ToolsDir "caddy.exe"
if (-not (Test-Path $caddy)) {
    throw "Falta $caddy. Descarga Caddy para Windows (https://caddyserver.com/download) y copia caddy.exe ahi (sec. 2 del instructivo)."
}
Write-Step "Registrando el servicio DentiaWeb..."
& $nssm install DentiaWeb $caddy "run --config $(Join-Path $AppDir 'deploy\caddy\Caddyfile')"
& $nssm set DentiaWeb AppDirectory $DentiaRoot
& $nssm set DentiaWeb Start SERVICE_AUTO_START

# 7. Arrancar y probar.
Write-Step "Iniciando servicios..."
& $nssm start DentiaAPI
& $nssm start DentiaWeb
Start-Sleep -Seconds 3

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/v1/health" -TimeoutSec 10
    Write-Host "API: $($health.status)" -ForegroundColor Green
} catch {
    Write-Warning "La API no respondio en 127.0.0.1:8001/api/v1/health. Revisa $DataRoot\logs\api.log."
}
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:8080" -TimeoutSec 10 -UseBasicParsing | Out-Null
    Write-Host "Frontend (Caddy): responde en 127.0.0.1:8080" -ForegroundColor Green
} catch {
    Write-Warning "Caddy no respondio en 127.0.0.1:8080. Revisa el Visor de eventos de Windows -> DentiaWeb."
}

Write-Host ""
Write-Host "Instalacion local lista. Lo que falta, siempre manual (ver docs/INSTALACION_PRODUCCION.md):"
Write-Host "  1. Crear los 3 usuarios de la clinica: ver 'Alta de usuarios' en el instructivo (app\bootstrap_clinic.py)."
Write-Host "  2. Tunel de Cloudflare, Access y Turnstile (sec. 7 y 8 del instructivo) -- requieren tu cuenta de Cloudflare."
Write-Host "  3. Recorrer el checklist final (sec. 10 del instructivo) antes de cargar pacientes reales."
