# App móvil DENT-IA v1.1 — Paridad con la web y flujo de consulta completo

Fecha: 12 de octubre de 2026. Complementa `docs/05_APP_MOVIL.md`.
Copia este archivo a `C:\workspace\dentia-system\docs\06_APP_MOVIL_V1_1_PARIDAD.md`.

---

## 0. Por qué la v1.0 se siente incompleta

La v1.0 se diseñó como "lectura + dictado": agenda para ver, odontograma ligado a "la atención de hoy" y lo demás "en la web". En la práctica el odontólogo usa el teléfono o la tablet **en el sillón** y necesita cerrar el ciclo completo sin ir a la computadora:

```
Agenda → Llegó → Iniciar atención → (alertas · odontograma · dictado · fotos · nota)
       → Cerrar consulta → Generar próxima cita → Agenda
```

Los reportes del usuario y su causa más probable:

| # | Reporte | Causa probable (Claude Code debe confirmarla en el código) |
|---|---|---|
| R1 | La agenda no permite crear citas como en la web | La v1.0 nunca implementó `POST /appointments`; solo cambios de estado. |
| R2 | ¿Cómo se inicia la atención del paciente? | El botón solo aparece en citas **EN_SALA** y con permiso `ai.use`; si falta B4 (permisos en `/me/clinics`) o la cita no se marcó "Llegó", el botón no existe. No hay forma de iniciar atención desde la ficha del paciente (sin cita / urgencia). |
| R3 | El odontograma no permite cambios | Depende de una "atención de hoy". Como R2 impide abrirla, siempre queda en **solo lectura**. Además solo permite *registrar* hallazgos, no cambiar/resolver/anular uno vigente. |
| R4 | En Configuración un usuario normal no puede cambiar idioma ni voz | La pantalla de Ajustes completa está protegida con un permiso de administración (`ai.configure` o `branding.manage`). Idioma y voz son **preferencias personales**, no configuración de la clínica. |
| R5 | El botón "Cerrar sesión" no sirve | Muy probable: `await api.logout()` falla (refresh token no viaja en el cuerpo → B1, o 401) y la excepción corta la función antes de borrar el token y cambiar de pantalla. O se borra el store pero el token sigue en SecureStore y el arranque vuelve a entrar solo. |
| R6 | Falta "Cerrar consulta" | No existe pantalla de nota/cierre en móvil (se dejó "para la web"). |
| R7 | Falta "Generar nueva cita" al terminar | Depende de R1 y R6. |

---

## 1. Principios de la v1.1

1. **Mismos endpoints que la web.** Antes de programar cualquier pantalla, Claude Code lee el módulo equivalente en `frontend/src/modules/<modulo>` y usa exactamente la misma API, reglas y mensajes. Cero lógica clínica nueva en el teléfono.
2. **El backend autoriza; la app solo oculta.** Si un botón no aparece, debe haber un texto que diga por qué ("Tu rol no puede editar el odontograma").
3. **Nunca un botón muerto.** Todo botón visible hace algo o muestra un mensaje. Todo error de red se muestra con un aviso y un "Reintentar".
4. **Reglas clínicas 1–10 intactas**, en especial: nota FINAL no se edita (1), no hay borrado físico (2), un hallazgo vigente por pieza/superficie (5), alertas antes de cerrar nota o registrar procedimiento (8), IA solo propone (9).
5. Pantallas pensadas para **tablet del consultorio y teléfono**: botones de 48 dp mínimo, una acción principal por pantalla, nada que dependa de hover.

---

## 2. Navegación nueva (más amigable)

Barra inferior con 4 pestañas + botón de Dentia:

| Pestaña | Contenido |
|---|---|
| **Agenda** | Día / semana, filtros por profesional, botón **+ Nueva cita** |
| **Pacientes** | Búsqueda, **+ Nuevo paciente** (si `patients.write`), ficha |
| **Consulta** | Atajo a la **atención en curso** (si hay una abierta); si no, "No tienes una consulta abierta" + lista de pacientes en sala |
| **Más** | Mis preferencias, Clínica (solo admin), Acerca de, **Cerrar sesión** |

Mientras haya una consulta abierta, se muestra una **barra fija** arriba: "En consulta: Laura Sánchez · 12 min · Abrir" (como la llamada en curso de un teléfono). Así el odontólogo nunca "pierde" la consulta al navegar.

---

## 3. Cambios por bloque

Cada bloque es un *vertical slice*: pantalla + llamadas a API + pruebas + entrada en la checklist §5. Un bloque a la vez.

