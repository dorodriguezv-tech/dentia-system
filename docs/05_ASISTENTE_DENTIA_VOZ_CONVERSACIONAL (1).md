# Fase 13 — "Dentia": asistente de voz conversacional (tipo Alexa)

> Evolución del asistente de la Fase 8. Antes: el odontólogo pulsa el micrófono, dicta y
> revisa propuestas en un panel. Ahora: **Dentia escucha siempre** desde que inicia sesión,
> se despierta al oír su nombre, entiende órdenes cortas, **pregunta lo que le falta**,
> **confirma en voz alta (voz de mujer)** y ejecuta. Todo sigue siendo 100 % local.

---

## 1. Principios de diseño (lo que hace que sea fácil de usar)

1. **Manos libres de verdad.** El odontólogo trae guantes y las manos en la boca del paciente:
   nada debe requerir mouse ni teclado. Activación por voz, con pedal USB opcional como respaldo.
2. **Órdenes cortas, respuestas más cortas.** Dentia habla solo lo necesario
   ("Listo, 18 caries oclusal"). Nada de frases largas que interrumpan la consulta.
3. **Confirmar según el riesgo, no siempre.** Confirmar todo cansa y hace que la gente deje de
   usarlo. Navegar no se confirma; capturar se repite en voz alta; lo delicado pregunta "¿confirmas?".
4. **Siempre se puede corregir:** "cancela" antes de ejecutar, "deshaz" después.
5. **Lo que se oye, se ve.** Todo lo que Dentia entiende aparece en pantalla (subtítulo + tarjeta),
   para que el odontólogo lo verifique de un vistazo sin tener que escuchar con atención.
6. **Rápido o no sirve.** Las órdenes frecuentes se resuelven sin el modelo de lenguaje
   (< 1.5 s). Ollama solo entra cuando la frase es libre o rara.
7. **Dentia nunca decide sola lo clínico.** Captura lo que el odontólogo dice; no diagnostica,
   no firma, no cobra, no borra (se mantiene la regla 9, ver sec. 9).

---

## 2. Cómo se vive en la consulta

### 2.1 Ciclo de una orden
```
 (escucha pasiva)  ──"Dentia"──►  🔔 tono corto + orbe se ilumina
        ▲                                │
        │                         escucha la orden (termina al detectar ~0.8 s de silencio)
        │                                │
        │                         entiende → ¿le falta algo? ──sí──► PREGUNTA ("¿Qué superficie?")
        │                                │no                              │
        │                         ¿nivel de riesgo?                         └──► vuelve a escuchar
        │                    ┌───────────┼──────────────┐
        │               Navegar      Capturar          Delicado
        │              (ejecuta)   (repite y ejecuta   ("¿confirmas?"
        │                           si no dices          espera sí/no)
        │                           "cancela" en 3 s)
        │                                │
        └──── ventana de seguimiento de 8 s (puedes dar otra orden SIN decir "Dentia") ◄─┘
```

La **ventana de seguimiento** es clave en el odontograma: el odontólogo dice
"Dentia, la 18 caries oclusal" y luego, sin repetir el nombre, "la 17 resina", "la 16 sana"...
Mientras siga hablando, Dentia sigue atenta. 8 s de silencio y vuelve a escucha pasiva.

### 2.2 Ejemplos de diálogo

**Abrir expediente e iniciar consulta (nivel delicado → pregunta)**
```
ODONTÓLOGO: Dentia, abre el expediente de Juan Pérez e inicia la consulta.
DENTIA:     Encontré a Juan Pérez López, 45 años, con cita a las 10:30.
            Inicio la consulta, ¿confirmas?
ODONTÓLOGO: Sí.
DENTIA:     Consulta iniciada. Tiene alergia a la penicilina.        ← lee alertas críticas al abrir
```

