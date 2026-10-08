"""Gestor de dialogo (13.2 "Navegacion", 13.3 "Captura en consulta"): entiende
la orden ya transcrita (ruta rapida, nlu_fast.py -- Ollama con el esquema de
intenciones de la pantalla es 13.5, todavia no existe) y decide que responder
y que hacer. Codigo Python deterministico, no un LLM (sec. 5 del diseno): "un
modelo de 7B no es fiable para llevar la conversacion; el codigo si".

Solo las intenciones GLOBALES de la sec. 4.1 y las de atencion/odontograma de
la sec. 4.2/4.3 que ya tienen criterio de aceptacion en 13.3 (`iniciar_consulta`,
`hallazgo`); el resto de la sec. 4.2-4.5 (signos, motivo, nota, alergia,
medicamento, diagnostico, agenda) y el filtrado por pantalla (`screens` del
registro de intenciones de la sec. 6.3) quedan para una siguiente etapa.

Las intenciones de captura (nivel 2/3, sec. 3 y 6.4 del diseno) NO ejecutan de
inmediato: devuelven un `PendingCapture` con la frase de vista previa y un
`execute()` que crea la `AiSuggestion` y la aplica via `app/ai/applier.py` --
la misma ruta de la Fase 8, con `confirmation_mode="voice_implicit"` (nivel 2)
o "voice_explicit" (nivel 3). `session.py` es quien de verdad maneja la cuenta
regresiva/espera de "si" y llama a `execute()` cuando corresponde.
"""

from __future__ import annotations

import re
import unicodedata
import urllib.parse
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import applier as ai_applier
from app.ai import interpreter as ai_interpreter
from app.ai.models import AiSuggestion
from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.agenda import rules as agenda_rules
from app.modules.agenda import service as agenda_service
from app.modules.agenda.schemas import (
    AppointmentCreateRequest,
    RescheduleRequest,
    StatusChangeRequest,
    WaitlistCreateRequest,
)
from app.modules.catalogs import service as catalogs_service
from app.modules.encounters import service as encounters_service
from app.modules.encounters.models import Encounter
from app.modules.encounters.schemas import EncounterCreateRequest
from app.modules.iam.models import Clinic
from app.modules.iam.rules import DEFAULT_CLINIC_TIMEZONE
from app.modules.odontogram import service as odontogram_service
from app.modules.patients import service as patients_service
from app.modules.patients.models import Patient
from app.modules.records import service as records_service
from app.modules.treatment import service as treatment_service
from app.voice import agenda_llm, datetime_parse, nlu_fast
from app.voice.context import ScreenContext

_RESOLVED_APPOINTMENT_STATUSES = {"CANCELADA", "NO_SHOW", "REPROGRAMADA"}
_MAX_DISAMBIGUATION_NAMES = 5


async def _clinic_zoneinfo(db: AsyncSession, *, clinic_id: uuid.UUID) -> ZoneInfo:
    """Bug #42 de docs/PENDIENTES_CLINICOS.md: "hoy" para citas/atenciones debe
    calcularse con la zona horaria de la SUCURSAL (`Clinic.timezone`), nunca
    con la hora local del servidor -- las columnas son TIMESTAMPTZ en UTC, y
    `date.today()`/`datetime.now(UTC).date()` del servidor pueden ya ser un
    dia distinto al que es "hoy" para la clinica (p.ej. Mexico, UTC-6, entre
    que el reloj local marca la tarde y la medianoche)."""
    clinic = await db.get(Clinic, clinic_id)
    tz_name = clinic.timezone if clinic else DEFAULT_CLINIC_TIMEZONE
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo(DEFAULT_CLINIC_TIMEZONE)


def _local_day_bounds_utc(tz: ZoneInfo, day: date) -> tuple[datetime, datetime]:
    """[00:00, 24:00) de ESE dia en `tz`, convertido a UTC -- para consultar
    columnas TIMESTAMPTZ (siempre en UTC) por el dia DE LA SUCURSAL, no por el
    dia calendario UTC (que puede ser un dia distinto, ver #42 arriba)."""
    start_local = datetime.combine(day, time.min, tzinfo=tz)
    return start_local.astimezone(UTC), (start_local + timedelta(days=1)).astimezone(UTC)


_UNRECOGNIZED_SAY = "No te entendí, ¿me lo repites?"

_SURFACE_LABELS = {
    "O": "oclusal",
    "M": "mesial",
    "D": "distal",
    "V": "vestibular",
    "L": "lingual",
    "P": "palatina",
    "I": "incisal",
}


def _join_es(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} y {items[-1]}"


@dataclass
class UiAction:
    action: str
    payload: dict[str, object] = field(default_factory=dict)


@dataclass
class UndoEntry:
    """Lo que `session.py` apila para "deshaz" (sec. 6.5 del diseno) -- solo
    lo necesario para revertir, no una copia completa de la captura."""

    action_type: str
    entity_id: str
    patient_id: str
    say: str


@dataclass
class PendingCapture:
    """Una captura (nivel 2 o 3) que todavia no se ejecuto -- `session.py`
    decide CUANDO llamar a `execute()` (cuenta regresiva de 3 s sin "cancela",
    o "si" explicito), nunca `dialogue.py` (que no tiene temporizadores)."""

    level: int
    say_preview: str
    confirm_prompt: str | None
    execute: Callable[[], Awaitable[DialogueResult]]
    cancel_say: str = "Cancelado."


@dataclass
class DialogueResult:
    say: str
    ui_actions: list[UiAction] = field(default_factory=list)
    pending: PendingCapture | None = None
    undo_entry: UndoEntry | None = None
    pop_undo: bool = False
    encounter_id: str | None = None
    start_dictation: bool = False
    # 13.4 (resto): el paciente que una intencion de agenda acaba de resolver --
    # `session.py` lo recuerda para que "agregala a la lista de espera" (C2 del
    # doc 06) sepa a quien se refiere "la" sin que haga falta repetir el nombre.
    patient_ref: tuple[str, str] | None = None


