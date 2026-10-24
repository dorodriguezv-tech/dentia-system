# Usuarios y accesos de DENT-IA

Quién puede entrar a cada ambiente, con qué contraseña, y qué puede hacer
una vez dentro. Complementa a `docs/MATRIZ_PERMISOS.md` (la lista técnica
completa, permiso por permiso) con una vista más práctica: "le doy esta
cuenta a quién, y para qué le sirve".

> ⚠️ **Regla de seguridad, antes de seguir leyendo:** las contraseñas
> `Dentia2025!` de abajo son **ficticias**, usadas solo en el ambiente de
> demostración (`demo.dentia.digital`), y ya están escritas en texto plano
> en el propio código fuente del proyecto (`backend/app/seed.py`) — por
> eso es seguro documentarlas aquí. La contraseña real del administrador de
> producción **nunca se escribe en este archivo ni en ningún otro del
> repositorio** — el repositorio es público. Guárdala en un gestor de
> contraseñas (1Password, Bitwarden, etc.), nunca en un documento de texto
> plano ni en un chat.

---

## 1. Ambiente de demostración — `demo.dentia.digital`

Datos ficticios (pacientes generados con Faker, nunca datos reales). Sirve
para probar el sistema y para enseñárselo a alguien sin riesgo.

| Correo | Contraseña | Rol | Para qué sirve esta cuenta |
|---|---|---|---|
| `admin@dentalcare-demo.mx` | `Dentia2025!` | Administrador de la clínica | Administración general: usuarios, catálogos, reportes, cobranza. Ve todo menos el detalle clínico de los pacientes (no tiene acceso a notas/odontograma). |
| `odontologo@dentalcare-demo.mx` | `Dentia2025!` | Odontólogo | El flujo clínico completo: pacientes, expediente, odontograma, diagnóstico, planes de tratamiento, documentos y consentimientos, agenda. |
| `recepcion@dentalcare-demo.mx` | `Dentia2025!` | Recepción | Alta de pacientes, agenda, y solo lectura de cobranza (no cobra). |
| `caja@dentalcare-demo.mx` | `Dentia2025!` | Caja | Cobranza: abrir/cerrar caja, cargos, pagos, recibos, reportes. No ve el expediente clínico. |

Estas cuatro se crean (o se confirma que ya existen, no se duplican) con:

```bash
sudo docker compose --project-name dentia-demo --project-directory compose \
    run --rm --no-deps api python -m app.seed
```

También existe un quinto usuario en demo, el administrador "real" dado de
alta a mano en la sección 3.5 de `INSTALACION_VPS.md`:

| Correo | Contraseña | Rol |
|---|---|---|
| `admin@dentia.digital` | la que se definió al correr `create-admin.sh` — no documentada aquí (ver advertencia arriba) | Administrador de la clínica |

---

## 2. Ambiente de producción — `app.dentia.digital`

**Aquí no hay usuarios de demostración** — el checklist de la sección 14 de
`INSTALACION_VPS.md` exige explícitamente "sin usuarios del seed ni
`DEMO_PASSWORD` en `dentia-prod`". Solo existen las cuentas reales que se
den de alta a mano, empezando por:

| Correo | Contraseña | Rol |
|---|---|---|
| `admin@dentia.digital` (o el correo real que se use) | definida al correr `create-admin.sh` en `dentia-prod` — no documentada aquí | Administrador de la clínica |

A partir de esa primera cuenta, el propio administrador da de alta al resto
del personal real desde la aplicación (sección 4 de abajo).

---

## 3. Qué puede hacer cada rol (resumen funcional)

| Rol | Pacientes | Expediente / odontograma | Agenda | Tratamientos | Cobranza | Usuarios / configuración |
|---|---|---|---|---|---|---|
| **Administrador de la clínica** (`admin_clinica`) | Alta y edición | — | Ver y crear citas | Solo ver | Cobrar y configurar | Gestiona usuarios, catálogos, marca, reportes |
| **Odontólogo** (`odontologo`) | Alta y edición | Lectura y escritura completa | Ver y crear citas | Crear y aceptar planes | — | — |
| **Especialista** (`especialista`) | Solo ver | Lectura y escritura completa | Ver y crear citas | Crear y aceptar planes | — | — |
| **Asistente dental** (`asistente`) | Solo ver | Ver odontograma, subir imágenes | Solo ver | — | — | — |
| **Recepción** (`recepcion`) | Alta y edición | — | Ver y crear citas | — | Solo ver | — |
| **Caja** (`caja`) | Solo ver | — | — | — | Cobrar y emitir recibos | — |
| **Super administrador** (`superadmin`) | — | — | — | — | — | Crea organizaciones/sucursales; **sin acceso a contenido clínico de ningún paciente** (CLAUDE.md sec. 5) |

Nota: `odontologo` y `especialista` comparten casi todos los permisos
clínicos (expediente, odontograma, diagnóstico, tratamiento, documentos,
agenda); la única diferencia real es que el odontólogo también puede dar
de alta y editar pacientes (`patients.write`) y el especialista solo
puede verlos.

Para la lista exacta, permiso por permiso (útil si vas a dar de alta un rol
nuevo o dudas de un caso puntual), ver `docs/MATRIZ_PERMISOS.md`.

---

## 4. Dar de alta un usuario nuevo (personal real)

Con una cuenta `admin_clinica` (o `superadmin`), dentro de la aplicación:
**Usuarios → Nuevo usuario** — se define correo, nombre, rol, y una
contraseña inicial que la propia persona debe cambiar en su primer ingreso
(sección 5).

---

## 5. Cambiar tu propia contraseña

Una vez con sesión iniciada: menú de usuario → cambiar contraseña. Pide la
contraseña actual y valida la nueva contra la política del sistema (mínimo
12 caracteres, rechaza contraseñas comunes — CLAUDE.md sec. 5).

## 6. Si alguien pierde su contraseña

Hoy el sistema **no tiene autorrecuperación** (no hay "olvidé mi
contraseña" por correo). Las opciones son:

- Pedirle a un `admin_clinica` que la **desactive** (Usuarios → editar →
  inactivo) y se le dé de alta de nuevo con el mismo correo.
- Si quien perdió el acceso es el **único** administrador (sin nadie más
  que pueda desactivar/recrear su cuenta): hace falta una intervención
  directa en la base de datos del servidor — no hay un flujo de
  autoservicio para ese caso. Evitar llegar aquí es la razón para guardar
  siempre la contraseña del primer administrador en un gestor de
  contraseñas apenas se crea (sección 3.5 de `INSTALACION_VPS.md`).