**Nombre ambiguo (pregunta en vez de adivinar)**
```
ODONTÓLOGO: Dentia, abre el expediente de Juan Pérez.
DENTIA:     Hay dos: Juan Pérez López, 45 años, y Juan Pérez García, 12 años. ¿Cuál?
ODONTÓLOGO: El de 12.
DENTIA:     Abriendo expediente de Juan Pérez García.
```

**Odontograma (nivel captura → repite y ejecuta)**
```
ODONTÓLOGO: Dentia, en el odontograma, la 18 tiene caries.
DENTIA:     ¿En qué superficie? Oclusal, mesial, distal, vestibular o palatina.
ODONTÓLOGO: Oclusal y distal.
DENTIA:     Coloco caries en la 18, oclusal y distal.      [tarjeta con cuenta regresiva 3 s]
            (aplicado)
ODONTÓLOGO: La 17 resina oclusal.                           ← dentro de la ventana, sin "Dentia"
DENTIA:     Resina en la 17, oclusal.
```

**Dentia escuchó mal → cancelar y repetir**
```
ODONTÓLOGO: Dentia, la 28 ausente.
DENTIA:     Marco la 38 como ausente.
ODONTÓLOGO: ¡Cancela! La veintiocho.
DENTIA:     Cancelado. Marco la 28 como ausente.
```

**Ya se aplicó y estaba mal → deshacer**
```
ODONTÓLOGO: Dentia, deshaz lo último.
DENTIA:     Quité "caries en la 18, oclusal y distal". 
```

**Algo que Dentia no debe hacer**
```
ODONTÓLOGO: Dentia, firma la nota.
DENTIA:     La firma la tienes que hacer tú. Te dejo abierta la ventana de finalizar.
```

**No entendió**
```
DENTIA (1er intento): No te entendí, ¿me lo repites?
DENTIA (2º intento):  Sigo sin entender. Te muestro en pantalla lo que puedo hacer aquí.
```

---

## 3. Niveles de confirmación

| Nivel | Qué incluye | Qué hace Dentia | Ejemplo de respuesta |
|---|---|---|---|
| **0 – Consulta** | Preguntas de solo lectura | Responde | "Alérgica a penicilina, severa." |
| **1 – Navegar** | Abrir expediente (coincidencia única), ir a una pestaña o pantalla, mostrar historial de una pieza | Ejecuta de inmediato y lo dice | "Abriendo odontograma." |
| **2 – Capturar** | Hallazgos de odontograma, signos vitales, motivo de consulta, texto en la nota, medicamento, antecedente | **Repite y ejecuta** tras 3 s si no se dice "no/cancela" (configurable a confirmación explícita) | "Coloco caries en la 18, oclusal." |
| **3 – Delicado** | Iniciar consulta, alergias, diagnósticos, procedimientos planeados/realizados, agendar o mover citas, cualquier orden con baja certeza de reconocimiento | **Pregunta y espera "sí"** | "Agendo control el 21 de octubre a las 10:00, ¿confirmas?" |
| **4 – Prohibido** | Finalizar/firmar nota, cobrar, borrar, recetar, cambiar identidad del paciente | **No lo hace**; lleva al odontólogo a la pantalla correspondiente | "Eso lo tienes que hacer tú." |

Reglas adicionales:
- **Baja certeza sube de nivel:** si Whisper reporta baja confianza en la pieza o el número,
  una orden de nivel 2 se trata como nivel 3 (pregunta explícita).
- **Alertas antes de procedimientos:** si se planea o realiza un procedimiento y el paciente
  tiene alertas activas, Dentia las dice antes de pedir confirmación.
- Respuestas válidas para confirmar: "sí", "correcto", "adelante", "confirmo", "ok".
  Para negar: "no", "cancela", "olvídalo", "espera", "alto".

---

## 4. Lo que Dentia sabe hacer (catálogo de intenciones, MVP)

