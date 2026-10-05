"""Consultas y administracion del asistente (lista de sugerencias, estado de Ollama/
Whisper y preferencias por sucursal) -- la logica de aceptar/rechazar una sugerencia
vive en applier.py, no aqui, porque esta si es puramente de lectura y configuracion."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import ollama_client
from app.ai.interpreter import effective_model
from app.ai.models import AiClinicSettings, AiSuggestion
from app.ai.schemas import AiSettingsOut, AiStatusOut
from app.audit import service as audit_service
from app.core.config import get_settings


async def list_suggestions(
    db: AsyncSession, *, clinic_id: uuid.UUID, encounter_id: uuid.UUID
) -> list[AiSuggestion]:
    stmt = (
        select(AiSuggestion)
        .where(AiSuggestion.clinic_id == clinic_id, AiSuggestion.encounter_id == encounter_id)
        .order_by(AiSuggestion.created_at)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_status(db: AsyncSession, *, clinic_id: uuid.UUID) -> AiStatusOut:
    settings = get_settings()
    model = await effective_model(db, clinic_id=clinic_id)
    reachable = await ollama_client.is_reachable()
    digest = await ollama_client.model_digest(model) if reachable else None
    return AiStatusOut(
        ai_enabled=settings.ai_enabled,
        ollama_reachable=reachable,
        ollama_model=model,
        ollama_digest=digest,
        whisper_model=settings.whisper_model,
        whisper_device=settings.whisper_device,
    )


async def get_ai_settings(db: AsyncSession, *, clinic_id: uuid.UUID) -> AiSettingsOut:
    settings = get_settings()
    model = await effective_model(db, clinic_id=clinic_id)
    try:
        tags = await ollama_client.tags()
        available = sorted({str(entry.get("name")) for entry in tags if entry.get("name")})
    except ollama_client.OllamaUnavailableError:
        available = []
    return AiSettingsOut(
        ollama_model=model, available_models=available, ai_store_audio=settings.ai_store_audio
    )


async def update_ai_settings(
    db: AsyncSession, *, clinic_id: uuid.UUID, ollama_model: str, actor_id: uuid.UUID
) -> AiSettingsOut:
    clinic_settings = await db.get(AiClinicSettings, clinic_id)
    if clinic_settings is None:
        clinic_settings = AiClinicSettings(clinic_id=clinic_id)
        db.add(clinic_settings)
    clinic_settings.ollama_model = ollama_model
    clinic_settings.updated_by = actor_id

    await audit_service.log(
        db,
        action="ai.settings_updated",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="ai_clinic_settings",
        entity_id=str(clinic_id),
        details={"ollama_model": ollama_model},
    )
    await db.commit()
    return await get_ai_settings(db, clinic_id=clinic_id)
