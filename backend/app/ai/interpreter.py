"""Orquesta un dictado: arma el prompt, llama a Ollama, valida la respuesta contra los
catalogos reales de la clinica y crea AiSuggestion en PENDING (docs/03_AGENTE_IA_VOZ.md
sec. 2 y 3). Regla 9 de CLAUDE.md: esta funcion NUNCA escribe en una tabla clinica, solo
en ai_suggestions -- aplicar una sugerencia es responsabilidad exclusiva de applier.py,
despues de que el odontologo la acepta."""

import json
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import dental_parser, ollama_client
from app.ai.actions import ACTION_MODELS_BY_TYPE, AiInterpretResult
from app.ai.models import AiClinicSettings, AiSuggestion
from app.ai.ollama_client import OllamaUnavailableError
from app.ai.rules import PROHIBITED_ACTION_TYPES
from app.audit import service as audit_service
from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.diagnosis.rules import DIAGNOSIS_CODES
from app.modules.encounters.models import Encounter
from app.modules.odontogram import rules as odontogram_rules
from app.modules.odontogram.finding_catalog import FINDING_CODES
from app.modules.patients.models import Patient
from app.modules.records.rules import HISTORY_CATEGORIES
from app.modules.treatment import service as treatment_service

_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_es.md"

_TOOTH_ACTIONS = {
    "add_tooth_finding",
    "add_planned_procedure",
    "add_performed_procedure",
    "add_diagnosis",
}
_PROCEDURE_ACTIONS = {"add_planned_procedure", "add_performed_procedure"}


class UnrecognizedEntry:
    def __init__(self, text: str, reason: str) -> None:
        self.text = text
        self.reason = reason


async def _get_patient_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Paciente no encontrado", status_code=404)
    return patient


async def _get_encounter_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, encounter_id: uuid.UUID
) -> Encounter:
    encounter = await db.get(Encounter, encounter_id)
    if encounter is None or encounter.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Atencion no encontrada", status_code=404)
    return encounter


async def effective_model(db: AsyncSession, *, clinic_id: uuid.UUID) -> str:
    settings = get_settings()
    clinic_settings = await db.get(AiClinicSettings, clinic_id)
    if clinic_settings is not None and clinic_settings.ollama_model:
        return clinic_settings.ollama_model
    return settings.ollama_model


def _denticion_label(date_of_birth: date) -> str:
    age_years = (date.today() - date_of_birth).days // 365
    return "mixta probable (menor de 13 anos)" if age_years < 13 else "permanente"


def _build_prompts(
    *, transcript: str, patient_name: str, denticion: str, procedure_codes: list[str]
) -> tuple[str, str]:
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    system_prompt = template.format(
        finding_codes=", ".join(FINDING_CODES),
        procedure_codes=", ".join(procedure_codes) or "(sin procedimientos en el catalogo)",
        diagnosis_codes=", ".join(DIAGNOSIS_CODES),
        history_categories=", ".join(HISTORY_CATEGORIES),
        patient_name=patient_name,
        screen="atencion",
        denticion=denticion,
        parser_hints=dental_parser.build_hints(transcript),
    )
    return system_prompt, transcript


def _validate_against_real_catalogs(
    action_type: str, data: dict[str, Any], *, procedure_codes: set[str]
) -> str | None:
    """Reglas que un esquema Pydantic generico no puede expresar porque dependen de la
    BD de esta clinica (igual que en los servicios de dominio). Devuelve un motivo de
    rechazo, o None si la accion es valida."""
    if action_type in _TOOTH_ACTIONS:
        tooth_fdi = data.get("tooth_fdi")
        if tooth_fdi is not None:
            if not odontogram_rules.is_valid_tooth(tooth_fdi):
                return f"Pieza FDI invalida: {tooth_fdi}"
            for surface in data.get("surfaces") or []:
                if not odontogram_rules.is_valid_surface_for_tooth(tooth_fdi, surface):
                    return f"La superficie {surface} no es valida para la pieza {tooth_fdi}"
        elif action_type == "add_tooth_finding":
            return "Se necesita una pieza FDI para un hallazgo del odontograma"

    if action_type in _PROCEDURE_ACTIONS:
        code = data.get("procedure_code")
        if code not in procedure_codes:
            return f"El procedimiento '{code}' no esta en el catalogo de esta clinica"

    return None