async def handle_order(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    transcript: str,
    context: ScreenContext,
    last_say: str | None,
    has_clinical: bool,
    active_encounter_id: str | None = None,
    undo_top: UndoEntry | None = None,
    last_patient: tuple[str, str] | None = None,
) -> DialogueResult:
    fast_match = nlu_fast.match(transcript)
    if fast_match is None:
        # Ruta LLM clinica (13.5, sec. 5 del diseno): solo con una atencion
        # activa y `voice.clinical` -- reusa el esquema de 11 acciones de la
        # Fase 8 (interpreter.py), que no varia por pantalla/rol (esquema
        # dinamico por pantalla, sec. 5/6.3 del diseno, sigue pendiente).
        if has_clinical and active_encounter_id:
            llm_result = await _try_llm_fallback(
                db,
                clinic_id=clinic_id,
                user_id=user_id,
                encounter_id=active_encounter_id,
                transcript=transcript,
            )
            if llm_result is not None:
                return llm_result
        # Ruta LLM de agenda (resto de 13.5, pendiente explicito de la sec.
        # 5.20): disponible para CUALQUIERA con `voice.use` -- a diferencia
        # de la clinica, no exige atencion activa ni `voice.clinical`, es
        # justo lo que recepcion puede hacer por rol (igual que la agenda de
        # la ruta rapida, C2 del doc 06). Se intenta despues de la clinica
        # (nunca antes) para no desplazar un dictado clinico real.
        agenda_llm_result = await _try_agenda_llm_fallback(
            db,
            clinic_id=clinic_id,
            user_id=user_id,
            transcript=transcript,
            last_patient=last_patient,
        )
        if agenda_llm_result is not None:
            return agenda_llm_result
        return DialogueResult(say=_UNRECOGNIZED_SAY)

    intent = fast_match.intent
    if intent == "ayuda":
        return DialogueResult(
            say=(
                "Puedo abrir el expediente de un paciente, llevarte a otra pantalla, "
                "leerte las alertas del paciente actual, decirte tus citas de hoy, "
                "iniciar la consulta y capturar hallazgos del odontograma."
            ),
            ui_actions=[UiAction("show_help")],
        )
    if intent == "repetir":
        return DialogueResult(say=last_say or "Todavía no he dicho nada.")
    if intent == "silencio":
        return DialogueResult(say="Entendido, me quedo callada.", ui_actions=[UiAction("mute")])
    if intent == "ir_a":
        return _handle_ir_a(fast_match.slots["destino"], context)
    if intent == "abrir_expediente":
        return await _handle_abrir_expediente(
            db, clinic_id=clinic_id, query=fast_match.slots["query"]
        )
    if intent == "leer_alertas":
        if not has_clinical:
            return DialogueResult(say="Eso no lo puedo hacer con tu rol.")
        return await _handle_leer_alertas(db, clinic_id=clinic_id, context=context)
    if intent == "citas_hoy":
        return await _handle_citas_hoy(db, clinic_id=clinic_id, user_id=user_id)
    if intent == "iniciar_consulta":
        if not has_clinical:
            return DialogueResult(say="Eso no lo puedo hacer con tu rol.")
        return await _handle_iniciar_consulta(
            db, clinic_id=clinic_id, user_id=user_id, context=context
        )
    if intent == "hallazgo":
        if not has_clinical:
            return DialogueResult(say="Eso no lo puedo hacer con tu rol.")
        return await _handle_hallazgo(
            db,
            clinic_id=clinic_id,
            user_id=user_id,
            context=context,
            active_encounter_id=active_encounter_id,
            slots=fast_match.slots,
        )
    if intent == "diagnostico":
        if not has_clinical:
            return DialogueResult(say="Eso no lo puedo hacer con tu rol.")
        return await _handle_diagnostico(
            db,
            clinic_id=clinic_id,
            user_id=user_id,
            context=context,
            active_encounter_id=active_encounter_id,
            slots=fast_match.slots,
        )
    if intent == "procedimiento_planeado":
        if not has_clinical:
            return DialogueResult(say="Eso no lo puedo hacer con tu rol.")
        return await _handle_procedimiento_planeado(
            db,
            clinic_id=clinic_id,
            user_id=user_id,
            context=context,
            active_encounter_id=active_encounter_id,
            slots=fast_match.slots,
        )
    if intent == "procedimiento_realizado":
        if not has_clinical:
            return DialogueResult(say="Eso no lo puedo hacer con tu rol.")
        return await _handle_procedimiento_realizado(
            db,
            clinic_id=clinic_id,
            user_id=user_id,
            context=context,
            active_encounter_id=active_encounter_id,
            slots=fast_match.slots,
        )
    if intent == "deshacer":
        return await _handle_deshacer(db, clinic_id=clinic_id, user_id=user_id, undo_top=undo_top)
    if intent == "agendar_cita":
        # Agenda por voz (13.4, C2 del doc 06): disponible para cualquiera con
        # `voice.use` -- es exactamente lo que recepcion puede hacer, sin
        # exigir `voice.clinical` (a diferencia de iniciar_consulta/hallazgo).
        return await _handle_agendar_cita(
            db, clinic_id=clinic_id, user_id=user_id, slots=fast_match.slots
        )
    if intent == "reprogramar_cita":
        return await _handle_reprogramar_cita(
            db, clinic_id=clinic_id, user_id=user_id, slots=fast_match.slots
        )
    if intent == "confirmar_cita":
        return await _handle_confirmar_cita(
            db, clinic_id=clinic_id, user_id=user_id, slots=fast_match.slots
        )
    if intent == "registrar_llegada":
        return await _handle_registrar_llegada(
            db, clinic_id=clinic_id, user_id=user_id, slots=fast_match.slots
        )
    if intent == "huecos_libres":
        return await _handle_huecos_libres(db, clinic_id=clinic_id, slots=fast_match.slots)
    if intent == "cancelar_cita":
        return await _handle_cancelar_cita(
            db, clinic_id=clinic_id, user_id=user_id, slots=fast_match.slots
        )
    if intent == "no_show":
        return await _handle_no_show(
            db, clinic_id=clinic_id, user_id=user_id, slots=fast_match.slots
        )
    if intent == "lista_espera":
        return await _handle_lista_espera(
            db,
            clinic_id=clinic_id,
            user_id=user_id,
            slots=fast_match.slots,
            last_patient=last_patient,
        )
    if intent == "alta_rapida_paciente":
        return _handle_alta_rapida_paciente(fast_match.slots)
    if intent == "modo_dictado":
        if not has_clinical:
            return DialogueResult(say="Eso no lo puedo hacer con tu rol.")
        if not active_encounter_id:
            return DialogueResult(say="Primero inicia la consulta.")
        return DialogueResult(
            say='Te escucho. Di "fin del dictado" cuando termines.', start_dictation=True
        )

    return DialogueResult(say=_UNRECOGNIZED_SAY)


_TAB_DESTINATIONS = {"expediente", "odontograma", "tratamientos", "imagenes", "consentimientos"}
_STANDALONE_ROUTES = {"agenda": "/agenda", "inicio": "/", "pacientes": "/pacientes"}


def _handle_ir_a(destino: str, context: ScreenContext) -> DialogueResult:
    if destino in _TAB_DESTINATIONS:
        if not context.patient_id:
            return DialogueResult(say="Primero dime de qué paciente, o abre uno.")
        return DialogueResult(
            say=f"Abriendo {destino}.",
            ui_actions=[
                UiAction(
                    "navigate",
                    {"path": f"/pacientes/{context.patient_id}", "tab": destino},
                )
            ],
        )
    path = _STANDALONE_ROUTES.get(destino)
    if path is None:
        return DialogueResult(say="No conozco esa pantalla todavía.")
    return DialogueResult(
        say=f"Abriendo {destino}.", ui_actions=[UiAction("navigate", {"path": path})]
    )


async def _handle_abrir_expediente(
    db: AsyncSession, *, clinic_id: uuid.UUID, query: str
) -> DialogueResult:
    matches = await patients_service.search_patients(db, clinic_id=clinic_id, query=query)
    if not matches:
        return DialogueResult(say=f"No encontré a nadie llamado {query}.")
    if len(matches) == 1:
        patient = matches[0]
        return DialogueResult(
            say=f"Abriendo expediente de {patient.full_name}.",
            ui_actions=[UiAction("navigate", {"path": f"/pacientes/{patient.id}"})],
        )
    names = ", ".join(p.full_name for p in matches[:_MAX_DISAMBIGUATION_NAMES])
    return DialogueResult(say=f"Hay varios: {names}. ¿Cuál?")


async def _handle_leer_alertas(
    db: AsyncSession, *, clinic_id: uuid.UUID, context: ScreenContext
) -> DialogueResult:
    if not context.patient_id:
        return DialogueResult(say="¿De qué paciente quieres saber las alertas?")
    alerts = await records_service.get_patient_alerts(
        db, clinic_id=clinic_id, patient_id=uuid.UUID(context.patient_id)
    )
    if not alerts:
        return DialogueResult(say="No tiene alertas registradas.")
    return DialogueResult(say=". ".join(alerts))