Cada intención se define **una sola vez** en un registro declarativo (sec. 6.3): nombre, frases
de ejemplo, campos (slots) requeridos y opcionales, de dónde valida cada campo, nivel de
confirmación, plantilla de lo que dice y a qué servicio de dominio llama. Así Dentia "conoce
los menús y campos" desde la misma fuente que usa el sistema, y agregar un comando nuevo es
agregar una entrada, no programar un flujo.

### 4.1 Globales (en cualquier pantalla)
| Intención | Frases típicas | Campos | Nivel |
|---|---|---|---|
| `abrir_expediente` | "abre el expediente de…", "busca a…" | paciente (búsqueda tolerante `pg_trgm` ya existente) | 1 (3 si hay varios) |
| `ir_a` | "ve a la agenda", "abre el odontograma / expediente / tratamientos / imágenes" | destino | 1 |
| `iniciar_consulta` | "inicia la consulta", "empieza la atención" | paciente (contexto); usa la cita del día si existe (`start-encounter`), si no, crea `Encounter` | 3 |
| `citas_hoy` | "¿qué citas tengo hoy?", "¿quién sigue?" | — | 0 |
| `siguiente_paciente` | "siguiente paciente" | — | 1 |
| `leer_alertas` | "¿tiene alergias?", "¿qué alertas tiene?" | — | 0 |
| `deshacer` | "deshaz", "quita lo último" | — | 2 |
| `repetir` | "repite", "¿qué dijiste?" | — | 0 |
| `ayuda` | "¿qué puedo decir?" | — | 0 (muestra tarjeta en pantalla) |
| `silencio` | "deja de escuchar", "silencio" | — | pausa el micrófono hasta reactivar con el botón o el pedal |

### 4.2 Atención (consulta)
| Intención | Frases típicas | Campos | Nivel |
|---|---|---|---|
| `motivo_consulta` | "motivo: dolor al frío en la inferior izquierda" | texto | 2 |
| `signos_vitales` | "presión 120 80, pulso 72" | ≥1 de TA, FC, temp | 2 |
| `alergia` | "alérgico a la penicilina" | sustancia, severidad? | 3 |
| `medicamento` | "toma metformina 850 cada 12 horas" | nombre, dosis?, frecuencia? | 2 |
| `antecedente` | "antecedente: diabetes tipo 2" | categoría, texto | 2 |
| `nota` | "en la nota, subjetivo: …" / "en el plan: …" | sección S/O/A/P/libre, texto | 2 |
| `modo_dictado` | "Dentia, dictado" … "Dentia, fin del dictado" | — | Reutiliza el flujo de la Fase 8: el texto largo va a `/ai/interpret` y genera propuestas; al terminar Dentia dice "Tengo 6 propuestas, ¿las acepto todas?" |

### 4.3 Odontograma
| Intención | Frases típicas | Campos | Nivel |
|---|---|---|---|
| `hallazgo` | "la 18 caries oclusal", "dieciocho ausente", "treinta y seis endodoncia" | pieza FDI, hallazgo, superficies (se pregunta si el hallazgo lo requiere), material? | 2 |
| `historial_pieza` | "historial de la 36" | pieza | 1 |
| `denticion` | "cambia a temporal / mixta" | tipo | 1 |

El parser determinista ya existente (`dental_parser.py`) resuelve "dieciocho", "uno ocho",
"la 18". Si la pieza no existe en esa dentición ("la 19"), Dentia pregunta en vez de adivinar.

### 4.4 Diagnóstico y tratamiento
| Intención | Frases típicas | Campos | Nivel |
|---|---|---|---|
| `diagnostico` | "diagnóstico pulpitis reversible en la 36" | texto/código, pieza? | 3 |
| `procedimiento_planeado` | "planea resina en la 36 oclusal" | procedimiento (catálogo de la sucursal), pieza?, superficies? | 3 |
| `procedimiento_realizado` | "realicé la resina de la 36" | procedimiento planeado o del catálogo | 3 |

