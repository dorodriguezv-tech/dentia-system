# Pendientes de la instalación en el VPS

Seguimiento de lo que falta antes de considerar `demo.dentia.digital`
completamente alineado con `deploy/vps/INSTALACION_VPS.md`, y antes de
repetir la instalación para `app.dentia.digital` (producción). No
reemplaza al checklist formal de la sección 14 de ese documento — es un
registro más operativo de "qué quedó a medias y por qué", para no perder
el hilo entre sesiones de trabajo.

| # | Pendiente | Estado | Contexto / siguiente paso |
|---|---|---|---|
| 1 | **Respaldos cifrados** (`restic.env`, Backblaze B2 o Google Cloud Storage) | Pospuesto a propósito | `deploy.sh` ya no bloquea el despliegue si falta (avisa y sigue) — decisión explícita del operador mientras se trabaja solo con datos de demo. Antes de producción real es obligatorio: hay que elegir proveedor (B2 es más simple; GCS con bucket en Querétaro si se prioriza mantener los respaldos dentro de México por LFPDPPP), crear la cuenta/bucket, y seguir la sección 5.1 de `INSTALACION_VPS.md`. |
| 2 | **Cloudflare Access** en `demo.dentia.digital` | Pendiente, sin decidir | Hoy el dominio no pide ningún código antes de la pantalla de login de DENT-IA, aunque la sección 3.6 de la guía lo asume como ya configurado. Dos caminos posibles: código de un solo uso por correo (Zero Trust → Access → Applications) o restringir por IP (regla de WAF). Falta decidir cuál, y configurarlo en el panel de Cloudflare. |
| 3 | **Login de `admin@dentalcare-demo.mx`** reportado con error | Sin confirmar | Se reportó "no se pudo iniciar sesion" en el navegador; al reproducirlo (credenciales exactas, después de que `v1.0.1` ya estaba desplegado) funcionó sin problema. Pudo haber sido: (a) una prueba hecha antes de `v1.0.1` —mismo bug ya corregido de `VITE_API_URL`—, o (b) caché del navegador con el frontend viejo. Falta confirmar si persiste con un refresco forzado (`Ctrl+Shift+R`). |
| 4 | **Repetir la instalación para `app.dentia.digital`** (producción) | No iniciado | Solo debe hacerse cuando el checklist completo de la sección 14 de `INSTALACION_VPS.md` esté satisfecho en demo — eso incluye los puntos 1-2 de esta lista. Hasta entonces, `dentia-prod` no existe todavía en el servidor. |

~~`cosign` no instalado en el servidor~~ — **resuelto** (24-oct-2026):
instalado en `/usr/local/bin/cosign` (v3.1.4) y verificado contra las
imágenes `dentia-api:1.0.2`/`dentia-web:1.0.2` ya desplegadas — la firma
corresponde exactamente al workflow `Release`, tag `v1.0.2` y commit
`1d324c7` esperados. Cada `deploy.sh` a partir de ahora verifica la firma
automáticamente en vez de solo advertir que falta la herramienta.

Cuando se resuelva un pendiente, actualizar su fila (estado y, si aplica,
quitarlo de la tabla) en el mismo commit que resuelve el problema.