async def _handle_citas_hoy(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID
) -> DialogueResult:
    provider = await agenda_service.get_provider_for_user(db, clinic_id=clinic_id, user_id=user_id)
    if provider is None:
        return DialogueResult(say="No tienes una agenda propia en esta sucursal.")

    tz = await _clinic_zoneinfo(db, clinic_id=clinic_id)
    today = datetime.now(tz).date()
    starts_from, starts_to = _local_day_bounds_utc(tz, today)
    appointments = await agenda_service.list_appointments(
        db,
        clinic_id=clinic_id,
        starts_from=starts_from,
        starts_to=starts_to,
        provider_id=provider.id,
    )
    active = [a for a in appointments if a["status"] not in _RESOLVED_APPOINTMENT_STATUSES]
    if not active:
        return DialogueResult(say="No tienes citas hoy.")

    now = datetime.now(UTC)
    upcoming = [
        a
        for a in active
        if isinstance(a["starts_at"], datetime)
        and a["starts_at"] >= now
        and a["status"] != "TERMINADA"
    ]
    count = len(active)
    plural = "citas" if count != 1 else "cita"
    if not upcoming:
        return DialogueResult(say=f"Tienes {count} {plural} hoy, ya todas pasaron.")

    next_appointment = upcoming[0]
    next_starts_at = next_appointment["starts_at"]
    assert isinstance(next_starts_at, datetime)
    hour = next_starts_at.strftime("%H:%M")
    return DialogueResult(
        say=(
            f"Tienes {count} {plural} hoy. La siguiente es "
            f"{next_appointment['patient_full_name']} a las {hour}."
        )
    )


async def _find_or_create_todays_encounter(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID, professional_id: uuid.UUID
) -> Encounter:
    """Misma idea que `useEncounterPicker.ts` en el frontend (preseleccionar la
    atencion de hoy si existe) pero del lado del servidor, porque Dentia no
    puede esperar a que el odontologo elija una en un menu."""
    encounters = await encounters_service.list_patient_encounters(
        db, clinic_id=clinic_id, patient_id=patient_id
    )
    tz = await _clinic_zoneinfo(db, clinic_id=clinic_id)
    today = datetime.now(tz).date()
    for encounter in encounters:
        if encounter.started_at.astimezone(tz).date() == today:
            return encounter
    return await encounters_service.create_encounter(
        db,
        clinic_id=clinic_id,
        data=EncounterCreateRequest(patient_id=patient_id),
        professional_id=professional_id,
    )


async def _handle_iniciar_consulta(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, context: ScreenContext
) -> DialogueResult:
    if not context.patient_id:
        return DialogueResult(say="Primero abre el expediente de un paciente.")

    patient_id = uuid.UUID(context.patient_id)
    patient = await patients_service.get_patient(
        db, clinic_id=clinic_id, patient_id=patient_id, actor_id=user_id
    )
    preview = f"Inicio la consulta de {patient.full_name}."

    async def _execute() -> DialogueResult:
        encounter = await _find_or_create_todays_encounter(
            db, clinic_id=clinic_id, patient_id=patient_id, professional_id=user_id
        )
        alerts = await records_service.get_patient_alerts(
            db, clinic_id=clinic_id, patient_id=patient_id
        )
        say = "Consulta iniciada."
        if alerts:
            say = f"{say} " + ". ".join(alerts) + "."
        return DialogueResult(say=say, encounter_id=str(encounter.id))

    return DialogueResult(
        say=preview,
        pending=PendingCapture(
            level=3, say_preview=preview, confirm_prompt="¿Confirmas?", execute=_execute
        ),
    )


async def _handle_hallazgo(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    context: ScreenContext,
    active_encounter_id: str | None,
    slots: dict[str, str],
) -> DialogueResult:
    if not context.patient_id:
        return DialogueResult(say="Primero abre el expediente de un paciente.")
    if not active_encounter_id:
        return DialogueResult(say="Primero inicia la consulta.")

    tooth_fdi = int(slots["tooth_fdi"])
    finding_code = slots["finding_code"]
    surfaces = [s for s in slots.get("surfaces", "").split(",") if s]

    finding_items = await catalogs_service.list_items(
        db, clinic_id=clinic_id, catalog_type="odontogram_finding"
    )
    finding_item = next((f for f in finding_items if f.code == finding_code), None)
    if finding_item is None:
        return DialogueResult(say="No conozco ese hallazgo todavía.")
    if finding_item.extra.get("requires_surface") and not surfaces:
        return DialogueResult(
            say=(
                f"¿En qué superficie? Dime de nuevo la pieza, {finding_item.name.lower()} "
                "y la superficie: oclusal, mesial, distal, vestibular o palatina."
            )
        )

    patient_id = context.patient_id
    encounter_id = active_encounter_id
    surface_words = [_SURFACE_LABELS.get(s, s) for s in surfaces]
    description = f"{finding_item.name.lower()} en la {tooth_fdi}"
    if surface_words:
        description += f", {_join_es(surface_words)}"
    preview = f"Coloco {description}."

    async def _execute() -> DialogueResult:
        suggestion = AiSuggestion(
            clinic_id=clinic_id,
            patient_id=uuid.UUID(patient_id),
            encounter_id=uuid.UUID(encounter_id),
            batch_id=uuid.uuid4(),
            action_type="add_tooth_finding",
            payload={
                "tooth_fdi": tooth_fdi,
                "surfaces": surfaces,
                "finding_code": finding_code,
                "material": None,
            },
            status="PENDING",
            model_name="dentia_fast_path",
            model_digest=None,
            transcript_excerpt=preview[:500],
            created_by=user_id,
        )
        db.add(suggestion)
        await db.flush()
        await db.commit()

        _, entity_id = await ai_applier.accept_suggestion(
            db,
            clinic_id=clinic_id,
            suggestion_id=suggestion.id,
            edits=None,
            actor_id=user_id,
            confirmation_mode="voice_implicit",
        )
        assert entity_id is not None
        return DialogueResult(
            say="",
            ui_actions=[UiAction("highlight_tooth", {"tooth_fdi": tooth_fdi})],
            undo_entry=UndoEntry(
                action_type="add_tooth_finding",
                entity_id=entity_id,
                patient_id=patient_id,
                say=description,
            ),
        )

    return DialogueResult(
        say=preview,
        pending=PendingCapture(level=2, say_preview=preview, confirm_prompt=None, execute=_execute),
    )


# ------------------------------------------- 13.4 (mitad clinica): diagnostico
# ------------------------------------------- y procedimientos planeados/realizados


