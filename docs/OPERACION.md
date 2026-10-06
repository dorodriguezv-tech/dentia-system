# Operación: respaldos y continuidad (CLAUDE.md Fase 11)

Este documento explica cómo respaldar DentalCare, cómo probar que un respaldo
realmente sirve para recuperar el sistema, y cómo programar ambas cosas en Windows
y en Linux. Los scripts viven en `scripts/` (`.ps1` para Windows, `.sh` para
Linux/Mac — hacen exactamente lo mismo).

## 1. Qué se respalda

Cada corrida de `scripts/backup.ps1` (o `backup.sh`) genera dos archivos con el
mismo timestamp en la carpeta de respaldos (por defecto `<repo>/backups/`, fuera
del control de versiones — ver `.gitignore`):

| Archivo | Contenido |
|---|---|
| `dentalcare_<fecha>_db.dump` | Volcado completo de PostgreSQL (`pg_dump --format=custom`) |
| `dentalcare_<fecha>_storage.zip` | La carpeta `storage/` completa (expedientes, imágenes, PDFs firmados) |

Si hay una frase de paso configurada (sección 3), ambos quedan cifrados como
`*.enc` y el original sin cifrar se borra. El script nunca necesita credenciales
de administrador de PostgreSQL — usa el mismo rol de aplicación (`dentia`) que ya
tiene `backend/.env`, con permiso de solo lectura sobre su propia base.

## 2. Correr un respaldo manualmente

```powershell
# Windows
cd C:\workspace\dentia-system
.\scripts\backup.ps1
# con carpeta y retención distintas:
.\scripts\backup.ps1 -BackupDir D:\respaldos-dentalcare -RetentionDays 14
```

```bash
# Linux/Mac
cd /ruta/a/dentia-system
./scripts/backup.sh
./scripts/backup.sh /ruta/a/respaldos 14
```

El resultado de cada corrida queda en `backups/backup.log` (una línea por evento,
con fecha y hora), además de imprimirse en pantalla. Por defecto se conservan los
últimos 30 días de respaldos; los más viejos se borran automáticamente al final de
cada corrida (parámetro `-RetentionDays` / segundo argumento posicional).

## 3. Cifrado (recomendado, opcional)

Los respaldos contienen datos clínicos — CLAUDE.md sec. 5 pide tratarlos como
sensibles incluso en reposo. El cifrado usa OpenSSL (AES-256-CBC + PBKDF2) con una
frase de paso que **nunca se guarda en ningún archivo del repositorio**: se lee de
la variable de entorno `BACKUP_PASSPHRASE` justo antes de cada corrida.

```powershell
# Windows (solo dura la sesión de PowerShell actual)
$env:BACKUP_PASSPHRASE = "una frase larga y dificil de adivinar"
.\scripts\backup.ps1
```

```bash
# Linux/Mac
export BACKUP_PASSPHRASE="una frase larga y dificil de adivinar"
./scripts/backup.sh
```

Si `BACKUP_PASSPHRASE` no está definida, o si no hay un `openssl` disponible, el
script **igual completa el respaldo** (sin cifrar) para no romper una corrida
programada desatendida, pero deja una línea de advertencia bien visible en el
log — revísala. En Windows, si `openssl` no está en el `PATH`, el script también
busca automáticamente la copia que ya trae Git for Windows
(`C:\Program Files\Git\mingw64\bin\openssl.exe`); si no la encuentra tampoco,
instala OpenSSL para Windows o agrega Git al `PATH`.

Para programar un respaldo cifrado sin escribir la frase de paso en ningún
archivo, defínela como variable de entorno **del usuario del servicio** (no del
sistema completo) al crear la tarea programada — ver sección 5.

## 4. Probar la restauración (`restore_test`)

Un respaldo que nunca se restauró no es un respaldo, es una suposición. Por eso
`scripts/restore_test.ps1` / `restore_test.sh` automatizan la prueba completa:

1. Toman el respaldo más reciente de `backups/` (o uno específico).
2. Si está cifrado, lo descifran a un archivo temporal con `BACKUP_PASSPHRASE`.
3. Crean una base de datos **nueva y desechable** (`dentalcare_restore_test` por
   defecto) — nunca tocan la base real de la aplicación.
4. Restauran el volcado ahí con `pg_restore`.
5. Corren una consulta de verificación (cuenta filas en `organizations`,
   `clinics` y `users`) para confirmar que el esquema y los datos llegaron bien.
6. Si también existe el `.zip` de `storage/` de ese mismo respaldo, lo
   descomprimen en una carpeta temporal para confirmar que el archivo no está
   corrupto.
