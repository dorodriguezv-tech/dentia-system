import uuid

from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import applier, interpreter, service, stt
from app.ai.schemas import (
    AcceptSuggestionRequest,
    AiSettingsOut,
    AiSettingsUpdateRequest,
    AiStatusOut,
    AiSuggestionOut,
    InterpretRequest,
    InterpretResponse,
    RejectSuggestionRequest,
    TranscribeResponse,
    UnrecognizedOut,
)
from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.core.errors import AppError
from app.core.storage import StorageBackend, get_storage_backend
from app.modules.iam.models import User

router = APIRouter(tags=["ai"])


def _require_ai_enabled() -> None:
    """Interruptor de apagado: AI_ENABLED=false en .env desactiva de verdad el
    uso del asistente (transcribir, interpretar), no solo el badge de estado.
    Las sugerencias ya creadas se pueden seguir listando/aceptando/rechazando."""
    if not get_settings().ai_enabled:
        raise AppError(
            code="AI_DISABLED",
            message="El asistente de IA esta deshabilitado temporalmente.",
            status_code=503,
        )


@router.post("/ai/transcribe", response_model=TranscribeResponse)
async def transcribe(
    audio: UploadFile,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("ai.use")),
    storage: StorageBackend = Depends(get_storage_backend),
) -> TranscribeResponse:
    _require_ai_enabled()
    data = await audio.read()
    settings = get_settings()
    if settings.ai_store_audio:
        storage.save(data, subdir=f"ai_audio/{clinic_id}", suffix=".webm")
    text = stt.transcribe(data)
    return TranscribeResponse(text=text)


@router.post("/ai/interpret", response_model=InterpretResponse)
async def interpret(
    payload: InterpretRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("ai.use")),
    db: AsyncSession = Depends(get_db),
) -> InterpretResponse:
    _require_ai_enabled()
    suggestions, unrecognized = await interpreter.interpret(
        db,
        clinic_id=clinic_id,
        encounter_id=payload.encounter_id,
        transcript=payload.transcript,
        actor_id=actor.id,
    )
    return InterpretResponse(
        suggestions=[AiSuggestionOut.model_validate(s) for s in suggestions],
        unrecognized=[UnrecognizedOut(text=u.text, reason=u.reason) for u in unrecognized],
    )


@router.get("/ai/suggestions", response_model=list[AiSuggestionOut])
async def list_suggestions(
    encounter_id: uuid.UUID = Query(...),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("ai.use")),
    db: AsyncSession = Depends(get_db),
) -> list[AiSuggestionOut]:
    items = await service.list_suggestions(db, clinic_id=clinic_id, encounter_id=encounter_id)
    return [AiSuggestionOut.model_validate(i) for i in items]


@router.post("/ai/suggestions/{suggestion_id}/accept", response_model=AiSuggestionOut)
async def accept_suggestion(
    suggestion_id: uuid.UUID,
    payload: AcceptSuggestionRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("ai.use")),
    db: AsyncSession = Depends(get_db),
) -> AiSuggestionOut:
    item, _entity_id = await applier.accept_suggestion(
        db, clinic_id=clinic_id, suggestion_id=suggestion_id, edits=payload.edits, actor_id=actor.id
    )
    return AiSuggestionOut.model_validate(item)


@router.post("/ai/suggestions/{suggestion_id}/reject", response_model=AiSuggestionOut)
async def reject_suggestion(
    suggestion_id: uuid.UUID,
    payload: RejectSuggestionRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("ai.use")),
    db: AsyncSession = Depends(get_db),
) -> AiSuggestionOut:
    item = await applier.reject_suggestion(
        db,
        clinic_id=clinic_id,
        suggestion_id=suggestion_id,
        reason=payload.reason,
        actor_id=actor.id,
    )
    return AiSuggestionOut.model_validate(item)


@router.get("/ai/status", response_model=AiStatusOut)
async def get_status(
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("ai.configure")),
    db: AsyncSession = Depends(get_db),
) -> AiStatusOut:
    return await service.get_status(db, clinic_id=clinic_id)


@router.get("/ai/settings", response_model=AiSettingsOut)
async def get_ai_settings(
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("ai.configure")),
    db: AsyncSession = Depends(get_db),
) -> AiSettingsOut:
    return await service.get_ai_settings(db, clinic_id=clinic_id)


@router.put("/ai/settings", response_model=AiSettingsOut)
async def update_ai_settings(
    payload: AiSettingsUpdateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("ai.configure")),
    db: AsyncSession = Depends(get_db),
) -> AiSettingsOut:
    return await service.update_ai_settings(
        db, clinic_id=clinic_id, ollama_model=payload.ollama_model, actor_id=actor.id
    )
