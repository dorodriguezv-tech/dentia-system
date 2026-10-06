<#
.SYNOPSIS
    Prueba de restauracion de DentalCare (CLAUDE.md Fase 11): restaura el respaldo
    mas reciente (o uno especifico) en una base de datos TEMPORAL, la verifica y
    registra el resultado. Nunca toca la base de datos real de la aplicacion.

.DESCRIPTION
    Crear y borrar una base de datos requiere un rol con CREATEDB (el rol de la
    aplicacion, "dentia", no lo tiene a proposito -- menor privilegio posible). Por
    eso este script necesita credenciales de administrador de PostgreSQL, que NUNCA
    se piden como parametro ni se escriben en ningun archivo: se leen de las
    variables de entorno estandar de psql/pg_restore justo antes de ejecutarlo.

    Antes de correr este script:
        $env:PGPASSWORD = "<password del superusuario>"
    (y opcionalmente -AdminUser si no es "postgres"). La variable solo vive en la
    sesion de PowerShell actual.

    Pasos: decide que respaldo usar (el mas reciente en -BackupDir si no se da
    -BackupFile) -> si esta cifrado (.enc), lo descifra a un archivo temporal con
    OpenSSL y BACKUP_PASSPHRASE -> crea una base de datos nueva y desechable
    (-TestDbName) -> pg_restore ahi -> corre una consulta de verificacion (cuenta
    filas en tablas clave) -> si tambien existe un .zip de storage/ del mismo
    respaldo, lo descomprime en una carpeta temporal para confirmar que el archivo
    no esta corrupto -> limpia todo (borra la base de datos de prueba, el dump
    descifrado temporal y la carpeta de storage temporal) -> registra PASS o FAIL
    con el detalle en restore_test.log.

.PARAMETER BackupFile
    Ruta a un dentalcare_*_db.dump(.enc) especifico. Por defecto, el mas reciente.

.PARAMETER BackupDir
    Carpeta donde buscar respaldos. Por defecto <repo>\backups.

.PARAMETER TestDbName
    Nombre de la base de datos desechable. Por defecto "dentalcare_restore_test".

.PARAMETER AdminUser
    Rol de PostgreSQL con privilegio CREATEDB. Por defecto "postgres". La
    contrasena se lee de $env:PGPASSWORD (debe estar definida antes de llamar).

.EXAMPLE
    $env:PGPASSWORD = "..."
    .\scripts\restore_test.ps1
