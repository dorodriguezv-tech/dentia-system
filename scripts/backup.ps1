<#
.SYNOPSIS
    Respaldo de DentalCare (CLAUDE.md Fase 11): pg_dump de la base de datos +
    storage/ (archivos subidos), ambos cifrados si hay OpenSSL disponible, con
    retencion automatica de respaldos antiguos.

.DESCRIPTION
    Lee las credenciales de la base de datos de backend\.env (el mismo archivo que
    usa la API; nunca se piden ni se vuelven a escribir en ningun otro lado). Genera
    dos archivos por corrida en -BackupDir:
      dentalcare_<timestamp>_db.dump[.enc]      (pg_dump formato custom)
      dentalcare_<timestamp>_storage.zip[.enc]  (carpeta storage/ completa)

    El cifrado usa OpenSSL (AES-256-CBC + PBKDF2) con la frase de paso en la
    variable de entorno BACKUP_PASSPHRASE. Si OpenSSL no esta disponible o la
    variable no esta definida, el respaldo se guarda SIN cifrar y se registra una
    advertencia clara en la consola y en el log -- nunca falla la corrida solo por
    no poder cifrar, para que el respaldo nocturno programado no se interrumpa,
    pero el operador debe revisar el log.

.PARAMETER BackupDir
    Carpeta donde se guardan los respaldos. Por defecto <repo>\backups.

.PARAMETER RetentionDays
    Cuantos dias conservar respaldos anteriores antes de borrarlos. Por defecto 30.

.EXAMPLE
    .\scripts\backup.ps1
    .\scripts\backup.ps1 -BackupDir D:\respaldos-dentalcare -RetentionDays 14
#>
param(
    [string]$BackupDir = (Join-Path (Split-Path -Parent $PSScriptRoot) "backups"),
    [int]$RetentionDays = 30
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $RepoRoot "backend\.env"
$StorageDir = Join-Path $RepoRoot "storage"
$LogFile = Join-Path $BackupDir "backup.log"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

function Write-Log([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding utf8
}

function Read-EnvValue([string]$Path, [string]$Key) {
    if (-not (Test-Path $Path)) {
        throw "No se encontro $Path -- copia backend\.env.example a backend\.env primero."
    }
    $line = Get-Content $Path | Where-Object { $_ -match "^\s*$Key\s*=" } | Select-Object -First 1
    if (-not $line) { throw "La variable $Key no esta definida en $Path" }
    return ($line -split "=", 2)[1].Trim()
}

function Find-PgTool([string]$Name) {
    $onPath = Get-Command $Name -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    $candidates = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\$Name.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending
    if ($candidates) { return $candidates[0].FullName }
    throw "No se encontro $Name.exe ni en PATH ni en C:\Program Files\PostgreSQL\*\bin -- instala el cliente de PostgreSQL."
}

function Find-OpenSsl {
    $onPath = Get-Command openssl -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    $gitBundled = "C:\Program Files\Git\mingw64\bin\openssl.exe"
    if (Test-Path $gitBundled) { return $gitBundled }
    return $null
}

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

Write-Log "=== Iniciando respaldo $Timestamp ==="

$PgUser = Read-EnvValue $EnvFile "POSTGRES_USER"
$PgPassword = Read-EnvValue $EnvFile "POSTGRES_PASSWORD"
$PgDatabase = Read-EnvValue $EnvFile "POSTGRES_DB"
$PgDump = Find-PgTool "pg_dump"

$DbDumpPath = Join-Path $BackupDir "dentalcare_${Timestamp}_db.dump"
$StorageZipPath = Join-Path $BackupDir "dentalcare_${Timestamp}_storage.zip"

try {
    $env:PGPASSWORD = $PgPassword
    & $PgDump --host=localhost --username=$PgUser --format=custom --file=$DbDumpPath $PgDatabase
    if ($LASTEXITCODE -ne 0) { throw "pg_dump termino con codigo $LASTEXITCODE" }
    Write-Log "Volcado de base de datos creado: $DbDumpPath ($((Get-Item $DbDumpPath).Length) bytes)"
} finally {
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

if (Test-Path $StorageDir) {
    Compress-Archive -Path (Join-Path $StorageDir "*") -DestinationPath $StorageZipPath -Force
    Write-Log "Archivo de storage/ creado: $StorageZipPath ($((Get-Item $StorageZipPath).Length) bytes)"
} else {
    Write-Log "ADVERTENCIA: $StorageDir no existe, se omite el respaldo de archivos."
}

$OpenSsl = Find-OpenSsl
$Passphrase = $env:BACKUP_PASSPHRASE

if ($OpenSsl -and $Passphrase) {
    foreach ($plainPath in @($DbDumpPath, $StorageZipPath)) {
        if (-not (Test-Path $plainPath)) { continue }
        $encPath = "$plainPath.enc"
        & $OpenSsl enc -aes-256-cbc -pbkdf2 -salt -pass "pass:$Passphrase" -in $plainPath -out $encPath
        if ($LASTEXITCODE -ne 0) {
            Write-Log "ADVERTENCIA: fallo el cifrado de $plainPath, se conserva sin cifrar."
            continue
        }
        Remove-Item $plainPath -Force
        Write-Log "Cifrado: $encPath"
    }
} else {
    $reason = if (-not $OpenSsl) { "no se encontro OpenSSL" } else { "falta la variable de entorno BACKUP_PASSPHRASE" }
    Write-Log "ADVERTENCIA: respaldo guardado SIN CIFRAR ($reason). Ver docs/OPERACION.md seccion de cifrado."
}

$cutoff = (Get-Date).AddDays(-$RetentionDays)
$removed = 0
Get-ChildItem -Path $BackupDir -Filter "dentalcare_*" -File | Where-Object { $_.LastWriteTime -lt $cutoff } | ForEach-Object {
    Remove-Item $_.FullName -Force
    $removed++
}
if ($removed -gt 0) {
    Write-Log "Retencion: $removed archivo(s) de mas de $RetentionDays dias eliminado(s)."
}

Write-Log "=== Respaldo $Timestamp terminado ==="
