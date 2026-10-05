import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service


async def test_log_creates_an_event(db_session: AsyncSession) -> None:
    event = await audit_service.log(db_session, action="auth.login")
    await db_session.commit()

    assert event.id is not None
    assert event.action == "auth.login"


async def test_audit_event_cannot_be_updated(db_session: AsyncSession) -> None:
    event = await audit_service.log(db_session, action="auth.login")
    await db_session.commit()

    with pytest.raises(DBAPIError, match="append-only"):
        await db_session.execute(
            text("UPDATE audit_events SET action = 'tampered' WHERE id = :id"),
            {"id": str(event.id)},
        )
        await db_session.commit()


async def test_audit_event_cannot_be_deleted(db_session: AsyncSession) -> None:
    event = await audit_service.log(db_session, action="auth.login")
    await db_session.commit()

    with pytest.raises(DBAPIError, match="append-only"):
        await db_session.execute(
            text("DELETE FROM audit_events WHERE id = :id"), {"id": str(event.id)}
        )
        await db_session.commit()
