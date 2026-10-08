import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.voice.models import VoiceCommandLog


async def log_command(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    event: str,
    transcript: str | None = None,
    confirmation_mode: str | None = None,
    result: str | None = None,
    latency_ms: int | None = None,
) -> None:
    db.add(
        VoiceCommandLog(
            clinic_id=clinic_id,
            user_id=user_id,
            event=event,
            transcript=transcript,
            confirmation_mode=confirmation_mode,
            result=result,
            latency_ms=latency_ms,
        )
    )
    await db.commit()