async def _handle_diagnostico(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    context: ScreenContext,
    active_encounter_id: str | None,
    slots: dict[str, str],
) -> DialogueResult:
    """`diagnostico` (mitad clinica de 13.4, doc 06): a diferencia de
    `hallazgo`, el texto del diagnostico es libre (no hay catalogo cerrado que
    reconocer) -- solo se reconoce el verbo que introduce la orden
    (`nlu_fast._DIAGNOSTICO_RE`) y la pieza, si se menciona. Nivel 3 (no 2
    como `hallazgo`): un diagnostico es una decision clinica puntual, no una
    captura repetitiva fila tras fila."""
    if not context.patient_id:
        return DialogueResult(say="Primero abre el expediente de un paciente.")
    if not active_encounter_id:
        return DialogueResult(say="Primero inicia la consulta.")

    text = slots["text"]
    tooth_raw = slots.get("tooth_fdi", "")
    tooth_fdi = int(tooth_raw) if tooth_raw else None
    patient_id = context.patient_id
    encounter_id = active_encounter_id
    preview = f"Registro diagnóstico: {text}."

    async def _execute() -> DialogueResult:
        suggestion = AiSuggestion(
            clinic_id=clinic_id,
            patient_id=uuid.UUID(patient_id),
            encounter_id=uuid.UUID(encounter_id),
            batch_id=uuid.uuid4(),
            action_type="add_diagnosis",
            payload={"text": text, "diagnosis_code": None, "tooth_fdi": tooth_fdi},
            status="PENDING",
            model_name="dentia_fast_path",
            model_digest=None,
            transcript_excerpt=preview[:500],
            created_by=user_id,
        )
        db.add(suggestion)
        await db.flush()
        await db.commit()

        _, entity_id = await ai_applier.accept_suggestion(
            db,
            clinic_id=clinic_id,
            suggestion_id=suggestion.id,
            edits=None,
            actor_id=user_id,
            confirmation_mode="voice_explicit",
        )
        assert entity_id is not None
        return DialogueResult(say="Diagnóstico registrado.")

    return DialogueResult(
        say=preview,
        pending=PendingCapture(
            level=3, say_preview=preview, confirm_prompt="¿Confirmas?", execute=_execute
        ),
    )


async def _find_procedure_code(
    db: AsyncSession, *, clinic_id: uuid.UUID, full_text: str
) -> str | None:
    """Mismo criterio que `_find_appointment_type`: compara contra el CODIGO
    del catalogo de procedimientos (`ProcedureCatalog`, Fase 7), no el nombre
    para mostrar -- el codigo es un identificador corto y limpio (CLAUDE.md
    sec. 6), el nombre puede traer precio/puntuacion que nadie diria en voz."""
    text_words = set(full_text.split())
    items = await treatment_service.list_procedure_catalog(db, clinic_id=clinic_id)
    for item in items:
        if not item.is_active:
            continue
        code_words = set(_normalize_name(item.code.replace("_", " ")).split())
        if code_words and code_words <= text_words:
            return item.code
    return None


async def _handle_procedimiento(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    context: ScreenContext,
    active_encounter_id: str | None,
    slots: dict[str, str],
    action_type: Literal["add_planned_procedure", "add_performed_procedure"],
    verb: str,
) -> DialogueResult:
    """Comun a `procedimiento_planeado`/`procedimiento_realizado`: ambos solo
    difieren en el `action_type` que le pasan a `app/ai/applier.py` -- que ya
    sabe crear el plan/fase borrador si no existe uno (`add_planned_procedure`)
    o registrar lo realizado directo (`add_performed_procedure`, genera un
    `Charge` "SUGERIDO", Fase 7); reusarlo evita duplicar esa logica aqui."""
    if not context.patient_id:
        return DialogueResult(say="Primero abre el expediente de un paciente.")
    if not active_encounter_id:
        return DialogueResult(say="Primero inicia la consulta.")

    full_text = slots.get("full_text", "")
    procedure_code = await _find_procedure_code(db, clinic_id=clinic_id, full_text=full_text)
    if procedure_code is None:
        return DialogueResult(say="No reconozco ese procedimiento del catálogo.")

    tooth_raw = slots.get("tooth_fdi", "")
    tooth_fdi = int(tooth_raw) if tooth_raw else None
    surfaces = [s for s in slots.get("surfaces", "").split(",") if s]
    patient_id = context.patient_id
    encounter_id = active_encounter_id
    tooth_phrase = f" en la {tooth_fdi}" if tooth_fdi else ""
    preview = f"{verb} {procedure_code}{tooth_phrase}."

    async def _execute() -> DialogueResult:
        suggestion = AiSuggestion(
            clinic_id=clinic_id,
            patient_id=uuid.UUID(patient_id),
            encounter_id=uuid.UUID(encounter_id),
            batch_id=uuid.uuid4(),
            action_type=action_type,
            payload={
                "tooth_fdi": tooth_fdi,
                "surfaces": surfaces,
                "procedure_code": procedure_code,
                "notes": None,
            },
            status="PENDING",
            model_name="dentia_fast_path",
            model_digest=None,
            transcript_excerpt=preview[:500],
            created_by=user_id,
        )
        db.add(suggestion)
        await db.flush()
        await db.commit()

        _, entity_id = await ai_applier.accept_suggestion(
            db,
            clinic_id=clinic_id,
            suggestion_id=suggestion.id,
            edits=None,
            actor_id=user_id,
            confirmation_mode="voice_explicit",
        )
        assert entity_id is not None
        return DialogueResult(say="Listo, registrado.")

    return DialogueResult(
        say=preview,
        pending=PendingCapture(
            level=3, say_preview=preview, confirm_prompt="¿Confirmas?", execute=_execute
        ),
    )


async def _handle_procedimiento_planeado(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    context: ScreenContext,
    active_encounter_id: str | None,
    slots: dict[str, str],
) -> DialogueResult:
    return await _handle_procedimiento(
        db,
        clinic_id=clinic_id,
        user_id=user_id,
        context=context,
        active_encounter_id=active_encounter_id,
        slots=slots,
        action_type="add_planned_procedure",
        verb="Agrego al plan",
    )


async def _handle_procedimiento_realizado(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    context: ScreenContext,
    active_encounter_id: str | None,
    slots: dict[str, str],
) -> DialogueResult:
    return await _handle_procedimiento(
        db,
        clinic_id=clinic_id,
        user_id=user_id,
        context=context,
        active_encounter_id=active_encounter_id,
        slots=slots,
        action_type="add_performed_procedure",
        verb="Registro como realizado",
    )


async def _handle_deshacer(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, undo_top: UndoEntry | None
) -> DialogueResult:
    if undo_top is None:
        return DialogueResult(say="No hay nada que deshacer.")

    if undo_top.action_type == "add_tooth_finding":
        await odontogram_service.retire_finding(
            db,
            clinic_id=clinic_id,
            patient_id=uuid.UUID(undo_top.patient_id),
            finding_id=uuid.UUID(undo_top.entity_id),
            actor_id=user_id,
        )
        return DialogueResult(say=f"Quité {undo_top.say}.", pop_undo=True)

    return DialogueResult(say="Eso ya no se puede deshacer.", pop_undo=True)


# --------------------------------------------------------------- 13.4 agenda


def _normalize_name(text: str) -> str:
    """Mismo criterio que `nlu_fast._normalize`: sin acentos, en minusculas y
    sin puntuacion -- los nombres del catalogo traen cosas como "Consulta /
    valoracion" o "Restauracion (resina/amalgama)" que, sin esto, nunca
    calzarian palabra por palabra contra el texto ya normalizado de la orden."""
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^a-z0-9 ]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _speak_appointment_error(exc: AppError) -> str:
    if exc.code == "APPOINTMENT_CONFLICT":
        return "Ese horario ya está ocupado. Dime otra hora."
    if exc.code == "INVALID_TRANSITION":
        return "Esa cita ya no se puede cambiar así."
    if exc.code == "INVALID_RANGE":
        return "Esa hora no es válida."
    return "No pude hacer ese cambio en la agenda."


