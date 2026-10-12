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

.EXAMPLE
    .\scripts\start-dentia.ps1

.EXAMPLE
    .\scripts\start-dentia.ps1 -SkipDb
#>
param(
    [switch]$SkipDb,
    [switch]$SkipBackend,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"

function Write-Step([string]$Message) {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor Cyan
}

function Test-PortListening([int]$Port) {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
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
if ($SkipBackend) {
    Write-Step "Backend: se omite (-SkipBackend)."
} elseif (Test-PortListening 8001) {
    Write-Step "Backend: ya esta escuchando en el puerto 8001."
} else {
    Write-Step "Backend: abriendo ventana nueva (uvicorn, puerto 8001)..."
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "Set-Location '$BackendDir'; .\.venv\Scripts\Activate.ps1; alembic upgrade head; uvicorn app.main:app --reload --port 8001"
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

# 4. IA local (Ollama) -- solo informativo, nunca se arranca ni se detiene aqui
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