### 4.5 Agenda
| Intención | Frases típicas | Campos | Nivel |
|---|---|---|---|
| `agendar_cita` | "agéndale control en 15 días", "cita el martes a las 10" | fecha/plazo, hora?, tipo/duración (default del tipo), profesional (default: quien habla) | 3 |
| `reprogramar_cita` | "mueve su cita al jueves" | nueva fecha/hora | 3 |

Si falta la hora, Dentia **propone huecos libres reales** (respetando traslapes y horario):
"El 21 tienes libre a las 10:00 y a las 12:30, ¿cuál?".

---

## 5. Decisiones técnicas recomendadas

| Pieza | Recomendación | Por qué |
|---|---|---|
| **Captura de audio** | Navegador: `getUserMedia` + `AudioWorklet` a 16 kHz mono, con `echoCancellation`, `noiseSuppression` y `autoGainControl` activados | No se instala nada en las PCs de los consultorios |
| **Transporte** | WebSocket `/api/v1/voice/ws` (frames PCM de 20–30 ms) | Latencia baja en la red local; 16 kHz PCM ≈ 32 KB/s por consultorio |
| **Detector de "Dentia"** | **Etapa 1** (día 1, sin entrenar nada): VAD (Silero, ya viene con faster-whisper) + Whisper `tiny` sobre los fragmentos con voz, buscando que la frase **empiece** con "Dentia". **Etapa 2** (cuando se estabilice): modelo propio de palabra de activación entrenado con openWakeWord o su derivado `livekit-wakeword` (permite entrenar en español con voces sintéticas), que es mucho más ligero y no transcribe la conversación con el paciente | Funciona desde el primer día y luego se optimiza sin cambiar nada más |
| **Verificación anti-falsos** | Toda activación se confirma con la transcripción de Whisper de la orden: si no empieza por "Dentia" (y no estamos en ventana de seguimiento), se descarta en silencio | Evita que "dentista" o "de tía" la despierten |
| **Voz → texto (órdenes)** | El `faster-whisper` existente, con `language="es"`, `beam_size=1` para órdenes cortas y `hotwords` con nombres de pacientes del día + vocabulario dental | Ya está instalado y probado en el proyecto |
| **Entender la orden** | **Ruta rápida** (≈80 % de los casos): gramática/regex + `dental_parser.py` para navegación, odontograma, sí/no, cancelar, deshacer. **Ruta LLM** (resto): Ollama con JSON Schema **solo de las intenciones de la pantalla actual** y un prompt corto | En pruebas de la Fase 8, un dictado largo con el prompt completo tardó hasta 60–120 s en un 7B local; una orden con prompt reducido debe quedar en 2–4 s, y la ruta rápida en < 1 s |
| **Modelo Ollama** | Mantener cargado (`keep_alive: -1`). `qwen2.5:7b` con GPU; `qwen2.5:3b` si es solo CPU (las órdenes son cortas y la intención ya viene acotada) | Evita la espera de carga del modelo en cada orden |
| **Gestor de diálogo** | **Código Python determinista**, no el LLM: decide qué falta, qué preguntar, qué nivel de confirmación aplica y qué ejecutar | Un modelo de 7B no es fiable para llevar la conversación; el código sí |
| **Voz de Dentia (texto → voz)** | **Piper** con la voz `es_MX-claude-high` (femenina, español de México, local, rápida en CPU). Respaldo sin instalar nada: `speechSynthesis` del navegador con la voz de Windows "Sabina (México)" | Natural, local y sin costo; el respaldo garantiza que nunca se quede muda |
| **Respuestas habladas** | Frases precalculadas en caché ("Listo", "Cancelado", "¿Confirmas?", nombres de piezas) | Dentia responde al instante en las respuestas más comunes |

> Nota: verificar la licencia de la voz `es_MX-claude-high` en su ficha de `rhasspy/piper-voices`
> antes de distribuir el sistema comercialmente (el motor Piper es MIT; cada voz trae su propia
> licencia de datos).