async def _find_single_patient(
    db: AsyncSession, *, clinic_id: uuid.UUID, query: str
) -> tuple[Patient | None, str | None]:
    """Mismo criterio de busqueda/desambiguacion que `_handle_abrir_expediente`
    -- separado aqui porque las 4 intenciones de agenda lo necesitan igual."""
    if not query:
        return None, "¿De qué paciente hablamos?"
    matches = await patients_service.search_patients(db, clinic_id=clinic_id, query=query)
    if not matches:
        return None, f"No encontré a nadie llamado {query}."
    if len(matches) > 1:
        names = ", ".join(p.full_name for p in matches[:_MAX_DISAMBIGUATION_NAMES])
        return None, f"Hay varios: {names}. ¿Cuál?"
    return matches[0], None


async def _find_provider_by_name(
    db: AsyncSession, *, clinic_id: uuid.UUID, query: str
) -> tuple[uuid.UUID, str] | None:
    """La lista de profesionales de una sucursal es corta (a diferencia de
    pacientes): un emparejamiento simple por palabras en comun basta, no hace
    falta busqueda tolerante (pg_trgm)."""
    if not query:
        return None
    query_words = set(query.split())
    providers = await agenda_service.list_providers(db, clinic_id=clinic_id)
    for provider, full_name in providers:
        if query_words & set(_normalize_name(full_name).split()):
            return provider.id, full_name
    return None


async def _find_appointment_type(
    db: AsyncSession, *, clinic_id: uuid.UUID, full_text: str
) -> str | None:
    """Escanea toda la orden buscando un tipo de cita del catalogo de la
    sucursal (B1) -- igual que `_match_finding_code` escanea buscando un
    hallazgo conocido. Compara contra el CODIGO del catalogo (p.ej.
    "ortodoncia_control"), no el nombre para mostrar: los nombres traen
    puntuacion ("Consulta / valoracion", "Restauracion (resina/amalgama)") y
    varias palabras que nadie diria completas en voz; el codigo es un
    identificador corto y limpio (CLAUDE.md sec. 6)."""
    text_words = set(full_text.split())
    items = await catalogs_service.list_items(
        db, clinic_id=clinic_id, catalog_type="appointment_type"
    )
    for item in items:
        name_words = set(_normalize_name(item.code.replace("_", " ")).split())
        if name_words and name_words <= text_words:
            return item.code
    return None


async def _find_todays_appointment(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_query: str, time_text: str
) -> tuple[dict[str, object] | None, str | None]:
    tz = await _clinic_zoneinfo(db, clinic_id=clinic_id)
    today = datetime.now(tz).date()
    starts_from, starts_to = _local_day_bounds_utc(tz, today)
    appointments = await agenda_service.list_appointments(
        db, clinic_id=clinic_id, starts_from=starts_from, starts_to=starts_to
    )
    active = [
        a
        for a in appointments
        if a["status"] not in _RESOLVED_APPOINTMENT_STATUSES and a["status"] != "TERMINADA"
    ]

    if time_text:
        target_time = datetime_parse.extract_time_of_day(time_text)
        if target_time is None:
            return None, "¿A qué hora es la cita?"
        matches = [
            a
            for a in active
            if isinstance(a["starts_at"], datetime) and a["starts_at"].time() == target_time
        ]
    else:
        if not patient_query:
            return None, "¿De qué paciente hablamos?"
        query_words = set(patient_query.split())
        matches = [
            a
            for a in active
            if query_words & set(_normalize_name(str(a["patient_full_name"])).split())
        ]

    if not matches:
        return None, "No encontré esa cita hoy."
    if len(matches) > 1:
        return None, "Hay varias citas que coinciden. ¿Cuál?"
    return matches[0], None


async def _find_upcoming_appointment_for_patient(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_query: str, days_ahead: int = 14
) -> tuple[dict[str, object] | None, str | None]:
    if not patient_query:
        return None, "¿De qué paciente hablamos?"
    tz = await _clinic_zoneinfo(db, clinic_id=clinic_id)
    starts_from, _ = _local_day_bounds_utc(tz, datetime.now(tz).date())
    starts_to = starts_from + timedelta(days=days_ahead)
    appointments = await agenda_service.list_appointments(
        db, clinic_id=clinic_id, starts_from=starts_from, starts_to=starts_to
    )
    active = [
        a
        for a in appointments
        if a["status"] not in _RESOLVED_APPOINTMENT_STATUSES and a["status"] != "TERMINADA"
    ]
    query_words = set(patient_query.split())
    matches = [
        a for a in active if query_words & set(_normalize_name(str(a["patient_full_name"])).split())
    ]
    if not matches:
        return None, f"No encontré una cita próxima de {patient_query}."
    if len(matches) > 1:
        return None, f"Hay varias citas de {patient_query}. ¿Cuál?"
    return matches[0], None


async def _handle_agendar_cita(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, slots: dict[str, str]
) -> DialogueResult:
    patient, error_say = await _find_single_patient(
        db, clinic_id=clinic_id, query=slots.get("patient_query", "")
    )
    if patient is None:
        assert error_say is not None
        return DialogueResult(say=error_say)

    tz = await _clinic_zoneinfo(db, clinic_id=clinic_id)
    target_date = datetime_parse.extract_relative_date(
        slots.get("date_text", ""), today=datetime.now(tz).date()
    )
    if target_date is None:
        return DialogueResult(say="¿Qué día? Puedo entender hoy, mañana o un día de la semana.")

    provider_match = await _find_provider_by_name(
        db, clinic_id=clinic_id, query=slots.get("provider_query", "")
    )
    if provider_match is None:
        return DialogueResult(say="¿Con qué profesional?")
    provider_id, provider_name = provider_match

    appointment_type = await _find_appointment_type(
        db, clinic_id=clinic_id, full_text=slots.get("full_text", "")
    )
    if appointment_type is None:
        return DialogueResult(say="¿Qué tipo de cita? Por ejemplo, consulta o limpieza.")

    time_text = slots.get("time_text", "")
    target_time = datetime_parse.extract_time_of_day(time_text)
    if target_time is None:
        if time_text:
            return DialogueResult(say="¿A qué hora?")
        # Huecos libres reales (sec. 4.5 del diseno, resto de 13.4): en vez de
        # solo pedir la hora, Dentia propone horarios reales de ese profesional
        # ese dia -- el usuario repite la orden completa con la hora elegida
        # (mismo criterio que el resto de la ruta rapida: sin continuidad de
        # slots entre turnos, ver docs/PENDIENTES_CLINICOS.md).
        free_slots = await agenda_service.find_free_slots(
            db,
            clinic_id=clinic_id,
            provider_id=provider_id,
            day=target_date,
            duration_minutes=agenda_rules.DEFAULT_APPOINTMENT_DURATION_MINUTES,
        )
        if not free_slots:
            return DialogueResult(
                say=f"{provider_name} no tiene horario libre ese día. ¿Qué otro día?"
            )
        hours = _join_es([s.strftime("%H:%M") for s in free_slots])
        return DialogueResult(
            say=(
                f"El {datetime_parse.format_date_es(target_date)} {provider_name} tiene libre "
                f"a las {hours}. ¿Cuál? Dime de nuevo la cita con la hora."
            )
        )

    starts_at = datetime.combine(target_date, target_time, tzinfo=UTC)
    preview = (
        f"Agendo a {patient.full_name} el {datetime_parse.format_date_es(target_date)} a las "
        f"{target_time.strftime('%H:%M')} con {provider_name}."
    )
    patient_id = patient.id
    patient_full_name = patient.full_name

    async def _execute() -> DialogueResult:
        provider = await agenda_service.get_provider_in_clinic(
            db, clinic_id=clinic_id, provider_id=provider_id
        )
        try:
            await agenda_service.create_appointment(
                db,
                clinic_id=clinic_id,
                data=AppointmentCreateRequest(
                    patient_id=patient_id,
                    provider_id=provider_id,
                    resource_id=provider.default_resource_id,
                    appointment_type=appointment_type,
                    starts_at=starts_at,
                ),
                actor_id=user_id,
            )
        except AppError as exc:
            return DialogueResult(say=_speak_appointment_error(exc))
        return DialogueResult(say=f"Listo, cita agendada para {patient_full_name}.")

    return DialogueResult(
        say=preview,
        pending=PendingCapture(
            level=3, say_preview=preview, confirm_prompt="¿Confirmas?", execute=_execute
        ),
        patient_ref=(str(patient_id), patient_full_name),
    )


