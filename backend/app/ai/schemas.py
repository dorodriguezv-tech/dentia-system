import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.ai.rules import STATUSES

Status = Literal["PENDING", "ACCEPTED", "REJECTED"]


class TranscribeResponse(BaseModel):
    text: str


class InterpretRequest(BaseModel):
    encounter_id: uuid.UUID
    transcript: str = Field(min_length=1, max_length=8000)


class UnrecognizedOut(BaseModel):
    text: str
    reason: str


class InterpretResponse(BaseModel):
    suggestions: list["AiSuggestionOut"]
    unrecognized: list[UnrecognizedOut]


class AiSuggestionOut(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID
    encounter_id: uuid.UUID
    action_type: str
    payload: dict[str, Any]
    status: Status
    model_name: str
    model_digest: str | None
    transcript_excerpt: str | None
    created_at: datetime
    reviewed_at: datetime | None
    reject_reason: str | None

    model_config = {"from_attributes": True}


class AcceptSuggestionRequest(BaseModel):
    """`edits` sobreescribe campos del payload original antes de aplicarlo (docs sec. 3:
    "Aceptar/Editar"), por ejemplo para corregir una pieza o un texto antes de guardar."""

    edits: dict[str, Any] | None = None


class RejectSuggestionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class AiStatusOut(BaseModel):
    ai_enabled: bool
    ollama_reachable: bool
    ollama_model: str
    ollama_digest: str | None
    whisper_model: str
    whisper_device: str


class AiSettingsOut(BaseModel):
    ollama_model: str
    available_models: list[str]
    ai_store_audio: bool


class AiSettingsUpdateRequest(BaseModel):
    ollama_model: str = Field(min_length=1, max_length=100)


def _validate_catalogs() -> None:
    assert set(STATUSES) == set(Status.__args__)  # type: ignore[attr-defined]


_validate_catalogs()
