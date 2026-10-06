"""Cliente httpx asincrono hacia Ollama (docs/03_AGENTE_IA_VOZ.md sec. 3 y 7): 100% local,
sin llamadas a internet. Si Ollama no responde, el resto del sistema sigue funcionando
(la transcripcion funciona siempre; solo /ai/interpret devuelve 503 -- ver interpreter.py)."""

import json
from typing import Any

import httpx

from app.core.config import get_settings

# Fase 12 (E2E): con AI_FAKE_MODE=true, cada dictado produce estas dos acciones fijas
# sin importar el texto -- no es un resumen del transcript, es un doble determinista
# para poder probar "aceptar propuestas" sin depender de un modelo real. Mismo patron
# que el FakeOllama por monkeypatch de las pruebas de integracion (tests/integration/ai),
# pero vive en el cliente mismo para que un backend levantado en otro proceso (como el
# que arranca Playwright) tambien lo use sin tocar interpreter.py ni el router.
_FAKE_CHAT_CONTENT = json.dumps(
    {
        "actions": [
            {"type": "set_chief_complaint", "text": "Dolor en muela inferior derecha"},
            {"type": "add_vital_signs", "hr": 72},
        ],
        "unrecognized": [],
    }
)


class OllamaUnavailableError(Exception):
    """Ollama no responde o tardo mas del timeout configurado (OLLAMA_TIMEOUT_S)."""


async def chat(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    json_schema: dict[str, Any],
) -> dict[str, Any]:
    """Llama a POST /api/chat con format=<json_schema> y temperature=0 (salida
    determinista, igual en cada corrida con el mismo dictado).

    repeat_penalty evita un bucle real observado con qwen2.5:7b: con temperature=0 (exigido
    por docs/03 sec. 3, para que el mismo dictado siempre produzca el mismo resultado) y
    decodificacion forzada por una gramatica tan grande como nuestra union discriminada de
    11 acciones, el muestreo greedy puede quedar atrapado repitiendo el mismo objeto
    valido-pero-incorrecto sin parar (visto en pruebas reales: cientos de copias seguidas
    de {"type": "add_vital_signs", "bp_sys": null, ...}). Penalizar tokens recientes rompe
    el ciclo sin dejar de ser determinista. num_predict es ademas una red de seguridad:
    acota cuanto se puede generar, para que un bucle que repeat_penalty no alcance a romper
    termine en un error rapido en vez de agotar todo OLLAMA_TIMEOUT_S."""
    settings = get_settings()
    if settings.ai_fake_mode:
        return {"message": {"role": "assistant", "content": _FAKE_CHAT_CONTENT}}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "format": json_schema,
        "stream": False,
        "options": {"temperature": 0, "repeat_penalty": 1.3, "num_predict": 800},
    }
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_s) as client:
            response = await client.post(f"{settings.ollama_url}/api/chat", json=payload)
            response.raise_for_status()
            return dict(response.json())
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        raise OllamaUnavailableError(str(exc)) from exc


async def tags() -> list[dict[str, Any]]:
    """GET /api/tags: modelos instalados en Ollama, para el estado y el selector de
    modelo en Configuracion -> Asistente IA."""
    settings = get_settings()
    if settings.ai_fake_mode:
        return [{"name": "fake-e2e-model", "model": "fake-e2e-model", "digest": "fakedigest"}]
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return list(data.get("models", []))
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        raise OllamaUnavailableError(str(exc)) from exc


async def is_reachable() -> bool:
    try:
        await tags()
        return True
    except OllamaUnavailableError:
        return False


async def model_digest(model: str) -> str | None:
    """Digest del modelo instalado (docs sec. 9: cada sugerencia guarda el digest del
    modelo de Ollama que la produjo)."""
    try:
        for entry in await tags():
            if entry.get("name") == model or entry.get("model") == model:
                digest = entry.get("digest")
                return str(digest) if digest else None
    except OllamaUnavailableError:
        return None
    return None