async def _handle_reprogramar_cita(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, slots: dict[str, str]
) -> DialogueResult:
    appointment, error_say = await _find_upcoming_appointment_for_patient(
        db, clinic_id=clinic_id, patient_query=slots.get("patient_query", "")
    )
    if appointment is None:
        assert error_say is not None
        return DialogueResult(say=error_say)

    tz = await _clinic_zoneinfo(db, clinic_id=clinic_id)
    target_date = datetime_parse.extract_relative_date(
        slots.get("date_text", ""), today=datetime.now(tz).date()
    )
    if target_date is None:
        return DialogueResult(say="¿A qué día la muevo?")

    old_starts_at = appointment["starts_at"]
    assert isinstance(old_starts_at, datetime)
    time_text = slots.get("time_text", "")
    if time_text:
        parsed_time = datetime_parse.extract_time_of_day(time_text)
        if parsed_time is None:
            return DialogueResult(say="¿A qué hora?")
        target_time = parsed_time
    else:
        target_time = old_starts_at.time()

    new_starts_at = datetime.combine(target_date, target_time, tzinfo=UTC)
    patient_full_name = str(appointment["patient_full_name"])
    preview = (
        f"Muevo la cita de {patient_full_name} al {datetime_parse.format_date_es(target_date)} "
        f"a las {target_time.strftime('%H:%M')}."
    )
    appointment_id = appointment["id"]
    assert isinstance(appointment_id, uuid.UUID)

    async def _execute() -> DialogueResult:
        try:
            await agenda_service.reschedule_appointment(
                db,
                clinic_id=clinic_id,
                appointment_id=appointment_id,
                data=RescheduleRequest(starts_at=new_starts_at),
                actor_id=user_id,
            )
        except AppError as exc:
            return DialogueResult(say=_speak_appointment_error(exc))
        return DialogueResult(say="Listo, cita reprogramada.")

    return DialogueResult(
        say=preview,
        pending=PendingCapture(
            level=3, say_preview=preview, confirm_prompt="¿Confirmas?", execute=_execute
        ),
        patient_ref=(str(appointment["patient_id"]), patient_full_name),
    )


async def _handle_confirmar_cita(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, slots: dict[str, str]
) -> DialogueResult:
    appointment, error_say = await _find_todays_appointment(
        db,
        clinic_id=clinic_id,
        patient_query=slots.get("patient_query", ""),
        time_text=slots.get("time_text", ""),
    )
    if appointment is None:
        assert error_say is not None
        return DialogueResult(say=error_say)

    appointment_id = appointment["id"]
    assert isinstance(appointment_id, uuid.UUID)
    preview = f"Confirmo la cita de {appointment['patient_full_name']}."

    async def _execute() -> DialogueResult:
        try:
            await agenda_service.change_status(
                db,
                clinic_id=clinic_id,
                appointment_id=appointment_id,
                data=StatusChangeRequest(status="CONFIRMADA"),
                actor_id=user_id,
            )
        except AppError as exc:
            return DialogueResult(say=_speak_appointment_error(exc))
        return DialogueResult(say="")

    return DialogueResult(
        say=preview,
        pending=PendingCapture(level=2, say_preview=preview, confirm_prompt=None, execute=_execute),
        patient_ref=(str(appointment["patient_id"]), str(appointment["patient_full_name"])),
    )


async def _handle_registrar_llegada(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, slots: dict[str, str]
) -> DialogueResult:
    appointment, error_say = await _find_todays_appointment(
        db, clinic_id=clinic_id, patient_query=slots.get("patient_query", ""), time_text=""
    )
    if appointment is None:
        assert error_say is not None
        return DialogueResult(say=error_say)

    appointment_id = appointment["id"]
    assert isinstance(appointment_id, uuid.UUID)
    preview = f"Registro la llegada de {appointment['patient_full_name']}."

    async def _execute() -> DialogueResult:
        try:
            await agenda_service.change_status(
                db,
                clinic_id=clinic_id,
                appointment_id=appointment_id,
                data=StatusChangeRequest(status="EN_SALA"),
                actor_id=user_id,
            )
        except AppError as exc:
            return DialogueResult(say=_speak_appointment_error(exc))
        return DialogueResult(say="")

    return DialogueResult(
        say=preview,
        pending=PendingCapture(level=2, say_preview=preview, confirm_prompt=None, execute=_execute),
        patient_ref=(str(appointment["patient_id"]), str(appointment["patient_full_name"])),
    )


# ----------------------------------- 13.4 (resto): huecos, cancelar/no_show,
# ----------------------------------- lista de espera, alta rapida de paciente


async def _handle_huecos_libres(
    db: AsyncSession, *, clinic_id: uuid.UUID, slots: dict[str, str]
) -> DialogueResult:
    """`huecos_libres` como intencion propia (pendiente explicito de la
    seccion anterior de 13.4): consultar disponibilidad SIN agendar -- nivel 0,
    respuesta directa, igual que `citas_hoy`."""
    provider_match = await _find_provider_by_name(
        db, clinic_id=clinic_id, query=slots.get("provider_query", "")
    )
    if provider_match is None:
        return DialogueResult(say="¿Con qué profesional?")
    provider_id, provider_name = provider_match

    date_text = slots.get("date_text", "")
    tz = await _clinic_zoneinfo(db, clinic_id=clinic_id)
    today = datetime.now(tz).date()
    if "semana" in date_text:
        start_date, days_to_check = today, 7
    elif date_text:
        parsed = datetime_parse.extract_relative_date(date_text, today=today)
        if parsed is None:
            return DialogueResult(say="¿Qué día? Puedo entender hoy, mañana o un día de la semana.")
        start_date, days_to_check = parsed, 1
    else:
        start_date, days_to_check = today, 7

    for offset in range(days_to_check):
        day = start_date + timedelta(days=offset)
        free_slots = await agenda_service.find_free_slots(
            db,
            clinic_id=clinic_id,
            provider_id=provider_id,
            day=day,
            duration_minutes=agenda_rules.DEFAULT_APPOINTMENT_DURATION_MINUTES,
        )
        if free_slots:
            hours = _join_es([s.strftime("%H:%M") for s in free_slots])
            day_label = datetime_parse.format_date_es(day)
            return DialogueResult(say=f"El {day_label} {provider_name} tiene libre a las {hours}.")
    return DialogueResult(say=f"No encontré horario libre con {provider_name} esos días.")