### M0 · Auditoría de paridad (sin cambiar código)
- Recorre `frontend/src/modules/*` y `mobile/src/*` y genera `docs/PARIDAD_WEB_MOVIL.md`: tabla funcionalidad × (web, móvil, endpoint, permiso, ¿va en móvil?).
- Lista qué endpoints usa la web para: crear/editar/reprogramar/cancelar cita, disponibilidad, iniciar atención (encounter), nota clínica (crear, guardar borrador, finalizar), hallazgos del odontograma (crear, cambiar, resolver, anular), plan de tratamiento, preferencias de usuario, logout.
- Confirma o descarta cada causa de la tabla §0.
- **Entrega:** el documento y una lista de cambios de backend necesarios (si los hay). No avanzar a M1 sin revisión del usuario.

### M1 · Cerrar sesión (R5) — primero, es el más sencillo
- `logout()` en `try/finally`: el `finally` **siempre** borra access token (memoria), refresh token (SecureStore), caché de TanStack Query (`queryClient.clear()`), store de Zustand, sucursal elegida y consulta abierta; detiene Dentia y la grabación; y reinicia la navegación al Login (reset, no `navigate`, para que "Atrás" no regrese).
- La llamada `POST /auth/logout` con `{refresh_token}` en el cuerpo se intenta, pero su error **no** bloquea el cierre (se registra en consola de desarrollo).
- Confirmación: "¿Cerrar sesión? Si tienes una consulta abierta, quedará en borrador." → **Cerrar sesión** / Cancelar.
- Pruebas: logout con red, sin red, con 401 → en los tres casos termina en Login y al reabrir la app pide contraseña.

### M2 · Mis preferencias vs. Configuración de la clínica (R4)
Divide Ajustes en dos secciones:

| Sección | Quién la ve | Contenido |
|---|---|---|
| **Mis preferencias** | **Todos** los usuarios | Idioma de la interfaz (es-MX por defecto; en-US si la web lo soporta), voz de Dentia (lista de voces femeninas en español instaladas en el teléfono + botón "Probar voz"), velocidad y volumen de voz, Dentia activado/desactivado, tema (sistema/claro/oscuro), tamaño de letra, bloqueo con huella/PIN, tiempo de bloqueo (1/2/5 min). |
| **Clínica** | Solo con `branding.manage` o `ai.configure` | Servidor, marca/logo, configuración de IA (modelo, idioma de transcripción del servidor). |

- Las preferencias se guardan en el teléfono (no son datos clínicos) y, si la web tiene preferencias por usuario, se sincronizan con el mismo endpoint (si no existe, ver B7).
- Cambiar idioma o voz aplica **al instante**, sin reiniciar.
- Prueba: usuario `recepcion` y `odontologo` cambian idioma y voz; `recepcion` no ve la sección Clínica.

### M3 · Agenda completa (R1)
Igual que la web, con los mismos endpoints y validación de conflictos **en el backend**:
- **+ Nueva cita** (botón flotante y también al tocar un hueco libre en la vista de día):
  1. Paciente: buscador; si no existe → "Crear paciente rápido" (nombre, apellidos, teléfono, fecha de nacimiento) si el rol tiene `patients.write`.
  2. Profesional (por defecto el usuario si es odontólogo).
  3. Tipo de cita (catálogo de la clínica) → propone la duración.
  4. Fecha y hora: muestra **horarios disponibles** del profesional (mismo cálculo que la web); permite hora manual.
  5. Motivo / notas para recepción.
  6. Resumen → **Agendar**.
- Si el backend responde conflicto (409 o el código que use la web): mostrar "Ese horario ya está ocupado por *X*" y sugerir los 3 horarios libres más cercanos.
- Al tocar una cita: **Llegó**, **Iniciar atención**, **Reprogramar**, **Cancelar** (con motivo obligatorio), **No asistió**, **Llamar / WhatsApp** al paciente. Solo se muestran las transiciones válidas según la máquina de estados de `rules.py`.
- Vista **semana** además de día; deslizar para cambiar de día; botón "Hoy".
- Dentia: "agenda a Laura Sánchez mañana a las 10 para limpieza" abre el formulario **prellenado** con confirmación de 3 s (mismo intérprete de la web).
- Permisos: `agenda.write` para crear/modificar. Asistente dental solo ve.

### M4 · Iniciar atención (R2)
Tres formas de iniciar, todas llegan a la misma pantalla **Consulta**:
1. Desde la agenda: cita en **EN_SALA** → **Iniciar atención**. Si la cita sigue en "Agendada", el botón aparece igual y al tocarlo marca "Llegó" e inicia en un solo paso (preguntando "¿El paciente ya está en el sillón?").
2. Desde la ficha del paciente: **Iniciar atención** sin cita (urgencia / paciente sin cita). Crea el encounter con el mismo endpoint que la web.
3. Por voz: "Dentia, inicia la atención de Laura Sánchez".

