import pytest
from pydantic import TypeAdapter, ValidationError

from app.ai.actions import ACTION_MODELS_BY_TYPE, AiAction, AiInterpretResult

_adapter: TypeAdapter[AiAction] = TypeAdapter(AiAction)


def test_all_eleven_action_types_are_registered() -> None:
    assert len(ACTION_MODELS_BY_TYPE) == 11


def test_add_tooth_finding_parses_with_discriminator() -> None:
    action = _adapter.validate_python(
        {
            "type": "add_tooth_finding",
            "tooth_fdi": 36,
            "surfaces": ["O", "D"],
            "finding_code": "caries",
        }
    )
    assert action.type == "add_tooth_finding"
    assert action.tooth_fdi == 36  # type: ignore[union-attr]


def test_schedule_followup_defaults_and_bounds() -> None:
    action = _adapter.validate_python(
        {"type": "schedule_followup", "in_days": 15, "reason": "Control"}
    )
    assert action.type == "schedule_followup"


def test_unknown_type_is_rejected_by_discriminator() -> None:
    with pytest.raises(ValidationError):
        _adapter.validate_python({"type": "finalize_note", "text": "x"})


def test_invalid_finding_code_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _adapter.validate_python(
            {
                "type": "add_tooth_finding",
                "tooth_fdi": 36,
                "surfaces": [],
                "finding_code": "no_existe",
            }
        )


def test_interpret_result_accepts_empty_actions_and_unrecognized() -> None:
    result = AiInterpretResult.model_validate({"actions": [], "unrecognized": []})
    assert result.actions == []
    assert result.unrecognized == []


def test_interpret_result_json_schema_has_discriminator_mapping() -> None:
    schema = AiInterpretResult.model_json_schema()
    assert "actions" in schema["properties"]