### 5.1 Presupuesto de latencia (objetivo)
| Tramo | Objetivo |
|---|---|
| Decir "Dentia" → tono de activación | < 400 ms |
| Fin de la orden → respuesta hablada (ruta rápida) | < 1.5 s |
| Fin de la orden → respuesta hablada (ruta LLM) | < 4 s; si pasa de 2 s, Dentia dice "Un momento…" |
| "Cancela" → cancelado | < 500 ms (se reconoce por la ruta rápida) |

---

## 6. Arquitectura

```
┌──────────────────────── Navegador (React) ─────────────────────────┐
│ VoiceProvider (global, montado tras el login)                      │
│  ├─ AudioCapture (AudioWorklet 16 kHz)  ─── PCM ──┐                 │
│  ├─ DentiaOrb (estado, subtítulo en vivo, tarjeta con cuenta atrás) │
│  ├─ TtsPlayer (reproduce audio de Piper / fallback speechSynthesis)│
│  ├─ ScreenContext (ruta, paciente, atención, pestaña activa) ──┐   │
│  └─ UiActionBus (navegar, resaltar campo/pieza, abrir modal) ◄─┼─┐ │
└────────────────────────────────────────────────────────────────┼─┼─┘
                       WebSocket /api/v1/voice/ws                │ │
┌──────────────────────── Backend FastAPI ───────────────────────▼─┼─┐
│ app/voice/                                                       │ │
│  ws.py           sesión por usuario/pestaña, autenticación JWT    │ │
│  wake.py         Etapa 1: VAD + whisper tiny │ Etapa 2: openWakeWord│
│  endpointing.py  fin de frase por silencio (VAD)                  │ │
│  stt.py          reutiliza app/ai/stt.py                          │ │
│  nlu/fast.py     gramáticas + dental_parser (sin LLM)             │ │
│  nlu/llm.py      Ollama con esquema de intenciones de la pantalla │ │
│  intents/        registro declarativo (sec. 6.3)                  │ │
│  dialogue.py     máquina de estados, slots, confirmación, deshacer│ │
│  executors.py    llama a servicios de dominio vía app/ai/applier ─┘ │
│  tts.py          Piper + caché de frases                            │
│  models.py       VoiceCommandLog                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.1 Mensajes del WebSocket
| Dirección | Tipo | Contenido |
|---|---|---|
| cliente → servidor | `auth` | access token + `X-Clinic-Id` (primer mensaje) |
| cliente → servidor | `context` | `{route, patient_id, encounter_id, tab}` cada vez que cambia la pantalla |
| cliente → servidor | binario | frames PCM 16 kHz |
| cliente → servidor | `ui` | botón "Cancelar"/"Confirmar" de la tarjeta, pedal, mute |
| servidor → cliente | `state` | `passive / awake / listening / thinking / speaking / confirming / follow_up / muted` |
| servidor → cliente | `transcript` | texto reconocido (parcial y final) |
| servidor → cliente | `card` | lo que va a hacer, nivel, segundos de cuenta regresiva |
| servidor → cliente | `say` | texto + audio (ogg/opus) |
| servidor → cliente | `ui_action` | `navigate`, `highlight_tooth`, `highlight_field`, `open_modal`, `refresh` |
| servidor → cliente | `applied` / `undone` | id de la acción y entidad creada/anulada |

### 6.2 Máquina de estados del diálogo
```
PASSIVE ─wake─► LISTENING ─fin de frase─► THINKING ─┬─ faltan datos ─► ASKING ─respuesta─► THINKING
   ▲                                                ├─ nivel 1 ─► EXECUTE
   │                                                ├─ nivel 2 ─► COUNTDOWN(3 s) ─┬─ "cancela" ─► CANCELLED
   │                                                │                             └─ fin ──────► EXECUTE
   │                                                └─ nivel 3 ─► CONFIRMING ─┬─ "sí" ─► EXECUTE
   │                                                                          └─ "no" ─► CANCELLED
   └──── 8 s sin voz ◄── FOLLOW_UP ◄── EXECUTE / CANCELLED
