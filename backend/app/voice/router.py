from fastapi import APIRouter, WebSocket

from app.voice.session import handle_connection

router = APIRouter(tags=["voice"])


@router.websocket("/voice/ws")
async def voice_ws(websocket: WebSocket) -> None:
    """Fase 13 ("Dentia"), 13.1 "Base de voz". Autenticacion por mensaje (no por
    header: el navegador no puede mandar Authorization en un WebSocket), ver
    app/voice/session.py::authenticate. Usa el sessionmaker del estado de la app
    (no Depends(get_db)) porque un endpoint de WebSocket no vuelve a correr sus
    dependencias en cada mensaje -- igual que AccessDeniedAuditMiddleware."""
    sessionmaker = websocket.app.state.db_sessionmaker
    async with sessionmaker() as db:
        await handle_connection(websocket, db)
