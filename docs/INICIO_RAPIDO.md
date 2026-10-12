# Inicio rápido (PowerShell, Windows)

.\scripts/stop-dentia.ps1
.\scripts\stop-dentia.ps1

Comandos para levantar DENT-IA en esta máquina, donde la base de datos, el entorno
virtual (`backend/.venv`) y las dependencias de Node (`node_modules`) ya están
instalados. Para una instalación desde cero (otra máquina, sin nada previo) usa en su
lugar el paso a paso completo del [`README`](../README.md).

Abre **tres ventanas de PowerShell** (una por proceso) y deja cada una corriendo.

> Atajo: `scripts\start-dentia.ps1` hace los pasos 1-3 por ti (detecta lo que ya
> esté corriendo y no lo duplica) y `scripts\stop-dentia.ps1` los apaga. Ver
> [scripts/README.md](../scripts/README.md).

## 1. Base de datos

Solo si usas PostgreSQL vía Docker (si tienes PostgreSQL nativo instalado y ya está
corriendo como servicio de Windows, omite este paso):

```powershell
cd C:\workspace\dentia-system
docker compose up -d db
```

## 2. Backend (API)

```powershell
cd C:\workspace\dentia-system\backend
.venv\Scripts\Activate.ps1
alembic upgrade head          # aplica migraciones pendientes, si hay
uvicorn app.main:app --reload --port 8001
```

Verificar que responde: `http://localhost:8001/api/v1/health` → `{"status":"ok"}`.

## 3. Frontend

```powershell
cd C:\workspace\dentia-system\frontend
npm run dev
```

Abre `http://localhost:5174` en el navegador.

## 4. Asistente de IA (opcional, solo si lo vas a usar)

El instalador de Ollama para Windows deja una app en segundo plano (**Ollama**, en la
bandeja del sistema) que arranca sola con Windows y ya escucha en el puerto 11434 —
en ese caso **no** corras `ollama serve`, ya está listo. Verifica primero:

```powershell
curl http://localhost:11434/api/version
```

Si responde con un JSON (`{"version":"..."}`), ya está corriendo — no hagas nada más.
Si da error de conexión, entonces sí falta levantarlo:

```powershell
ollama serve
```

> El error `listen tcp 127.0.0.1:11434: bind: Only one usage of each socket address...`
> al correr `ollama serve` no es una falla: significa justamente que Ollama ya estaba
> corriendo (la app de la bandeja). Ignóralo y sigue usando el sistema normal.

(`ollama pull qwen2.5:7b` solo la primera vez, si no lo tienes descargado ya).

## 5. (Si la base de datos está vacía) sembrar datos ficticios

Solo la primera vez, o si reiniciaste la base de datos. Es idempotente — correrlo de
nuevo sobre datos ya sembrados no los duplica:

```powershell
cd C:\workspace\dentia-system\backend
.venv\Scripts\Activate.ps1
python -m app.seed
```

---

## Usuarios de prueba

Los crea `python -m app.seed` (organización **Clínica Dental Demo**, sucursal
**Sucursal Centro**). Todos con la misma contraseña:

**Contraseña: `Dentia2025!`**

| Correo                          | Rol                         | Notas                                                                                                |
| ------------------------------- | --------------------------- | ---------------------------------------------------------------------------------------------------- |
| `admin@dentalcare-demo.mx`      | Administrador de la clínica | MFA deshabilitada temporalmente (ver `docs/SEGURIDAD.md`) — entra directo, sin pedir configurar TOTP |
| `odontologo@dentalcare-demo.mx` | Odontólogo                  | Expediente, odontograma, diagnóstico, tratamiento, consentimientos, IA                               |
| `recepcion@dentalcare-demo.mx`  | Recepción                   | Alta de pacientes y agenda                                                                           |
| `caja@dentalcare-demo.mx`       | Caja                        | Pagos, corte de caja y reportes                                                                      |

Los nombres de las personas (p. ej. "Ing. Wilfrido Gaytán") son generados al azar por
Faker en cada corrida de `python -m app.seed` sobre una base nueva — solo el correo, la
contraseña y el rol son fijos.

Ver [`docs/MATRIZ_PERMISOS.md`](./MATRIZ_PERMISOS.md) para el detalle de qué puede hacer
cada rol, y [`docs/MANUAL_USUARIO.md`](./MANUAL_USUARIO.md) para cómo usar cada pantalla.