```
- Mientras Dentia habla, se pausa la detección (evita que se escuche a sí misma), excepto las
  palabras "cancela/alto", que siempre interrumpen.
- `ASKING` admite como máximo 2 repreguntas; después, muestra opciones en pantalla.
- Cada sesión guarda una **pila de deshacer** con las últimas 10 acciones de la atención actual.

### 6.3 Registro de intenciones (ejemplo)
```python
# app/voice/intents/odontograma.py
Intent(
    name="hallazgo",
    screens={"atencion", "odontograma"},
    examples=["la 18 caries oclusal", "dieciocho ausente", "la 46 tiene resina"],
    slots=[
        Slot("tooth_fdi", type=Tooth, required=True, ask="¿Qué pieza?"),
        Slot("finding_code", type=Catalog("finding"), required=True, ask="¿Qué hallazgo?"),
        Slot("surfaces", type=Surfaces, required_if=finding_requires_surface,
             ask="¿En qué superficie? {opciones_para_la_pieza}"),
        Slot("material", type=str, required=False),
    ],
    level=Level.CAPTURE,                      # nivel 2
    say="Coloco {finding} en la {tooth}{, surfaces}.",
    action="add_tooth_finding",               # misma acción de app/ai/actions.py
    ui_after=[HighlightTooth("tooth_fdi")],
)
```
- Los **tipos de slot** reutilizan las reglas existentes: `Tooth` y `Surfaces` validan con
  `odontogram/rules.py` (superficies válidas según la pieza), `Catalog("procedure")` consulta
  `procedure_catalog` de la sucursal, `Patient` usa la búsqueda tolerante de pacientes.
- Del registro se generan automáticamente: el JSON Schema para Ollama (solo las intenciones de
  `screens` actuales), la gramática de la ruta rápida y la tarjeta "¿Qué puedo decir?".

### 6.4 Ejecución
Las intenciones de captura **no escriben directo**: crean la `AiSuggestion` como en la Fase 8 y,
al confirmarse por voz, llaman a `applier.py` (que ya usa los servicios de dominio con
`origin="AI_ASSISTED"`). Así no se duplica lógica y todo lo de la Fase 8 (validación, auditoría,
acciones prohibidas) sigue aplicando.

### 6.5 Deshacer
| Tipo de registro | Cómo se deshace |
|---|---|
| Alergia, medicamento, antecedente, diagnóstico | Anulación existente con motivo automático "Deshecho por voz" (regla 2) |
| Hallazgo de odontograma | **Nuevo** `odontogram_service.retire_finding` (como `retire_planned`): marca `is_current=False` y reactiva el evento que reemplazó (`supersedes_id`) — nunca borra |
| Texto agregado a la nota DRAFT | Se revierte el fragmento agregado (solo si la nota sigue en DRAFT) |
| Cita agendada | Cancelación con motivo "Deshecho por voz" |

Solo se puede deshacer dentro de la atención actual y lo hecho por voz.

---

## 7. Interfaz

- **Orbe de Dentia** fijo en la esquina inferior derecha, visible en toda la app para roles con
  `ai.use`. Colores por estado (variables de tema, nunca `#hex` fijo):
  gris = escucha pasiva · azul pulsante = escuchando · morado = pensando ·
  verde = hablando/ejecutado · ámbar = esperando confirmación · rojo tachado = micrófono apagado.
- **Subtítulo en vivo** de lo que entendió, en letra grande legible a 1.5 m del monitor.
- **Tarjeta de acción** con la cuenta regresiva (nivel 2) o botones Sí/No (nivel 3), por si el
  asistente prefiere tocar la pantalla.
- **Resaltado en contexto:** al capturar la 18, la pieza parpadea en el odontograma; al llenar
  "Motivo de consulta", el campo se ilumina. El odontólogo ve dónde quedó cada dato.
- **Clic en el orbe** = silenciar/activar. Atajo `Alt+M` y **pedal USB** (se configura como una
  tecla) = "escuchar ahora" sin decir "Dentia", útil con mucho ruido.
