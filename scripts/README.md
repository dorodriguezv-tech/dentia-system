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

El cliente **móvil** (Metro/`npx expo start --dev-client`, puerto 8081) no se
levanta por defecto porque es un cliente aparte del frontend web. Para incluirlo:

```powershell
.\scripts\start-dentia.ps1 -Mobile
```

Con `-Mobile`, el backend se arranca con `--host 0.0.0.0` (en vez de solo
`localhost`): un teléfono real, a diferencia del navegador del frontend web que
corre en esta misma máquina, necesita que uvicorn escuche en la red
(`mobile/docs/05_APP_MOVIL.md` §4.1). El script imprime al final la URL de
Tailscale para pegar en la pantalla "Servidor" de la app. Si el backend ya estaba
corriendo *sin* `-Mobile` (solo en `localhost`), el teléfono no podrá conectarse
aunque el script diga que el puerto ya está escuchando — ese caso se avisa por
separado; cierra el backend (`.\scripts\stop-dentia.ps1`) y vuelve a levantarlo
con `-Mobile`.

Para apagar:

```powershell
.\scripts\stop-dentia.ps1
```

Cierra el backend y el frontend (localiza el proceso que escucha en cada puerto y
también su propio árbol de procesos — p. ej. el *reloader* de uvicorn — sin tocar
nunca la terminal o ventana que los lanzó). Por defecto **no** toca la base de
datos, Ollama ni el móvil, porque pueden estar en uso por otra cosa en la máquina.
Para apagarlos también:

```powershell
.\scripts\stop-dentia.ps1 -StopDb -StopOllama -StopMobile
```

Si solo quieres cerrar y volver a levantar backend + móvil para probar un cambio
(el caso típico al desarrollar la app), sin tocar base de datos ni frontend web:

```powershell
.\scripts\stop-dentia.ps1 -StopMobile
.\scripts\start-dentia.ps1 -SkipFrontend -Mobile
```

## Respaldo (`backup.ps1` / `backup.sh`, `restore_test.ps1` / `restore_test.sh`)

Ver los comentarios `.SYNOPSIS` al inicio de cada script (`Get-Help .\scripts\backup.ps1 -Full`).