async def _handle_cancelar_cita(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, slots: dict[str, str]
) -> DialogueResult:
    reason = slots.get("reason", "")
    if not reason:
        return DialogueResult(
            say='Dime el motivo. Por ejemplo: "cancela la cita de las 12, motivo enfermedad".'
        )

    appointment, error_say = await _find_todays_appointment(
        db,
        clinic_id=clinic_id,
        patient_query=slots.get("patient_query", ""),
        time_text=slots.get("time_text", ""),
    )
    if appointment is None:
        assert error_say is not None
        return DialogueResult(say=error_say)

    appointment_id = appointment["id"]
    assert isinstance(appointment_id, uuid.UUID)
    patient_full_name = str(appointment["patient_full_name"])
    preview = f"Cancelo la cita de {patient_full_name}. Motivo: {reason}."

    async def _execute() -> DialogueResult:
        try:
            await agenda_service.change_status(
                db,
                clinic_id=clinic_id,
                appointment_id=appointment_id,
                data=StatusChangeRequest(status="CANCELADA", reason=reason),
                actor_id=user_id,
            )
        except AppError as exc:
            return DialogueResult(say=_speak_appointment_error(exc))
        return DialogueResult(say="Listo, cita cancelada.")

    return DialogueResult(
        say=preview,
        pending=PendingCapture(
            level=3, say_preview=preview, confirm_prompt="¿Confirmas?", execute=_execute
        ),
        patient_ref=(str(appointment["patient_id"]), patient_full_name),
    )


_NO_SHOW_DEFAULT_REASON = "No se presentó"


async def _handle_no_show(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, slots: dict[str, str]
) -> DialogueResult:
    appointment, error_say = await _find_todays_appointment(
        db, clinic_id=clinic_id, patient_query=slots.get("patient_query", ""), time_text=""
    )
    if appointment is None:
        assert error_say is not None
        return DialogueResult(say=error_say)

    appointment_id = appointment["id"]
    assert isinstance(appointment_id, uuid.UUID)
    patient_full_name = str(appointment["patient_full_name"])
    preview = f"Marco que {patient_full_name} no se presentó a su cita."

    async def _execute() -> DialogueResult:
        try:
            await agenda_service.change_status(
                db,
                clinic_id=clinic_id,
                appointment_id=appointment_id,
                data=StatusChangeRequest(status="NO_SHOW", reason=_NO_SHOW_DEFAULT_REASON),
                actor_id=user_id,
            )
        except AppError as exc:
            return DialogueResult(say=_speak_appointment_error(exc))
        return DialogueResult(say="Listo, registrado.")

    return DialogueResult(
        say=preview,
        pending=PendingCapture(
            level=3, say_preview=preview, confirm_prompt="¿Confirmas?", execute=_execute
        ),
        patient_ref=(str(appointment["patient_id"]), patient_full_name),
    )


async def _handle_lista_espera(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    slots: dict[str, str],
    last_patient: tuple[str, str] | None,
) -> DialogueResult:
    patient_query = slots.get("patient_query", "")
    if patient_query:
        patient, error_say = await _find_single_patient(
            db, clinic_id=clinic_id, query=patient_query
        )
        if patient is None:
            assert error_say is not None
            return DialogueResult(say=error_say)
        patient_id, patient_full_name = str(patient.id), patient.full_name
    elif last_patient is not None:
        patient_id, patient_full_name = last_patient
    else:
        return DialogueResult(say="¿De qué paciente hablamos?")

    preview = f"Agrego a {patient_full_name} a la lista de espera."

    async def _execute() -> DialogueResult:
        await agenda_service.create_waitlist_entry(
            db,
            clinic_id=clinic_id,
            data=WaitlistCreateRequest(patient_id=uuid.UUID(patient_id)),
            actor_id=user_id,
        )
        return DialogueResult(say="Listo, en la lista de espera.")

    return DialogueResult(
        say=preview,
        pending=PendingCapture(level=2, say_preview=preview, confirm_prompt=None, execute=_execute),
        patient_ref=(patient_id, patient_full_name),
    )


def _split_patient_name(spoken_name: str) -> tuple[str, str]:
    """Heuristica igual de deliberadamente simple que `datetime_parse.py`: la
    ULTIMA palabra es el apellido paterno y el resto el/los nombre(s) -- cubre
    el caso frecuente de dictar "Nombre Apellido" (ver limitacion de apellido
    materno/compuesto en docs/PENDIENTES_CLINICOS.md)."""
    words = spoken_name.split()
    if len(words) == 1:
        return words[0].title(), words[0].title()
    return " ".join(w.title() for w in words[:-1]), words[-1].title()


def _handle_alta_rapida_paciente(slots: dict[str, str]) -> DialogueResult:
    """ "registra paciente nuevo..." (C2 del doc 06): abre el formulario de alta
    prellenado -- nivel 1, sin confirmacion de voz, igual que `ir_a`/
    `abrir_expediente`. El alta se termina en pantalla, con la deteccion de
    duplicados obligatoria que ya hace esa pantalla (CLAUDE.md regla 5/9: la
    IA nunca crea el paciente directamente)."""
    spoken_name = slots.get("patient_name", "")
    first_name, last_name_paternal = _split_patient_name(spoken_name)
    payload = {"first_name": first_name, "last_name_paternal": last_name_paternal}
    phone = slots.get("phone", "")
    if phone:
        payload["phone"] = phone
    query = urllib.parse.urlencode(payload)
    full_name = f"{first_name} {last_name_paternal}"
    return DialogueResult(
        say=f"Abriendo alta de paciente para {full_name}. Termínalo en pantalla.",
        ui_actions=[UiAction("navigate", {"path": f"/pacientes/nuevo?{query}"})],
    )


# ------------------------------------------------------- 13.5 ruta LLM/dictado

_ACTION_LABELS: dict[str, str] = {
    "set_chief_complaint": "el motivo de consulta",
    "add_allergy": "una alergia",
    "add_medication": "un medicamento",
    "add_medical_history": "un antecedente",
    "add_vital_signs": "signos vitales",
    "add_tooth_finding": "un hallazgo del odontograma",
    "add_planned_procedure": "un procedimiento planeado",
    "add_performed_procedure": "un procedimiento realizado",
    "add_diagnosis": "un diagnóstico",
    "append_note": "texto en la nota",
    "schedule_followup": "un control sugerido",
}


def _describe_action(action_type: str, payload: dict[str, object]) -> str:
    """Vista previa hablada de una accion de la Fase 8 (11 tipos, sec. 4 de
    docs/03_AGENTE_IA_VOZ.md) -- deliberadamente generica: el detalle completo
    ya queda en el panel de Propuestas para revisar con calma; la voz solo da
    el resumen suficiente para decidir "si" o "no"."""
    label = _ACTION_LABELS.get(action_type, "una propuesta")
    detail = str(
        payload.get("text") or payload.get("name") or payload.get("substance") or ""
    ).strip()
    if detail:
        return f"Registro {label}: {detail}."
    return f"Registro {label}."