Reglas:
- Requiere `records.write` (odontólogo/especialista). Para otros roles el botón no aparece y la cita muestra "Lo inicia el odontólogo".
- Solo **una consulta abierta por profesional**; si hay otra, preguntar "Tienes abierta la consulta de *X*. ¿Volver a ella o dejarla en borrador?".
- Al iniciar, **lo primero que se ve son las alertas clínicas** (alergias, medicamentos de riesgo, antecedentes) en una tarjeta roja/ámbar que hay que tocar "Enterado" (regla 8). Queda en auditoría.

**Pantalla Consulta** (pestañas superiores, todas sobre el mismo encounter):

| Pestaña | Contenido |
|---|---|
| Resumen | Alertas, motivo de la cita, últimas 3 consultas, plan de tratamiento vigente |
| Odontograma | Editable (M5) |
| Dictado | Grabar → propuestas IA (ya existe en v1.0) + **editar** la propuesta antes de aceptar |
| Nota | Nota de la consulta (M6) |
| Fotos | Cámara y galería del encounter |
| Procedimientos | Procedimientos **realizados** hoy, separados de los planificados (regla 3) |

Botón principal fijo abajo: **Cerrar consulta**.

### M5 · Odontograma editable (R3)
- Con consulta abierta y `odontogram.write`: editable. Sin consulta abierta: solo lectura con el botón **"Iniciar atención para editar"** (no solo un aviso).
- Tocar una pieza abre una hoja inferior con:
  - Las 5 superficies (O/I, M, D, V, L/P) seleccionables **varias a la vez**, más "pieza completa".
  - Catálogo de hallazgos de la clínica (el mismo de la web), con búsqueda y los 6 más usados arriba.
  - Estado: diagnóstico / planificado / realizado (según cómo lo modele la web).
  - Nota corta opcional.
- Acciones sobre un hallazgo **vigente**: **Cambiar** (crea un evento nuevo que reemplaza al vigente; el anterior queda en historial — regla 5), **Marcar como resuelto/tratado**, **Anular** con motivo obligatorio (regla 2; nunca borrar).
- **Deshacer** durante 5 s después de guardar (crea el evento inverso, no borra).
- Zoom con pellizco, cambio permanente/temporal/mixta, leyenda de colores igual a la web.
- Historial por pieza: fecha, autor, origen (manual / IA), encounter.
- Dentia y dictado: "caries oclusal en el 36" → propuesta → aceptar (ya existe; verificar que ahora sí escribe con consulta abierta).
- Pruebas: registrar, cambiar, resolver, anular, deshacer; cada uno visible en la web con su historial.

### M6 · Cerrar consulta (R6)
Al tocar **Cerrar consulta**:
1. **Nota de consulta** prellenada con lo hecho hoy: motivo, hallazgos nuevos, procedimientos realizados, propuestas IA aceptadas, fotos. Formato SOAP simple (S, O, A, P) editable; el dictado puede llenar cada sección (como propuesta).
2. **Validaciones** que hace el backend (mostrar sus mensajes tal cual): propuestas IA pendientes ("Tienes 2 propuestas sin revisar: Aceptar todas / Revisar / Descartar"), alertas clínicas vigentes (regla 8, otra vez antes de cerrar), procedimientos sin pieza.
3. Opciones:
   - **Guardar borrador** (DRAFT): puede seguir después, en móvil o web.
   - **Finalizar nota** (FINAL): confirmación "Una nota final no se puede modificar; las correcciones crean una versión nueva". Si la web pide firma o MFA para finalizar, la app pide lo mismo.
4. La cita pasa a **Atendida** (según la máquina de estados) y se cierra el encounter.
5. Si la clínica tiene cobranza activa, aviso para recepción: "Hay cargos por registrar" (la app **no** cobra; regla 4).
6. Inmediatamente después → **¿Agendar la próxima cita?** (M7).

Las correcciones a una nota FINAL (versión CORRECTED con motivo) se hacen en la web; en móvil se muestra el botón "Corregir en la web" con explicación.

### M7 · Generar próxima cita (R7)
Pantalla que aparece al cerrar la consulta (y también desde la ficha del paciente):
- Prellenado: paciente, profesional, **siguiente procedimiento planificado** del plan de tratamiento (si lo hay) con su duración, y una fecha sugerida (p. ej., +7 días, configurable por tipo de procedimiento si la web ya tiene ese dato).
- Muestra horarios libres; un toque para agendar.
- Opciones: **Agendar**, **Recordar después** (deja un pendiente en recepción si la web lo soporta), **No requiere**.
- Al agendar: mensaje "Cita creada: martes 20 de octubre, 10:00" + botón "Enviar recordatorio por WhatsApp" (abre WhatsApp con el texto; no se envía nada automáticamente).