async def interpret(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    encounter_id: uuid.UUID,
    transcript: str,
    actor_id: uuid.UUID,
    keep_alive: float | str | None = None,
) -> tuple[list[AiSuggestion], list[UnrecognizedEntry]]:
    encounter = await _get_encounter_in_clinic(db, clinic_id=clinic_id, encounter_id=encounter_id)
    patient_id = encounter.patient_id
    patient = await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)

    catalog_items = await treatment_service.list_procedure_catalog(db, clinic_id=clinic_id)
    procedure_codes = {item.code for item in catalog_items if item.is_active}

    model = await effective_model(db, clinic_id=clinic_id)
    system_prompt, user_prompt = _build_prompts(
        transcript=transcript,
        patient_name=patient.full_name,
        denticion=_denticion_label(patient.date_of_birth),
        procedure_codes=sorted(procedure_codes),
    )

    try:
        # `keep_alive` solo lo pasa la ruta de voz (Fase 13, 13.5): el
        # dictado REST normal de esta misma Fase 8 lo deja en None (deja a
        # Ollama con su idle timeout por defecto).
        response = await ollama_client.chat(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=AiInterpretResult.model_json_schema(),
            keep_alive=keep_alive,
        )
    except OllamaUnavailableError as exc:
        raise AppError(
            "AI_UNAVAILABLE",
            "El asistente de IA no esta disponible (Ollama no responde)",
            status_code=503,
        ) from exc

    content = response.get("message", {}).get("content", "{}")
    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        raw = {"actions": [], "unrecognized": []}

    unrecognized: list[UnrecognizedEntry] = [
        UnrecognizedEntry(text=item.get("text", ""), reason=item.get("reason", ""))
        for item in raw.get("unrecognized", [])
        if isinstance(item, dict)
    ]

    batch_id = uuid.uuid4()
    model_digest = await ollama_client.model_digest(model)
    excerpt = transcript[:500]
    created: list[AiSuggestion] = []

    for raw_action in raw.get("actions", []):
        if not isinstance(raw_action, dict):
            continue
        action_type = raw_action.get("type")

        if action_type in PROHIBITED_ACTION_TYPES:
            unrecognized.append(
                UnrecognizedEntry(
                    text=str(raw_action),
                    reason=f"Accion prohibida descartada: {action_type}",
                )
            )
            await audit_service.log(
                db,
                action="ai.prohibited_action_discarded",
                actor_user_id=actor_id,
                clinic_id=clinic_id,
                entity_type="ai_suggestion",
                entity_id=None,
                details={"action_type": action_type, "raw": raw_action},
            )
            continue

        model_cls = ACTION_MODELS_BY_TYPE.get(action_type) if isinstance(action_type, str) else None
        if model_cls is None or not isinstance(action_type, str):
            unrecognized.append(
                UnrecognizedEntry(
                    text=str(raw_action), reason=f"Tipo de accion desconocido: {action_type}"
                )
            )
            continue

        try:
            validated = model_cls.model_validate(raw_action)
        except ValidationError as exc:
            unrecognized.append(UnrecognizedEntry(text=str(raw_action), reason=str(exc)))
            continue

        data = validated.model_dump(mode="json")
        rejection = _validate_against_real_catalogs(
            action_type, data, procedure_codes=procedure_codes
        )
        if rejection is not None:
            unrecognized.append(UnrecognizedEntry(text=str(raw_action), reason=rejection))
            continue

        data.pop("type", None)
        suggestion = AiSuggestion(
            clinic_id=clinic_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            batch_id=batch_id,
            action_type=action_type,
            payload=data,
            status="PENDING",
            model_name=model,
            model_digest=model_digest,
            transcript_excerpt=excerpt,
            created_by=actor_id,
        )
        db.add(suggestion)
        created.append(suggestion)

    await db.flush()
    await audit_service.log(
        db,
        action="ai.interpreted",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="encounter",
        entity_id=str(encounter_id),
        details={
            "model": model,
            "actions_created": len(created),
            "unrecognized": len(unrecognized),
            "transcript_excerpt": excerpt,
        },
    )
    await db.commit()
    return created, unrecognized
