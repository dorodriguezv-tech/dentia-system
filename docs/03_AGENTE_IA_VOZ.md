# Asistente de IA por voz (local con Ollama)

## 1. Objetivo
El odontólogo dicta mientras atiende, por ejemplo:

> “Paciente refiere dolor al frío en el lado inferior izquierdo. Alérgica a la penicilina. Pieza treinta y seis caries oclusal y distal. La cuarenta y seis tiene resina oclusal. Falta la dieciocho. Diagnóstico pulpitis reversible en la treinta y seis. Plan: resina en treinta y seis. Control en quince días.”

El asistente transcribe el dictado, lo interpreta y **propone** las acciones correspondientes. El odontólogo las revisa y las acepta, edita o rechaza una por una (o todas). Solo entonces se guardan.

## 2. Flujo
```
[Micrófono] → MediaRecorder (webm/opus, fragmentos de 5 s)
   → POST /ai/transcribe  → faster-whisper (language="es", initial_prompt con vocabulario dental)
   → texto (se muestra en vivo)
   → Pre-parser determinista (números FDI, superficies, palabras clave)
   → POST /ai/interpret   → Ollama /api/chat (format = JSON Schema, temperature 0)
   → Validación Pydantic + reglas (FDI válido, catálogos existentes, paciente/encounter correctos)
   → AiSuggestion[PENDING]  → panel "Propuestas del asistente"
   → Odontólogo: Aceptar / Editar / Rechazar  → servicio de dominio normal (origin=AI_ASSISTED) + AuditEvent
```

## 3. Componentes backend (`backend/app/ai/`)
| Archivo | Responsabilidad |
|---|---|
| `stt.py` | Carga única de `WhisperModel` (modelo configurable) y `transcribe(bytes) -> text` con VAD activado |
| `dental_parser.py` | Convierte números hablados a FDI (“treinta y seis” → 36, “tres seis” → 36), normaliza superficies (oclusal→O, mesial→M, distal→D, vestibular/bucal→V, lingual→L, palatino→P, incisal→I) y detecta dentición temporal (51–85) |
| `ollama_client.py` | Cliente httpx asíncrono hacia `/api/chat` y `/api/tags`, con timeout, reintento y health check |
| `prompts/system_es.md` | Prompt de sistema con reglas y ejemplos |
| `actions.py` | Modelos Pydantic de cada acción (unión discriminada por `type`) y su JSON Schema |
| `interpreter.py` | Orquesta: contexto + texto → Ollama → validación → AiSuggestion |
| `applier.py` | Aplica una sugerencia aceptada llamando al **servicio de dominio** (nunca SQL directo) |

## 4. Acciones soportadas (MVP)
| type | Destino | Campos |
|---|---|---|
| `set_chief_complaint` | Encounter | text |
| `add_allergy` | Expediente | substance, reaction?, severity? |
| `add_medication` | Expediente | name, dose?, frequency? |
| `add_medical_history` | Expediente | category, text |
| `add_vital_signs` | Encounter | bp_sys?, bp_dia?, hr?, temp? |
| `add_tooth_finding` | Odontograma | tooth_fdi, surfaces[], finding_code, material?, kind=EXISTING |
| `add_planned_procedure` | Plan | tooth_fdi?, surfaces[], procedure_code, notes? |
| `add_performed_procedure` | Atención | tooth_fdi?, surfaces[], procedure_code, notes? |
| `add_diagnosis` | Diagnóstico | text, diagnosis_code?, tooth_fdi? |
| `append_note` | Nota DRAFT | section (S/O/A/P/free), text |
| `schedule_followup` | Agenda (solo propuesta) | in_days, reason |

**Prohibido para la IA:** finalizar o firmar notas, borrar, recetar, cobrar o cambiar datos de identidad. Si el dictado lo pide, el asistente responde con un aviso para que el odontólogo lo haga manualmente.

