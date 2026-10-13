<#
.SYNOPSIS
    Levanta DentalCare completo: base de datos, backend (API) y frontend, cada uno
    en su propia ventana de PowerShell. Automatiza los pasos manuales de
    docs/INICIO_RAPIDO.md.

.DESCRIPTION
    Si un servicio ya esta corriendo (su puerto ya esta escuchando) lo detecta y no
    abre una ventana duplicada. La base de datos se levanta como servicio nativo de
    Windows (postgresql-x64-*) si existe, o con `docker compose up -d db` si no hay
    servicio nativo pero si Docker.

    Ollama (IA local) NO se arranca desde este script: en esta maquina corre como
    app de bandeja que inicia sola con Windows (ver docs/INICIO_RAPIDO.md seccion
    4). El script solo informa si lo detecta en el puerto 11434.

.PARAMETER SkipDb
    No intenta levantar la base de datos.

.PARAMETER SkipBackend
    No levanta el backend (API).

.PARAMETER SkipFrontend
    No levanta el frontend.

.PARAMETER Mobile
    Tambien levanta el cliente movil (Metro/expo, puerto 8081). No forma parte del
    arranque por defecto porque es un cliente aparte del frontend web, no algo que
    se necesite en cada sesion.

.EXAMPLE
    .\scripts\start-dentia.ps1

.EXAMPLE
    .\scripts\start-dentia.ps1 -SkipDb

.EXAMPLE
    .\scripts\start-dentia.ps1 -Mobile
#>
param(
    [switch]$SkipDb,
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$Mobile
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"
$MobileDir = Join-Path $RepoRoot "mobile"

function Write-Step([string]$Message) {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor Cyan
}

function Test-PortListening([int]$Port) {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Test-PortListeningOnAllInterfaces([int]$Port) {
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return [bool]($conns | Where-Object { $_.LocalAddress -in @('0.0.0.0', '::') })
}

function Wait-ForPort([int]$Port, [string]$Name, [int]$TimeoutS = 60) {
    $deadline = (Get-Date).AddSeconds($TimeoutS)
    while (-not (Test-PortListening $Port)) {
        if ((Get-Date) -gt $deadline) {
            Write-Warning "$Name no respondio en el puerto $Port tras $TimeoutS s. Revisa la ventana que se abrio."
            return $false
        }
        Start-Sleep -Milliseconds 500
    }
    return $true
}

# 1. Base de datos
if ($SkipDb) {
    Write-Step "Base de datos: se omite (-SkipDb)."
} elseif (Test-PortListening 5432) {
    Write-Step "Base de datos: ya esta escuchando en el puerto 5432."
} else {
    $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pgService) {
        Write-Step "Base de datos: iniciando servicio nativo '$($pgService.Name)'..."
        Start-Service -Name $pgService.Name
        Wait-ForPort 5432 "PostgreSQL" 30 | Out-Null
    } elseif (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Step "Base de datos: no hay servicio nativo instalado, usando 'docker compose up -d db'..."
        Push-Location $RepoRoot
        try { docker compose up -d db } finally { Pop-Location }
        Wait-ForPort 5432 "PostgreSQL (docker)" 60 | Out-Null
    } else {
        Write-Warning "No se encontro un servicio de PostgreSQL nativo ni Docker. Levanta la base de datos manualmente antes de seguir."
    }
}

# 2. Backend
# docs/05_APP_MOVIL.md Sec. 4.1: un telefono (a diferencia del navegador del
# frontend web, que corre en esta misma maquina) necesita que uvicorn escuche en
# todas las interfaces (--host 0.0.0.0), no solo en localhost. Si no se pide
# -Mobile, se deja el comportamiento de siempre (solo localhost basta).
$backendHostArgs = if ($Mobile) { "--host 0.0.0.0" } else { "" }
if ($SkipBackend) {
    Write-Step "Backend: se omite (-SkipBackend)."
} elseif (Test-PortListening 8001) {
    if ($Mobile -and -not (Test-PortListeningOnAllInterfaces 8001)) {
        Write-Warning "Backend: ya esta escuchando en el puerto 8001, pero solo en localhost (no se vio con --host 0.0.0.0). El telefono NO podra conectarse asi. Cierralo (.\scripts\stop-dentia.ps1) y vuelve a correr este script con -Mobile."
    } else {
        Write-Step "Backend: ya esta escuchando en el puerto 8001."
    }
} else {
    Write-Step "Backend: abriendo ventana nueva (uvicorn, puerto 8001$(if ($Mobile) { ', visible en la red (--host 0.0.0.0)' }))..."
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "Set-Location '$BackendDir'; .\.venv\Scripts\Activate.ps1; alembic upgrade head; uvicorn app.main:app --reload --port 8001 $backendHostArgs"
    ) | Out-Null
    Wait-ForPort 8001 "Backend" 60 | Out-Null
}

# 3. Frontend
if ($SkipFrontend) {
    Write-Step "Frontend: se omite (-SkipFrontend)."
} elseif (Test-PortListening 5174) {
    Write-Step "Frontend: ya esta escuchando en el puerto 5174."
} else {
    Write-Step "Frontend: abriendo ventana nueva (vite, puerto 5174)..."
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "Set-Location '$FrontendDir'; npm run dev"
    ) | Out-Null
    Wait-ForPort 5174 "Frontend" 60 | Out-Null
}

# 4. Cliente movil (Metro/expo) -- opcional, no forma parte del arranque por defecto
if (-not $Mobile) {
    Write-Step "Movil: se omite (usa -Mobile para levantarlo tambien)."
} elseif (Test-PortListening 8081) {
    Write-Step "Movil: ya esta escuchando en el puerto 8081."
} else {
    Write-Step "Movil: abriendo ventana nueva (npx expo start --dev-client, puerto 8081)..."
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "Set-Location '$MobileDir'; npx expo start --dev-client"
    ) | Out-Null
    Wait-ForPort 8081 "Movil (Metro)" 60 | Out-Null
}

# 5. IA local (Ollama) -- solo informativo, nunca se arranca ni se detiene aqui
try {
    $null = Invoke-RestMethod -Uri "http://localhost:11434/api/version" -TimeoutSec 2
    Write-Step "IA local (Ollama): detectado en el puerto 11434."
} catch {
    Write-Warning "IA local (Ollama): no responde en el puerto 11434. Si lo necesitas, revisa docs/INICIO_RAPIDO.md seccion 4 (ollama serve)."
}

Write-Host ""
Write-Host "Listo. URLs:"
Write-Host "  API:       http://localhost:8001/api/v1/health"
Write-Host "  Frontend:  http://localhost:5174"
if ($Mobile) {
    Write-Host "  Movil:     http://localhost:8081 (Metro -- abre la app DENT-IA en el telefono)"

    $tailscaleIp = $null
    if (Get-Command tailscale -ErrorAction SilentlyContinue) {
        try { $tailscaleIp = (tailscale ip -4 2>$null | Select-Object -First 1) } catch {}
    }
    if ($tailscaleIp) {
        Write-Host "  Servidor (pantalla 'Servidor' de la app, por Tailscale): http://$($tailscaleIp):8001"
    } else {
        Write-Warning "No se detecto Tailscale corriendo. Si el telefono se conecta por Tailscale, verifica que 'tailscale status' lo muestre activo."
    }
}