async def _try_llm_fallback(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    encounter_id: str,
    transcript: str,
) -> DialogueResult | None:
    """Ruta LLM (13.5, sec. 5 del diseno): solo para UNA orden suelta que la
    ruta rapida no reconocio -- reutiliza el mismo interprete de la Fase 8
    (texto -> Ollama -> `AiSuggestion` validada contra catalogos reales) en
    vez de un esquema de voz aparte. Nivel 3 SIEMPRE (sec. 3: "baja certeza
    sube de nivel" -- una orden que vino de la ruta libre nunca tiene la
    confianza de un patron reconocido, no se aplica con cuenta regresiva
    implicita). Devuelve None si no hay exactamente una accion reconocida
    (nada, o mas de una -- eso es dictado, `modo_dictado`) o si Ollama no esta
    disponible, para que el llamador caiga en "no te entendi" sin mas drama."""
    stripped = nlu_fast.strip_wake_word(transcript)
    if not stripped:
        return None
    try:
        suggestions, unrecognized = await ai_interpreter.interpret(
            db,
            clinic_id=clinic_id,
            encounter_id=uuid.UUID(encounter_id),
            transcript=stripped,
            actor_id=user_id,
            keep_alive=get_settings().ollama_keep_alive,
        )
    except AppError:
        return None
    if len(suggestions) != 1 or unrecognized:
        return None

    suggestion = suggestions[0]
    suggestion_id = suggestion.id
    preview = _describe_action(suggestion.action_type, suggestion.payload)

    async def _execute() -> DialogueResult:
        await ai_applier.accept_suggestion(
            db,
            clinic_id=clinic_id,
            suggestion_id=suggestion_id,
            edits=None,
            actor_id=user_id,
            confirmation_mode="voice_explicit",
        )
        return DialogueResult(say="Listo.")

    return DialogueResult(
        say=preview,
        pending=PendingCapture(
            level=3, say_preview=preview, confirm_prompt="¿Confirmas?", execute=_execute
        ),
    )


def _format_llm_time(time_text: str | None) -> str:
    """El esquema de `agenda_llm.py` le pide al modelo solo el numero/hora
    ("10", "10:30"), sin el prefijo "a las" -- `datetime_parse.
    extract_time_of_day` siempre lo espera, igual que `nlu_fast._format_time_
    text` para la ruta rapida."""
    if not time_text:
        return ""
    normalized = time_text.strip().lower()
    return normalized if normalized.startswith("a las") else f"a las {normalized}"


async def _try_agenda_llm_fallback(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    transcript: str,
    last_patient: tuple[str, str] | None,
) -> DialogueResult | None:
    """Resto de 13.5 (pendiente explicito de la sec. 5.20): agenda por voz
    con frase libre, para cuando `nlu_fast` no reconoce las anclas de
    palabra clave de la ruta rapida (sec. C2 del doc 06). El esquema de
    `agenda_llm.py` le pide al modelo que devuelva fecha/hora en el MISMO
    formato de texto que ya entiende `datetime_parse.py` -- asi el resultado
    se convierte en un `dict` de slots identico al de `nlu_fast.FastMatch` y
    se reusan los MISMOS manejadores de la ruta rapida (preview, nivel de
    confirmacion, `execute()`), sin duplicar logica de agenda."""
    stripped = nlu_fast.strip_wake_word(transcript)
    if not stripped:
        return None

    result = await agenda_llm.interpret_agenda_order(stripped)
    if result is None or result.action is None:
        return None
    action = result.action

    if isinstance(action, agenda_llm.AgendarCitaAction):
        appointment_hint = _normalize_name(action.appointment_type_hint or "")
        slots = {
            "patient_query": _normalize_name(action.patient_name),
            "date_text": action.date_text or "",
            "time_text": _format_llm_time(action.time_text),
            "provider_query": _normalize_name(action.provider_name or ""),
            "full_text": f"{appointment_hint} {_normalize_name(stripped)}".strip(),
        }
        return await _handle_agendar_cita(db, clinic_id=clinic_id, user_id=user_id, slots=slots)
    if isinstance(action, agenda_llm.ReprogramarCitaAction):
        slots = {
            "patient_query": _normalize_name(action.patient_name),
            "date_text": action.date_text,
            "time_text": _format_llm_time(action.time_text),
        }
        return await _handle_reprogramar_cita(db, clinic_id=clinic_id, user_id=user_id, slots=slots)
    if isinstance(action, agenda_llm.ConfirmarCitaAction):
        slots = {
            "patient_query": _normalize_name(action.patient_name or ""),
            "time_text": _format_llm_time(action.time_text),
        }
        return await _handle_confirmar_cita(db, clinic_id=clinic_id, user_id=user_id, slots=slots)
    if isinstance(action, agenda_llm.RegistrarLlegadaAction):
        slots = {"patient_query": _normalize_name(action.patient_name)}
        return await _handle_registrar_llegada(
            db, clinic_id=clinic_id, user_id=user_id, slots=slots
        )
    if isinstance(action, agenda_llm.CancelarCitaAction):
        slots = {
            "patient_query": _normalize_name(action.patient_name or ""),
            "time_text": _format_llm_time(action.time_text),
            "reason": action.reason,
        }
        return await _handle_cancelar_cita(db, clinic_id=clinic_id, user_id=user_id, slots=slots)
    if isinstance(action, agenda_llm.NoShowAction):
        slots = {"patient_query": _normalize_name(action.patient_name)}
        return await _handle_no_show(db, clinic_id=clinic_id, user_id=user_id, slots=slots)
    if isinstance(action, agenda_llm.ListaEsperaAction):
        slots = {"patient_query": _normalize_name(action.patient_name or "")}
        return await _handle_lista_espera(
            db,
            clinic_id=clinic_id,
            user_id=user_id,
            slots=slots,
            last_patient=last_patient,
        )
    if isinstance(action, agenda_llm.HuecosLibresAction):
        slots = {
            "provider_query": _normalize_name(action.provider_name),
            "date_text": action.date_text or "",
        }
        return await _handle_huecos_libres(db, clinic_id=clinic_id, slots=slots)
    return None


async def finish_dictation(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    encounter_id: str,
    transcript: str,
) -> DialogueResult:
    """Fin de "Dentia, dictado" (sec. 4.2 del diseno): el texto acumulado
    durante todo el modo dictado (no solo la ultima frase) va al mismo
    interprete de la Fase 8 -- puede generar varias `AiSuggestion` de una vez,
    a diferencia de la ruta LLM de una sola orden (`_try_llm_fallback`).
    Aceptar todas es nivel 3 explicito; "no" las deja PENDING para revisar en
    el panel de Propuestas en vez de perderlas."""
    if not transcript.strip():
        return DialogueResult(say="No dictaste nada.")

    suggestions, _unrecognized = await ai_interpreter.interpret(
        db,
        clinic_id=clinic_id,
        encounter_id=uuid.UUID(encounter_id),
        transcript=transcript,
        actor_id=user_id,
        keep_alive=get_settings().ollama_keep_alive,
    )
    if not suggestions:
        return DialogueResult(say="No entendí ninguna propuesta de ese dictado.")

    count = len(suggestions)
    plural = "propuestas" if count != 1 else "propuesta"
    preview = f"Tengo {count} {plural}. ¿Las acepto todas?"
    suggestion_ids = [s.id for s in suggestions]

    async def _execute() -> DialogueResult:
        for suggestion_id in suggestion_ids:
            await ai_applier.accept_suggestion(
                db,
                clinic_id=clinic_id,
                suggestion_id=suggestion_id,
                edits=None,
                actor_id=user_id,
                confirmation_mode="voice_explicit",
            )
        return DialogueResult(say="Listo, aplicadas.")

    return DialogueResult(
        say=preview,
        pending=PendingCapture(
            level=3,
            say_preview=preview,
            confirm_prompt=None,
            execute=_execute,
            cancel_say="Quedan pendientes en el panel de propuestas.",
        ),
    )