#>
param(
    [string]$BackupFile,
    [string]$BackupDir = (Join-Path (Split-Path -Parent $PSScriptRoot) "backups"),
    [string]$TestDbName = "dentalcare_restore_test",
    [string]$AdminUser = "postgres"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$LogFile = Join-Path $BackupDir "restore_test.log"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$TempDir = Join-Path $env:TEMP "dentalcare_restore_test_$Timestamp"

function Write-Log([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding utf8
}

function Find-PgTool([string]$Name) {
    $onPath = Get-Command $Name -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    $candidates = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\$Name.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending
    if ($candidates) { return $candidates[0].FullName }
    throw "No se encontro $Name.exe ni en PATH ni en C:\Program Files\PostgreSQL\*\bin."
}

function Find-OpenSsl {
    $onPath = Get-Command openssl -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    $gitBundled = "C:\Program Files\Git\mingw64\bin\openssl.exe"
    if (Test-Path $gitBundled) { return $gitBundled }
    return $null
}

if (-not $env:PGPASSWORD) {
    throw "Define `$env:PGPASSWORD con la contrasena del rol -AdminUser ($AdminUser) antes de llamar a este script."
}

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
$result = "FAIL"
$detail = ""

try {
    Write-Log "=== Iniciando prueba de restauracion $Timestamp ==="

    if (-not $BackupFile) {
        $latest = Get-ChildItem -Path $BackupDir -Filter "dentalcare_*_db.dump*" -File |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if (-not $latest) { throw "No hay respaldos en $BackupDir (dentalcare_*_db.dump*)." }
        $BackupFile = $latest.FullName
    }
    Write-Log "Respaldo a restaurar: $BackupFile"

    $dumpToRestore = $BackupFile
    if ($BackupFile -like "*.enc") {
        $passphrase = $env:BACKUP_PASSPHRASE
        if (-not $passphrase) { throw "El respaldo esta cifrado; define `$env:BACKUP_PASSPHRASE." }
        $openssl = Find-OpenSsl
        if (-not $openssl) { throw "El respaldo esta cifrado pero no se encontro OpenSSL." }
        $dumpToRestore = Join-Path $TempDir "db.dump"
        & $openssl enc -d -aes-256-cbc -pbkdf2 -pass "pass:$passphrase" -in $BackupFile -out $dumpToRestore
        if ($LASTEXITCODE -ne 0) { throw "No se pudo descifrar $BackupFile (¿passphrase incorrecta?)." }
        Write-Log "Descifrado a archivo temporal: $dumpToRestore"
    }

    $psql = Find-PgTool "psql"
    $createdb = Find-PgTool "createdb"
    $dropdb = Find-PgTool "dropdb"
    $pgRestore = Find-PgTool "pg_restore"

    & $dropdb --host=localhost --username=$AdminUser --if-exists $TestDbName
    & $createdb --host=localhost --username=$AdminUser $TestDbName
    Write-Log "Base de datos temporal creada: $TestDbName"

    & $pgRestore --host=localhost --username=$AdminUser --dbname=$TestDbName --no-owner --exit-on-error $dumpToRestore
    if ($LASTEXITCODE -ne 0) { throw "pg_restore termino con codigo $LASTEXITCODE" }
    Write-Log "pg_restore completado sin errores."

    $verifyQuery = "select (select count(*) from organizations) as organizations, (select count(*) from clinics) as clinics, (select count(*) from users) as users;"
    $verifyOutput = & $psql --host=localhost --username=$AdminUser --dbname=$TestDbName --tuples-only --no-align --command=$verifyQuery
    if ($LASTEXITCODE -ne 0) { throw "La consulta de verificacion fallo." }
    Write-Log "Verificacion (organizations|clinics|users): $verifyOutput"

    # Comilla simple a proposito: en una cadena con comillas dobles, PowerShell
    # interpola "$1" como una variable (vacia) antes de que -replace la vea, y la
    # referencia al grupo de captura del regex se pierde silenciosamente.
    $storageZip = $BackupFile -replace '_db\.dump(\.enc)?$', '_storage.zip$1'
    if (Test-Path $storageZip) {
        $zipToExtract = $storageZip
        if ($storageZip -like "*.enc") {
            $passphrase = $env:BACKUP_PASSPHRASE
            $openssl = Find-OpenSsl
            if ($passphrase -and $openssl) {
                $zipToExtract = Join-Path $TempDir "storage.zip"
                & $openssl enc -d -aes-256-cbc -pbkdf2 -pass "pass:$passphrase" -in $storageZip -out $zipToExtract
            } else {
                Write-Log "ADVERTENCIA: no se pudo descifrar $storageZip para verificarlo (sin passphrase u OpenSSL)."
                $zipToExtract = $null
            }
        }
        if ($zipToExtract) {
            $extractDir = Join-Path $TempDir "storage"
            Expand-Archive -Path $zipToExtract -DestinationPath $extractDir -Force
            $fileCount = (Get-ChildItem -Path $extractDir -Recurse -File).Count
            Write-Log "Archivo de storage/ verificado: $fileCount archivo(s) extraidos sin error."
        }
    } else {
        Write-Log "No se encontro un .zip de storage/ para este respaldo (puede no haberse generado)."
    }

    $result = "PASS"
    $detail = "organizations/clinics/users: $verifyOutput"
} catch {
    $detail = $_.Exception.Message
    Write-Log "ERROR: $detail"
} finally {
    $dropdb = Get-Command dropdb -ErrorAction SilentlyContinue
    if (-not $dropdb) {
        $candidates = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\dropdb.exe" -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending
        if ($candidates) { $dropdb = $candidates[0].FullName } else { $dropdb = $null }
    } else {
        $dropdb = $dropdb.Source
    }
    if ($dropdb) {
        & $dropdb --host=localhost --username=$AdminUser --if-exists $TestDbName 2>$null
        Write-Log "Base de datos temporal $TestDbName eliminada."
    }
    Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Log "=== Resultado: $result -- $detail ==="
if ($result -ne "PASS") { exit 1 }
