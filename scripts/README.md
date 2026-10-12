# Scripts de operación

## Inicio y apagado (`start-dentia.ps1` / `stop-dentia.ps1`)

Automatizan los pasos manuales de [`docs/INICIO_RAPIDO.md`](../docs/INICIO_RAPIDO.md):
base de datos, backend (API) y frontend.

Desde PowerShell, parados en la raíz del repo (`C:\workspace\dentia-system`):

```powershell
.\scripts\start-dentia.ps1
```

Si PowerShell bloquea la ejecución por la política de scripts (`...no está firmado
digitalmente...`), usa:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-dentia.ps1
```

Esto:
1. Levanta PostgreSQL si no está corriendo (servicio nativo de Windows, o
   `docker compose up -d db` si no hay servicio nativo).
2. Abre una ventana de PowerShell nueva con el backend (`uvicorn`, puerto 8001).
3. Abre otra ventana nueva con el frontend (`npm run dev`, puerto 5174).
4. Revisa si Ollama (IA local) responde en el puerto 11434 y solo informa — no lo
   arranca ni lo detiene (ver sección 4 de `docs/INICIO_RAPIDO.md`).

Si un puerto ya está escuchando (p. ej. ya tenías el backend corriendo), ese paso
se omite y no se abre una ventana duplicada.

Parámetros: `-SkipDb`, `-SkipBackend`, `-SkipFrontend` (ej.
`.\scripts\start-dentia.ps1 -SkipDb` si ya la administras aparte).

Para apagar:

```powershell
.\scripts\stop-dentia.ps1
```

Cierra el backend y el frontend (localiza el proceso que escucha en cada puerto y
también su propio árbol de procesos — p. ej. el *reloader* de uvicorn — sin tocar
nunca la terminal o ventana que los lanzó). Por defecto **no** toca la base de
datos ni Ollama, porque pueden estar en uso por otra cosa en la máquina. Para
apagarlos también:

```powershell
.\scripts\stop-dentia.ps1 -StopDb -StopOllama
```

## Respaldo (`backup.ps1` / `backup.sh`, `restore_test.ps1` / `restore_test.sh`)

Ver los comentarios `.SYNOPSIS` al inicio de cada script (`Get-Help .\scripts\backup.ps1 -Full`).
