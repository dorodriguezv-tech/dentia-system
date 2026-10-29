<#
.SYNOPSIS
  Verificacion RAPIDA antes de un release: corre solo las pruebas de los
  modulos que de verdad cambiaron desde la ultima version (o la referencia
  que se indique), en vez de la suite completa de punta a punta.

.DESCRIPTION
  Complementa a docs/FLUJO_DE_TRABAJO.md seccion 2 ("Verificar en local
  antes de subir nada"). La suite completa (`pytest` sin acotar, `vitest
  run` completo) sigue siendo la referencia definitiva y la que corre el
  pipeline de CI antes de publicar de verdad -- este script es para el dia
  a dia: iterar rapido mientras se trabaja en un cambio concreto, sin
  pagar el costo (tiempo, memoria, tokens si lo corre un agente) de
  reverificar modulos que no se tocaron.

  Backend: traduce los archivos tocados (`git diff --name-only`) a
  carpetas `backend/app/modules/<nombre>/` (o `backend/app/<nombre>/` para
  voice/ai) y corre `pytest` acotado a `tests/unit/<nombre>
  tests/integration/<nombre>` de cada modulo detectado, cuando esa carpeta
  de pruebas existe.

  Frontend: usa `vitest run --changed <ref>`, que ya trae Vitest para
  correr solo las pruebas relacionadas (por analisis estatico de imports)
  con los archivos que cambiaron desde esa referencia -- no reinventa esa
  logica.

.PARAMETER Base
  Referencia de git contra la que comparar (default: el ultimo tag
  `vX.Y.Z` alcanzable desde HEAD -- el ultimo release publicado).

.PARAMETER Full
  Ignora todo lo anterior y corre la suite completa de siempre (pytest sin
  acotar + vitest run completo) -- util antes de un release real, como
  ultimo chequeo exhaustivo.

.EXAMPLE
  .\scripts\verify-changed.ps1
  Verifica solo lo que cambio desde el ultimo tag.

.EXAMPLE
  .\scripts\verify-changed.ps1 -Base v1.0.5
  Verifica todo lo que cambio desde v1.0.5 (varias versiones atras).

.EXAMPLE
  .\scripts\verify-changed.ps1 -Full
  Suite completa, sin acotar (equivalente a lo que ya hacia FLUJO_DE_TRABAJO.md).
#>
param(
    [string]$Base,
    [switch]$Full
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Write-Step($msg) {
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] $msg" -ForegroundColor Cyan
}

if (-not $Base) {
    $Base = git describe --tags --abbrev=0 2>$null
    if (-not $Base) {
        Write-Host "No hay ningun tag alcanzable -- usa -Full o pasa -Base explicito." -ForegroundColor Yellow
        exit 1
    }
}

if ($Full) {
    Write-Step "Modo -Full: suite completa, sin acotar."

    Write-Step "Backend: pytest completo"
    Push-Location "$repoRoot\backend"
    try { & .\.venv\Scripts\python.exe -m pytest -q; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
    finally { Pop-Location }

    Write-Step "Frontend: vitest run completo"
    Push-Location "$repoRoot\frontend"
    try { npx vitest run; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
    finally { Pop-Location }

    Write-Step "Listo (modo completo)."
    exit 0
}

Write-Step "Comparando contra $Base..."
$changedFiles = git diff --name-only "$Base...HEAD"
if (-not $changedFiles) {
    Write-Host "Nada cambio desde $Base -- nada que verificar." -ForegroundColor Yellow
    exit 0
}

# --- Backend: deriva que modulos de backend/app/modules/<nombre>/ (o
# backend/app/<nombre>/ para voice/ai, que viven fuera de modules/) se
# tocaron, y arma la lista de carpetas de pruebas correspondientes que de
# verdad existen en el repo.
$backendModules = New-Object System.Collections.Generic.HashSet[string]
foreach ($f in $changedFiles) {
    if ($f -match '^backend/app/modules/([^/]+)/') { [void]$backendModules.Add($Matches[1]) }
    elseif ($f -match '^backend/app/(voice|ai)/') { [void]$backendModules.Add($Matches[1]) }
}

$backendTestPaths = @()
foreach ($m in $backendModules) {
    foreach ($kind in @("unit", "integration")) {
        $p = "tests/$kind/$m"
        if (Test-Path "$repoRoot\backend\$p") { $backendTestPaths += $p }
    }
}

if ($backendTestPaths.Count -gt 0) {
    Write-Step "Backend: modulos tocados -> $($backendModules -join ', ')"
    Write-Step "Backend: pytest -q $($backendTestPaths -join ' ')"
    Push-Location "$repoRoot\backend"
    try {
        & .\.venv\Scripts\python.exe -m pytest -q @backendTestPaths
        if ($LASTEXITCODE -ne 0) { Write-Host "Backend: hay fallos reales, revisa arriba." -ForegroundColor Red; exit $LASTEXITCODE }
    } finally { Pop-Location }
} else {
    Write-Step "Backend: sin cambios en backend/app/modules|voice|ai -- se omite pytest."
}

# --- Frontend: le delega a Vitest su propio --changed (analisis estatico
# de imports contra el ref de git), no reinventa el mapeo de archivo a
# prueba.
$frontendChanged = $changedFiles | Where-Object { $_ -like 'frontend/*' }
if ($frontendChanged) {
    Write-Step "Frontend: vitest run --changed $Base"
    Push-Location "$repoRoot\frontend"
    try {
        npx vitest run --changed $Base
        if ($LASTEXITCODE -ne 0) { Write-Host "Frontend: hay fallos reales, revisa arriba." -ForegroundColor Red; exit $LASTEXITCODE }
    } finally { Pop-Location }
} else {
    Write-Step "Frontend: sin cambios en frontend/ -- se omite vitest."
}

Write-Step "Listo. Antes de publicar un release de verdad, corre ademas -Full al menos una vez (y el pipeline de CI lo corre completo de todos modos)."
