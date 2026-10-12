# Archivos de contexto para Claude.ai (Proyectos)

Esta carpeta junta los archivos pensados para subir como "conocimiento del
proyecto" en un Proyecto de claude.ai, de modo que cualquier conversación ahí
tenga una idea razonable de cómo está el sistema DENT-IA hoy **sin subir código
fuente**. Dos son nuevos (condensados para esto); el resto ya existían en
`docs/` y se recomienda subirlos tal cual, sin duplicarlos aquí.

## Qué subir (8 archivos, ~55 KB en total)

Generados en esta carpeta — súbelos primero, son el ancla:
1. **`01_arquitectura_y_estado.md`** — qué es el sistema, stack, reglas
   clínicas, módulos, modelo de datos, máquinas de estado, mapa de la API y
   qué está hecho vs. pendiente hoy.
2. **`02_notas_contrato_api.md`** — nombres de campo reales que no son obvios
   (p. ej. `starts_from`/`starts_to`, no `date_from`/`date_to`). Sin esto,
   Claude en la web va a sugerir nombres de campo "razonables" que no
   coinciden con el backend real.

Ya existen en `docs/` y `CLAUDE.md` — súbelos desde ahí, sin copiarlos:
3. **`CLAUDE.md`** (raíz del repo) — convenciones de código, estructura de
   carpetas, comandos, forma de trabajar.
4. **`docs/MATRIZ_PERMISOS.md`** — qué puede hacer cada rol (RBAC).
5. **`docs/PENDIENTES_CLINICOS.md`** — decisiones clínicas ya tomadas o
   todavía abiertas, con el porqué de cada una (es el registro de "por qué
   el sistema hace X y no Y" — muy útil para que Claude no proponga
   deshacer una decisión ya tomada a propósito).
6. **`docs/04_TEMAS_Y_MARCA.md`** — sistema de temas/marca DENT-IA (colores,
   presets, modo oscuro).
7. **`docs/01_ANALISIS_Y_DECISIONES.md`** — resumen de las decisiones de
   especificación v1.0/v2.0.
8. **`docs/03_AGENTE_IA_VOZ.md`** — diseño del asistente de voz (reglas 9/10,
   flujo de dictado → propuesta → aceptar/rechazar).

## Opcionales (según el tipo de conversación)
- `docs/MANUAL_USUARIO.md` / `docs/MANUAL_TECNICO.md` — si vas a hacer
  preguntas de producto/UX o de instalación/operación, no de desarrollo.
- `mobile/CLAUDE.md` y `mobile/docs/05_APP_MOVIL.md` — si la conversación es
  específicamente sobre la app móvil.
- `docs/CAMBIOS_WEB_MARCA.md` — ya aplicado por completo; solo útil como
  referencia histórica de la tarea de rebranding.

## Qué NO subir
`docs/02_ARQUITECTURA.md` completo (142 KB, narrativa fase por fase — ya está
condensado en `01_arquitectura_y_estado.md`), código fuente, `.env`, nada bajo
`storage/` o `mobile/secrets/`.

## Cómo mantenerlo al día
Estos dos archivos nuevos son un corte del 2026-10-12. Si el contrato de la
API cambia, lo más rápido es regenerar la comparación:
```
# con el backend corriendo en :8001
npx openapi-typescript http://localhost:8001/openapi.json -o schema.d.ts
```
y pedirle a Claude Code que actualice `02_notas_contrato_api.md` con lo que
haya cambiado.