7. Limpian todo (borran la base de datos de prueba, los archivos temporales
   descifrados y la carpeta temporal) y registran **PASS** o **FAIL** con el
   detalle en `backups/restore_test.log`. El código de salida del script es
   distinto de cero si falló — útil para que una tarea programada avise.

Crear y borrar una base de datos requiere el privilegio `CREATEDB`, que el rol de
la aplicación (`dentia`) **no tiene a propósito** (menor privilegio posible). Por
eso `restore_test` necesita credenciales de un superusuario de PostgreSQL
(`postgres` por defecto) — nunca como parámetro del script ni guardadas en un
archivo, siempre leídas de la variable de entorno estándar `PGPASSWORD` justo
antes de correrlo:

```powershell
# Windows
$env:PGPASSWORD = "<password del superusuario>"
.\scripts\restore_test.ps1
# el script borra $env:PGPASSWORD el solo al terminar
```

```bash
# Linux/Mac
export PGPASSWORD="<password del superusuario>"
./scripts/restore_test.sh
```

Verificado manualmente en esta fase: una corrida completa de `backup.ps1` (con y
sin cifrado) seguida de `restore_test.ps1` contra el respaldo cifrado más
reciente, incluyendo la verificación del `.zip` de `storage/` — resultado `PASS`,
`organizations/clinics/users: 1|1|2`, limpieza confirmada (la base de datos
temporal ya no existe después de la corrida).

## 5. Programar el respaldo

### Windows (Programador de tareas)

1. Abre el **Programador de tareas** → *Crear tarea básica...*
2. Nombre: `DentalCare - Respaldo diario`. Desencadenador: diario, a una hora de
   baja actividad (p. ej. 2:00 a.m.).
3. Acción: *Iniciar un programa*.
   - Programa/script: `powershell.exe`
   - Argumentos:
     `-NoProfile -ExecutionPolicy Bypass -File "C:\workspace\dentia-system\scripts\backup.ps1"`
   - Iniciar en: `C:\workspace\dentia-system`
4. En las propiedades de la tarea → pestaña **General**, elige *Ejecutar tanto si
   el usuario inició sesión como si no* y la cuenta de servicio que usarás.
5. Si quieres respaldos cifrados, define `BACKUP_PASSPHRASE` como variable de
   entorno **de esa cuenta de usuario** (Panel de control → Cuentas de usuario →
   Variables de entorno), no como argumento de la tarea — así no queda visible en
   el historial del Programador de tareas.
6. Programa una segunda tarea semanal igual, pero apuntando a `restore_test.ps1`,
   con `PGPASSWORD` definida de la misma forma (variable de entorno de la cuenta
   de servicio, nunca en el archivo de la tarea) para confirmar que los respaldos
   de la semana sí se pueden restaurar.

### Linux (cron)

```cron
# Respaldo diario a las 2:00 a.m., con la frase de paso tomada del entorno del
# usuario que corre cron (definida en su crontab con `crontab -e`, nunca en un
# archivo del repo):
BACKUP_PASSPHRASE=una-frase-larga-y-dificil-de-adivinar
0 2 * * * /ruta/a/dentia-system/scripts/backup.sh >> /ruta/a/dentia-system/backups/cron.log 2>&1

# Prueba de restauracion semanal, domingos a las 3:00 a.m. PGPASSWORD tambien se
# define arriba en el crontab, nunca en un archivo versionado:
PGPASSWORD=password-del-superusuario
0 3 * * 0 /ruta/a/dentia-system/scripts/restore_test.sh >> /ruta/a/dentia-system/backups/cron.log 2>&1
```

Una variable definida directamente en el crontab del usuario (`crontab -e`) vive
en `/var/spool/cron/crontabs/<usuario>`, legible solo por ese usuario y por root —
razonablemente seguro para un servidor de un solo propósito, y de todas formas
nunca queda dentro del repositorio de código.

## 6. Qué hacer si `restore_test` falla

Un `FAIL` en `restore_test.log` significa que el respaldo de esa corrida no sirve
para recuperar el sistema. No lo ignores:

1. Revisa el mensaje de error en el log — casi siempre es `pg_restore` fallando
   por una versión de PostgreSQL distinta a la que generó el volcado, o un
   `BACKUP_PASSPHRASE` incorrecta.
2. Corre `backup.ps1`/`backup.sh` manualmente una vez para generar un respaldo
   fresco y vuelve a correr `restore_test` contra ese mismo archivo
   (`-BackupFile`).
3. Si sigue fallando, no asumas que el respaldo del día anterior sirve — pruébalo
   también con `restore_test -BackupFile <ruta>` antes de confiar en él.
