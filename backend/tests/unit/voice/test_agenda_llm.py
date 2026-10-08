import json

import pytest
from pydantic import ValidationError

from app.ai.ollama_client import OllamaUnavailableError
from app.voice import agenda_llm


def _chat_returning(content: dict | str):
    body = content if isinstance(content, str) else json.dumps(content)

    async def _chat(**_kwargs):
        return {"message": {"role": "assistant", "content": body}}

    return _chat


async def test_interpret_agenda_order_parses_agendar_cita(monkeypatch) -> None:
    monkeypatch.setattr(
        agenda_llm.ollama_client,
        "chat",
        _chat_returning(
            {
                "action": {
                    "type": "agendar_cita",
                    "patient_name": "Maria Lopez",
                    "provider_name": "doctora Ruiz",
                    "date_text": "jueves",
                    "time_text": "11",
                }
            }
        ),
    )
    result = await agenda_llm.interpret_agenda_order("agendale a Maria Lopez el jueves")
    assert result is not None
    assert isinstance(result.action, agenda_llm.AgendarCitaAction)
    assert result.action.patient_name == "Maria Lopez"
    assert result.action.date_text == "jueves"


async def test_interpret_agenda_order_with_null_action_returns_a_result_without_one(
    monkeypatch,
) -> None:
    monkeypatch.setattr(agenda_llm.ollama_client, "chat", _chat_returning({"action": None}))
    result = await agenda_llm.interpret_agenda_order("cuentame un chiste")
    assert result is not None
    assert result.action is None


async def test_interpret_agenda_order_with_invalid_json_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(agenda_llm.ollama_client, "chat", _chat_returning("no es json"))
    result = await agenda_llm.interpret_agenda_order("algo")
    assert result is None


async def test_interpret_agenda_order_with_an_unknown_discriminator_returns_none(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        agenda_llm.ollama_client,
        "chat",
        _chat_returning({"action": {"type": "algo_inventado"}}),
    )
    result = await agenda_llm.interpret_agenda_order("algo")
    assert result is None


async def test_interpret_agenda_order_when_ollama_is_unavailable_returns_none(
    monkeypatch,
) -> None:
    async def _unavailable(**_kwargs):
        raise OllamaUnavailableError("sin conexion")

    monkeypatch.setattr(agenda_llm.ollama_client, "chat", _unavailable)
    result = await agenda_llm.interpret_agenda_order("algo")
    assert result is None


def test_cancelar_cita_action_requires_a_reason() -> None:
    with pytest.raises(ValidationError):
        agenda_llm.CancelarCitaAction(type="cancelar_cita", patient_name="Maria Lopez")