- **"¿Qué puedo decir?"**: tarjeta con las órdenes de la pantalla actual, también imprimible para
  pegar junto al monitor.
- **Bienvenida la primera vez:** Dentia se presenta, pide decir "Dentia" tres veces para ajustar
  la sensibilidad y enseña 3 órdenes básicas (menos de 1 minuto).

### 7.1 Inicio automático al iniciar sesión
- El navegador solo permite abrir el micrófono tras un gesto del usuario: se solicita
  `getUserMedia` **en el mismo clic de "Iniciar sesión"**. El permiso se recuerda después.
- **Requisito importante:** el micrófono solo funciona en contexto seguro (`https://` o
  `localhost`). Si la clínica entra por `http://192.168.x.x`, hay que servir el sistema con
  HTTPS en la red local (certificado de la CA interna o `mkcert`).
- Si hay varias pestañas abiertas, solo una tiene el micrófono (coordinadas con
  `BroadcastChannel`); las demás muestran el orbe en gris "activo en otra pestaña".
- Al cerrar sesión o tras la expiración de sesión, el micrófono se apaga.

---

## 8. Configuración (Configuración → Asistente IA → Dentia)

| Opción | Valores | Default |
|---|---|---|
| Activar Dentia | sí/no por usuario | sí para odontólogo/especialista |
| Iniciar escuchando al entrar | sí/no | sí |
| Sensibilidad de la palabra "Dentia" | baja / media / alta | media |
| Confirmación de capturas (nivel 2) | implícita 3 s / implícita 5 s / explícita "sí" | implícita 3 s |
| Ventana de seguimiento | 5 / 8 / 12 s | 8 s |
| Voz | `es_MX-claude-high` / voz del sistema | Piper |
| Velocidad y volumen de la voz | 0.8×–1.3× | 1.0× |
| Leer alertas al abrir expediente | sí/no | sí |
| Tono de activación | sí/no | sí |

Variables nuevas en `.env`:
```
VOICE_ENABLED=true
VOICE_WAKE_ENGINE=whisper_tiny     # whisper_tiny (etapa 1) | openwakeword (etapa 2)
VOICE_WAKE_MODEL_PATH=             # modelo .onnx/.tflite de "Dentia" para la etapa 2
VOICE_FOLLOWUP_S=8
VOICE_TTS_ENGINE=piper
VOICE_TTS_MODEL=es_MX-claude-high
OLLAMA_KEEP_ALIVE=-1
OLLAMA_INTENT_MODEL=qwen2.5:7b     # qwen2.5:3b en equipos sin GPU
```

---

## 9. Seguridad, privacidad y reglas del sistema

- **Regla 9 se mantiene con una precisión:** la IA nunca escribe sin aceptación; **la
  confirmación por voz cuenta como aceptación del odontólogo** (explícita en nivel 3, implícita
  con aviso visible y audible en nivel 2). El `AuditEvent ai.suggestion_accepted` guarda
  `confirmation_mode` (`voice_explicit`, `voice_implicit`, `touch`), la transcripción de la orden
  y la de la confirmación.
- **Audio:** se procesa en memoria y se descarta. La escucha pasiva usa un búfer circular de
  ~2 s que nunca se guarda ni se registra. Solo se registra el texto de las órdenes dirigidas a
  Dentia (`VoiceCommandLog`: usuario, intención, texto, resultado, latencia), nunca la
  conversación con el paciente.
- En la etapa 1 la conversación se transcribe en memoria para buscar "Dentia" y se descarta al
  instante; la etapa 2 elimina incluso eso. Es una razón más para migrar a la etapa 2.
- **Aviso de privacidad:** agregar una línea al aviso de la clínica indicando que el consultorio
  usa un asistente de voz local que no graba ni envía audio (LFPDPPP). Sugerido: un pequeño
  letrero en el consultorio.