## 5. Ejemplo de salida esperada
```json
{
  "actions": [
    {"type":"set_chief_complaint","text":"Dolor al frío en lado inferior izquierdo"},
    {"type":"add_allergy","substance":"Penicilina"},
    {"type":"add_tooth_finding","tooth_fdi":36,"surfaces":["O","D"],"finding_code":"CARIES"},
    {"type":"add_tooth_finding","tooth_fdi":46,"surfaces":["O"],"finding_code":"RESTAURACION","material":"resina"},
    {"type":"add_tooth_finding","tooth_fdi":18,"surfaces":[],"finding_code":"AUSENTE"},
    {"type":"add_diagnosis","text":"Pulpitis reversible","tooth_fdi":36},
    {"type":"add_planned_procedure","tooth_fdi":36,"surfaces":["O","D"],"procedure_code":"RESINA"},
    {"type":"schedule_followup","in_days":15,"reason":"Control"}
  ],
  "unrecognized": []
}
```

## 6. Prompt de sistema (base, en `prompts/system_es.md`)
```
Eres un asistente de captura clínica odontológica. Conviertes el dictado de un odontólogo
en acciones JSON estructuradas. NO diagnosticas, NO inventas datos y NO completas lo que
no se dijo. Usa notación FDI. Superficies: O,M,D,V,L,P,I.
Usa solo los códigos de los catálogos proporcionados; si no existe, pon el texto en
"unrecognized". Si un dato es ambiguo (pieza no clara), no generes la acción y agrégalo
a "unrecognized" con el motivo. Responde solo con JSON válido según el esquema.
Catálogos: {finding_codes} {procedure_codes} {diagnosis_codes}
Contexto: pantalla={screen}, dentición={denticion}
```
Se incluyen 5–8 ejemplos “few-shot” de dictado → JSON. El pre-parser envía al modelo los números FDI ya resueltos como pistas.

## 7. Configuración (`.env`)
```
AI_ENABLED=true
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b          # alternativa: llama3.1:8b ; equipos modestos: qwen2.5:3b
OLLAMA_TIMEOUT_S=120
WHISPER_MODEL=small              # medium/large-v3 = más precisión, requieren más RAM/GPU
WHISPER_DEVICE=cpu               # cuda si hay GPU NVIDIA
WHISPER_COMPUTE_TYPE=int8
AI_STORE_AUDIO=false
AI_SUGGESTION_TTL_HOURS=24
```
Estos ajustes también se pueden editar desde **Configuración → Asistente IA** (modelo, prueba de micrófono, estado de Ollama).

## 8. Interfaz
- Botón de micrófono con tres estados: inactivo, escuchando (onda animada) y procesando.
- Transcripción en vivo, editable antes de interpretarla.
- Panel de propuestas agrupadas por destino (Expediente, Odontograma, Diagnóstico, Plan). Cada tarjeta lleva un ícono “IA”, vista previa (por ejemplo, la pieza resaltada en el odontograma en color fantasma) y botones Aceptar / Editar / Rechazar, además de “Aceptar todo”.
- Las alertas críticas se revisan también aquí: si se propone un procedimiento y el paciente tiene alergias, se muestra la alerta antes de aceptar.
- Si Ollama no está disponible, la transcripción sigue funcionando y se ofrece “Insertar como texto en la nota”.

## 9. Privacidad y trazabilidad
- Procesamiento 100 % local; no se hacen llamadas a internet.
- El audio se descarta después de transcribir (salvo que `AI_STORE_AUDIO=true`, con retención limitada).
- Cada sugerencia guarda el modelo, el digest del modelo de Ollama, un extracto de la transcripción y quién la aceptó.
- Los permisos `ai.use` (odontólogo, especialista) y `ai.configure` (admin) son independientes.

## 10. Calidad
- `backend/tests/ai/corpus.jsonl`: 40 o más dictados de ejemplo con el JSON esperado.
- `python -m app.ai.eval` mide la precisión por tipo de acción, las piezas FDI correctas y las superficies correctas.
- Pruebas unitarias del `dental_parser` (números del 11 al 85 hablados de varias formas).
- Las pruebas de integración usan un `FakeOllama` (no requieren el modelo real en CI).
