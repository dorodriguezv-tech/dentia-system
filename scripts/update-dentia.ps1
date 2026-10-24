<#
.SYNOPSIS
    Actualiza DENT-IA en el servidor de produccion a una etiqueta de git nueva
    (docs/INSTALACION_PRODUCCION.md, "Actualizaciones"). Es el "paquete que
    puede actualizarse": cada version se publica como un tag y esto reproduce el
    procedimiento de la guia paso a paso, siempre con respaldo antes y una forma
    de revertir si algo sale mal.

.DESCRIPTION
    Correr como Administrador, parado en cualquier carpeta (usa -DentiaRoot para
    ubicar C:\Dentia). Antes de correr esto en produccion, probar la misma
    etiqueta en un ambiente demo (ver instructivo).

.PARAMETER Tag
    Etiqueta de git a publicar, p. ej. v1.1.0.

.PARAMETER DentiaRoot
    Carpeta base (C:\Dentia por defecto).

.PARAMETER SkipBackup
    No corre scripts\backup.ps1 antes de actualizar (usar solo si ya se hizo
    un respaldo manual hace poco).

.EXAMPLE
    .\scripts\update-dentia.ps1 -Tag v1.1.0
#>
param(
    [Parameter(Mandatory = $true)][string]$Tag,
    [string]$DentiaRoot = "C:\Dentia",
    [switch]$SkipBackup
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor Cyan
}

$AppDir = Join-Path $DentiaRoot "app"
$BackendDir = Join-Path $AppDir "backend"
$FrontendDir = Join-Path $AppDir "frontend"
$ToolsDir = Join-Path $DentiaRoot "tools"
$WwwDir = Join-Path $DentiaRoot "www"
$nssm = Join-Path $ToolsDir "nssm.exe"

if (-not (Test-Path $AppDir)) { throw "No se encontro $AppDir. Esto no es un servidor ya instalado -- usa install-dentia.ps1 primero." }

# 1. Respaldo inmediato: si algo sale mal, esta es la red de seguridad.
if ($SkipBackup) {
    Write-Step "Respaldo: se omite (-SkipBackup)."
} else {
    Write-Step "Respaldo antes de actualizar..."
    & (Join-Path $PSScriptRoot "backup.ps1")
}

$previousTag = (git -C $AppDir describe --tags --abbrev=0 2>$null)
Write-Step "Version actual: $(if ($previousTag) { $previousTag } else { '(sin etiqueta)' }) -> actualizando a $Tag"

# 2. Detener la API (no el frontend: puede seguir sirviendo mientras se
# actualiza el backend, aunque /api/* falle brevemente).
Write-Step "Deteniendo DentiaAPI..."
& $nssm stop DentiaAPI

# 3. Codigo: fetch + checkout de la etiqueta.
Push-Location $AppDir
try {
    git fetch --tags
    git checkout $Tag
} finally {
    Pop-Location
}

# 4. Backend: dependencias + migraciones.
Write-Step "Backend: dependencias y migraciones..."
Push-Location $BackendDir
try {
    & .\.venv\Scripts\pip.exe install -q -r requirements.txt
    & .\.venv\Scripts\alembic.exe upgrade head
} finally {
    Pop-Location
}

# 5. Reiniciar la API.
Write-Step "Iniciando DentiaAPI..."
& $nssm start DentiaAPI
Start-Sleep -Seconds 3
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/v1/health" -TimeoutSec 10
    Write-Host "API: $($health.status)" -ForegroundColor Green
} catch {
    Write-Warning "La API no respondio despues de actualizar. Revisa C:\DentiaData\logs\api.log."
    Write-Warning "Para revertir: .\scripts\update-dentia.ps1 -Tag $previousTag -SkipBackup (y si una migracion alteto datos, ver 'Reversion' en el instructivo -- puede requerir restaurar el respaldo del paso 1 en vez de un downgrade)."
    throw
}

# 6. Frontend: recompilar y publicar.
Write-Step "Frontend: compilando..."
Push-Location $FrontendDir
try {
    npm ci
    npm run build
} finally {
    Pop-Location
}
robocopy (Join-Path $FrontendDir "dist") $WwwDir /MIR | Out-Null

# 7. Si cambio el Caddyfile, reiniciar DentiaWeb tambien (barato, siempre seguro).
Write-Step "Reiniciando DentiaWeb..."
& $nssm restart DentiaWeb

Write-Host ""
Write-Host "Actualizado a $Tag." -ForegroundColor Green
Write-Host "Prueba rapida pendiente (manual): /api/v1/health, login, abrir un paciente, odontograma y un PDF -- ver checklist en docs/INSTALACION_PRODUCCION.md."