- Permisos: usa `ai.use`; nueva opción `voice.use` si se quiere habilitar por separado.
- El WebSocket exige el mismo JWT y `X-Clinic-Id`; cada orden se ejecuta con los permisos del
  usuario que habla (Dentia no puede hacer nada que el usuario no pueda hacer a mano).

---

## 10. Hardware recomendado

| Elemento | Recomendación |
|---|---|
| **Micrófono** (lo más importante) | Diadema inalámbrica con micrófono de brazo o micrófono de solapa. El micrófono del monitor/laptop capta pieza de mano, succión y al paciente: más errores y más falsas activaciones |
| Pedal | Pedal USB de una tecla (opcional), configurado como "escuchar ahora" |
| Bocinas | Pequeñas, junto al monitor, volumen moderado |
| Servidor | Con GPU NVIDIA de 8 GB o más, Whisper + Ollama responden en 1–3 s. Solo CPU: funciona con `whisper small int8` y `qwen2.5:3b`, más lento en la ruta LLM |

---

## 11. Plan de implementación (para Claude Code)

| Etapa | Alcance | Criterio de aceptación |
|---|---|---|
| **13.1 Base de voz** | WebSocket, `AudioWorklet`, `VoiceProvider` global, orbe, VAD, detección etapa 1, Piper + caché, inicio automático al login, mute, `BroadcastChannel` | Decir "Dentia" enciende el orbe en < 400 ms; Dentia responde "¿Sí?" con voz femenina |
| **13.2 Navegación** | Registro de intenciones, ruta rápida, `abrir_expediente` (con desambiguación), `ir_a`, `leer_alertas`, `citas_hoy`, `ayuda`, `repetir`, `ScreenContext` + `UiActionBus` | Los dos primeros ejemplos de la sec. 2.2 funcionan de punta a punta |
| **13.3 Captura en consulta** | `iniciar_consulta`, odontograma, signos, motivo, nota, alergia, medicamento; niveles 2 y 3; ventana de seguimiento; cancelar; deshacer (incluye `retire_finding`) | 20 hallazgos seguidos dictados en el odontograma sin tocar el teclado; "cancela" y "deshaz" funcionan |
| **13.4 Diagnóstico, plan y agenda** | Diagnóstico, procedimientos, agendar/reprogramar con propuesta de huecos libres | Agendar un control por voz sin traslapes |
| **13.5 Ruta LLM y dictado** | Ollama con esquema por pantalla, `modo_dictado` integrado con la Fase 8, "Un momento…" si tarda | Frases libres resueltas en < 4 s en el equipo de la clínica |
| **13.6 Afinación** | Corpus de órdenes por voz (`tests/voice/commands.jsonl`, 150+ frases), `python -m app.voice.eval`, pruebas con audio grabado con ruido de consultorio, entrenamiento del modelo "Dentia" (etapa 2) | Activación ≥ 95 %, falsas activaciones < 1 por hora de consulta, intención correcta ≥ 90 % en la ruta rápida |

Pruebas automatizadas: el diálogo (`dialogue.py`) se prueba con texto, sin audio, igual que el
intérprete de la Fase 8 se prueba con `FakeOllama`. En E2E, `VOICE_FAKE_MODE` inyecta
transcripciones en lugar de audio.

---

## 12. Decisiones y pendientes

**Decidido (6 oct 2026):**
- Confirmación implícita de 3 s para capturas (nivel 2); configurable.
- La recepción también usa Dentia, limitada a agenda y pacientes (detalle en el doc 06, C2).
- Vocabulario técnico tomado de `docs/diccionario_odontologico_2023.pdf` (doc 06, C3).

**Pendiente de validar con la clínica:**
- Lista final de hallazgos que **requieren** superficie y los que son de toda la pieza.
- Nombres coloquiales de procedimientos ("resina", "curación", "limpieza") ↔ catálogo.
- Ruido real del consultorio con la pieza de mano: decide el micrófono final.