### M8 · Experiencia general ("más amigable")
- Estados vacíos con acción: "No hay citas hoy · + Nueva cita".
- Avisos (toast) de éxito y error en todas las acciones; errores en español con "Reintentar".
- Indicadores de carga en botones (no pantallas en blanco) y deslizar para actualizar en listas.
- Confirmaciones solo para acciones irreversibles o clínicas (finalizar nota, anular, cancelar cita).
- Si se pierde la red a mitad de un formulario, **no se pierde lo escrito** (se conserva en memoria y se reintenta).
- Botón de atrás de Android: en Consulta pregunta "¿Salir de la consulta? Quedará abierta" (no la cierra).
- Ficha del paciente con acciones rápidas arriba: Iniciar atención · Nueva cita · Llamar · Odontograma.
- Accesibilidad: TalkBack lee todos los botones (`accessibilityLabel`), contraste AA, letra grande sin cortes.

---

## 4. Posibles cambios en el backend

Solo si M0 confirma que no existen (la web normalmente ya los tiene):

| # | Cambio | Motivo |
|---|---|---|
| B7 | `GET/PUT /me/preferences` (idioma, voz, tema, Dentia on/off) por usuario | Que las preferencias viajen entre web, tablet y teléfono. Si no se hace, quedan solo en el dispositivo. |
| B8 | `GET /appointments/availability?provider_id&date&duration` | Horarios libres en M3/M7 sin calcularlos en el teléfono. |
| B9 | `POST /encounters` acepta `appointment_id` opcional (atención sin cita) | M4 forma 2. |
| B10 | `GET /encounters/current` del profesional | Barra "En consulta" y recuperar la consulta al reabrir la app. |
| B11 | `POST /encounters/{id}/close` devuelve las validaciones pendientes con `code` estable | Mostrar mensajes claros en M6. |

Cada uno con prueba pytest, sin romper las pruebas existentes ni la web.

---

## 5. Checklist manual v1.1 (agregar a la de `05_APP_MOVIL.md` §6.2)

- [ ] **Cerrar sesión** con red, sin red y con token vencido → Login; reabrir la app pide contraseña.
- [ ] Recepción cambia idioma y voz de Dentia; no ve "Clínica".
- [ ] Recepción crea cita desde el hueco libre y desde el botón +; conflicto de horario muestra alternativas.
- [ ] Reprogramar y cancelar (con motivo) se reflejan en la web.
- [ ] Odontólogo inicia atención: desde cita EN_SALA, desde cita Agendada (un paso), desde la ficha sin cita, por voz.
- [ ] Al iniciar se muestran alertas y hay que tocar "Enterado".
- [ ] Odontograma: registrar caries en 36-O y 36-M a la vez, cambiarla a obturación, anular otra con motivo, deshacer; todo con historial en la web.
- [ ] Sin consulta abierta el odontograma muestra "Iniciar atención para editar".
- [ ] Cerrar consulta con propuestas IA pendientes → pide revisarlas.
- [ ] Guardar borrador → continuar en la web. Finalizar → nota FINAL no editable.
- [ ] Al cerrar aparece "Próxima cita" con el siguiente procedimiento del plan; agendar en un toque.
- [ ] Salir con "Atrás" durante la consulta no la cierra; la barra "En consulta" permite volver.
- [ ] Cerrar y reabrir la app con una consulta abierta → la barra "En consulta" reaparece.

---

## 6. Instrucciones para Claude Code (copiar en orden, una a la vez)

```text
1) Lee CLAUDE.md, mobile/CLAUDE.md, docs/05_APP_MOVIL.md y
   docs/06_APP_MOVIL_V1_1_PARIDAD.md. Haz SOLO el bloque M0: genera
   docs/PARIDAD_WEB_MOVIL.md comparando frontend/src/modules con mobile/src,
   lista los endpoints que usa la web para cada flujo de §M0 y confirma o
   descarta cada causa de la tabla §0. No cambies código. Dime qué cambios de
   backend (B7–B11) hacen falta realmente.

2) Implementa M1 (cerrar sesión) con sus pruebas. Muéstrame el diff.

3) Implementa M2 (Mis preferencias / Clínica) y, si M0 lo confirmó, B7 en el
   backend con su prueba pytest.

4) Implementa M3 (agenda completa) usando los mismos endpoints que
   frontend/src/modules/agenda. Si hace falta B8, hazlo primero con su prueba.

5) Implementa M4 (iniciar atención y pantalla Consulta) con B9/B10 si hacen
   falta.

6) Implementa M5 (odontograma editable) respetando la regla 5 y la 2.

7) Implementa M6 (cerrar consulta) y M7 (próxima cita), con B11 si hace falta.

8) Aplica M8 en todas las pantallas. Corre npm run typecheck, npm test,
   npx expo-doctor y pytest; todo en verde. Actualiza docs/05_APP_MOVIL.md
   §"Qué hace la versión" y la checklist §6.2 con la de §5 de este documento.
```

Revisa `git diff` después de cada paso y prueba en el teléfono antes de pedir el siguiente.
