"""Ruta LLM para agenda por voz (Fase 13, 13.5 "Ruta LLM y dictado", resto
pendiente de docs/02_ARQUITECTURA.md sec. 5.20): cuando `nlu_fast` no
reconoce una orden de agenda porque no calza con las anclas de palabra clave
("agenda a <paciente> el <dia> a las <hora> con <profesional>"), se intenta
una vez con Ollama antes de rendirse con "no te entendi".

A proposito NO resuelve fechas/horas a un valor final -- el esquema le pide
al modelo que las devuelva en el MISMO formato de texto que ya entiende
`app/voice/datetime_parse.py` ("manana", "el jueves", "en 3 dias", "a las
10"). Asi, el resultado del LLM se convierte en un `dict` de slots IDENTICO
al que ya producen los regex de `nlu_fast.py`, y `dialogue.py` lo pasa por
los MISMOS manejadores (`_handle_agendar_cita`, etc.) que la ruta rapida --
sin esquema de voz aparte ni logica de agenda duplicada (mismo criterio que
la ruta LLM clinica de `app/ai/interpreter.py`, sec. 5 del diseno)."""

from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import BaseModel, Field, ValidationError

from app.ai import ollama_client
from app.ai.ollama_client import OllamaUnavailableError
from app.core.config import get_settings

_SYSTEM_PROMPT = """Eres el modulo de comprension de ordenes de agenda de \
"Dentia", el asistente de voz de una clinica dental mexicana. Recepcion o un \
odontologo te dicta una orden sobre citas en espanol; tu unico trabajo es \
reconocer de que tipo de orden se trata y extraer sus datos en el formato \
EXACTO que se describe abajo -- nunca inventes un dato que no se haya dicho.

Tipos de orden (campo "type"):
- "agendar_cita": agendar una cita nueva. Requiere patient_name. Opcionales: \
provider_name, date_text, time_text, appointment_type_hint.
- "reprogramar_cita": mover una cita existente a otro dia/hora. Requiere \
patient_name y date_text. Opcional: time_text.
- "confirmar_cita": confirmar una cita de hoy. patient_name o time_text \
(al menos uno).
- "registrar_llegada": marcar que un paciente ya llego. Requiere \
patient_name.
- "cancelar_cita": cancelar una cita. Requiere reason (el motivo SIEMPRE se \
dice en la misma frase, p.ej. "motivo: enfermedad" -- si no hay motivo, NO \
generes esta accion). patient_name o time_text (al menos uno).
- "no_show": el paciente no se presento a su cita de hoy. Requiere \
patient_name.
- "lista_espera": agregar a un paciente a la lista de espera. patient_name \
es el nombre si se dijo uno; si en vez de un nombre se usa un pronombre \
("ella", "el", "la", "lo", p.ej. "ponla tambien en la lista de espera"), \
deja patient_name vacio (null) -- el sistema ya sabe de que paciente se \
trata por la conversacion.
- "huecos_libres": preguntar que horarios tiene libres un profesional. \
Requiere provider_name. Opcional: date_text.

Formato OBLIGATORIO de date_text (nunca una fecha calendario): "hoy", \
"manana", un dia de la semana en minusculas ("jueves"), o "en N dias". \
Formato OBLIGATORIO de time_text: solo el numero/hora tal como se dijo, sin \
el prefijo "a las" (p.ej. "10", "10:30", "diez y media").

Si la frase no es una orden de agenda, o no tiene los datos obligatorios de \
ningun tipo, responde con action = null. Nunca adivines un nombre, dia u \
hora que no se haya dicho."""


class AgendarCitaAction(BaseModel):
    type: Literal["agendar_cita"] = "agendar_cita"
    patient_name: str = Field(min_length=1, max_length=200)
    provider_name: str | None = None
    date_text: str | None = None
    time_text: str | None = None
    appointment_type_hint: str | None = None


class ReprogramarCitaAction(BaseModel):
    type: Literal["reprogramar_cita"] = "reprogramar_cita"
    patient_name: str = Field(min_length=1, max_length=200)
    date_text: str = Field(min_length=1, max_length=50)
    time_text: str | None = None


class ConfirmarCitaAction(BaseModel):
    type: Literal["confirmar_cita"] = "confirmar_cita"
    patient_name: str | None = None
    time_text: str | None = None


class RegistrarLlegadaAction(BaseModel):
    type: Literal["registrar_llegada"] = "registrar_llegada"
    patient_name: str = Field(min_length=1, max_length=200)


class CancelarCitaAction(BaseModel):
    type: Literal["cancelar_cita"] = "cancelar_cita"
    patient_name: str | None = None
    time_text: str | None = None
    reason: str = Field(min_length=1, max_length=500)


class NoShowAction(BaseModel):
    type: Literal["no_show"] = "no_show"
    patient_name: str = Field(min_length=1, max_length=200)


class ListaEsperaAction(BaseModel):
    type: Literal["lista_espera"] = "lista_espera"
    # A diferencia de los demas (nombre siempre obligatorio): "agrégala a la
    # lista de espera" es justo el ejemplo pronominal de C2 del doc 06. Vacio
    # cuando se usa un pronombre -- dialogue.py lo resuelve contra el ultimo
    # paciente de la conexion (`last_patient`), igual que la ruta rapida.
    patient_name: str | None = Field(default=None, max_length=200)


class HuecosLibresAction(BaseModel):
    type: Literal["huecos_libres"] = "huecos_libres"
    provider_name: str = Field(min_length=1, max_length=200)
    date_text: str | None = None


AgendaAction = Annotated[
    AgendarCitaAction
    | ReprogramarCitaAction
    | ConfirmarCitaAction
    | RegistrarLlegadaAction
    | CancelarCitaAction
    | NoShowAction
    | ListaEsperaAction
    | HuecosLibresAction,
    Field(discriminator="type"),
]


class AgendaInterpretResult(BaseModel):
    action: AgendaAction | None = None


async def interpret_agenda_order(transcript: str) -> AgendaInterpretResult | None:
    """Devuelve `None` si Ollama no responde, la respuesta no es JSON valido,
    o no calza con el esquema -- el llamador (`dialogue.py`) lo trata igual
    que "no reconoci nada" y cae en "no te entendi", nunca deja que un error
    de esta ruta tumbe la sesion de voz."""
    settings = get_settings()
    try:
        response = await ollama_client.chat(
            model=settings.ollama_intent_model,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=transcript,
            json_schema=AgendaInterpretResult.model_json_schema(),
            keep_alive=settings.ollama_keep_alive,
        )
    except OllamaUnavailableError:
        return None

    content = response.get("message", {}).get("content", "")
    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        return None

    try:
        return AgendaInterpretResult.model_validate(raw)
    except ValidationError:
        return None
