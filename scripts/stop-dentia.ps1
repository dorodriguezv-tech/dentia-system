<#
.SYNOPSIS
    Apaga DentalCare: cierra el backend (puerto 8001) y el frontend (puerto 5174),
    sin importar si se iniciaron con start-dentia.ps1, en una ventana manual, o en
    segundo plano (p. ej. nohup de Git Bash).

.DESCRIPTION
    Localiza el proceso que esta escuchando en cada puerto y cierra tambien el resto
    de su arbol de procesos propio: hacia arriba, el reloader de uvicorn (si no se
    detiene, uvicorn --reload vuelve a levantar el proceso hijo); hacia abajo,
    cualquier subproceso (p. ej. el worker de multiprocessing de uvicorn). El arbol
    nunca sube mas alla de python/uvicorn/node/npm -- nunca se toca la terminal,
    shell o ventana (powershell, cmd, bash, nohup) que los haya lanzado.

    La base de datos y Ollama NO se detienen por defecto: pueden estar en uso por
    otra cosa en la maquina. Usa -StopDb / -StopOllama para apagarlos tambien.

.PARAMETER StopDb
    Tambien detiene PostgreSQL (servicio nativo) o hace 'docker compose down' si
    aplica.

.PARAMETER StopOllama
    Tambien cierra Ollama (la app de bandeja de IA local).

.EXAMPLE
    .\scripts\stop-dentia.ps1

.EXAMPLE
    .\scripts\stop-dentia.ps1 -StopDb -StopOllama
#>
param(
    [switch]$StopDb,
    [switch]$StopOllama
)

$RepoRoot = Split-Path -Parent $PSScriptRoot

# Nombres de proceso que se consideran parte del arbol propio de la app (reloader
# de uvicorn, workers de python, node/npm del frontend). Deliberadamente NO incluye
# powershell/pwsh/cmd/bash/nohup: la terminal que lanzo el proceso nunca se toca.
$AppProcessNames = '^(python|uvicorn|node|npm)(\.exe)?$'

function Write-Step([string]$Message) {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor Cyan
}

function Get-OwnProcessTree([int]$RootProcessId, $AllProcesses) {
    $byId = @{}
    foreach ($p in $AllProcesses) { $byId[[int]$p.ProcessId] = $p }

    $result = [System.Collections.Generic.HashSet[int]]::new()
    if (-not $byId.ContainsKey($RootProcessId)) { return $result }
    [void]$result.Add($RootProcessId)

    # Subir por los padres mientras sigan siendo parte de la app (python/uvicorn/node/npm).
    $current = $byId[$RootProcessId]
    for ($i = 0; $i -lt 8; $i++) {
        $parentId = [int]$current.ParentProcessId
        if (-not $parentId -or -not $byId.ContainsKey($parentId)) { break }
        $parent = $byId[$parentId]
        if ($parent.Name -notmatch $AppProcessNames) { break }
        [void]$result.Add($parentId)
        $current = $parent
    }

    # Bajar por todos los descendientes del proceso que tiene el puerto abierto.
    $queue = [System.Collections.Generic.Queue[int]]::new()
    $queue.Enqueue($RootProcessId)
    while ($queue.Count -gt 0) {
        $pid0 = $queue.Dequeue()
        foreach ($p in $AllProcesses) {
            $childId = [int]$p.ProcessId
            if ([int]$p.ParentProcessId -eq $pid0 -and -not $result.Contains($childId)) {
                [void]$result.Add($childId)
                $queue.Enqueue($childId)
            }
        }
    }
    return $result
}

function Stop-ByPort([int]$Port, [string]$Name) {
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $conns) {
        Write-Step "$Name`: no hay nada escuchando en el puerto $Port."
        return
    }

    $allProcesses = Get-CimInstance Win32_Process
    $rootPids = $conns | Select-Object -ExpandProperty OwningProcess -Unique

    foreach ($rootPid in $rootPids) {
        $tree = Get-OwnProcessTree -RootProcessId $rootPid -AllProcesses $allProcesses
        foreach ($targetPid in $tree) {
            try {
                Stop-Process -Id $targetPid -Force -ErrorAction Stop
                Write-Step "$Name`: proceso $targetPid detenido."
            } catch {
                # Ya no existia o no se pudo cerrar -- seguimos con el resto del arbol.
            }
        }
    }
}

Stop-ByPort -Port 8001 -Name "Backend"
Stop-ByPort -Port 5174 -Name "Frontend"

if ($StopDb) {
    $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pgService -and $pgService.Status -eq "Running") {
        Write-Step "Base de datos: deteniendo servicio nativo '$($pgService.Name)'..."
        Stop-Service -Name $pgService.Name -Force
    } elseif (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Step "Base de datos: 'docker compose down'..."
        Push-Location $RepoRoot
        try { docker compose down } finally { Pop-Location }
    } else {
        Write-Step "Base de datos: no se encontro servicio nativo ni Docker, nada que detener."
    }
} else {
    Write-Step "Base de datos: no se toca (usa -StopDb para detenerla tambien)."
}

if ($StopOllama) {
    $ollama = Get-Process -Name "ollama*" -ErrorAction SilentlyContinue
    if ($ollama) {
        Write-Step "Ollama: deteniendo..."
        $ollama | Stop-Process -Force
    } else {
        Write-Step "Ollama: no esta corriendo."
    }
} else {
    Write-Step "Ollama: no se toca (usa -StopOllama para cerrarlo tambien)."
}

Write-Host ""
Write-Host "Listo."
