from app.modules.clinical_documents.rules import (
    allergy_summary,
    next_folio,
    vital_signs_summary_values,
)


def test_next_folio_starts_at_one() -> None:
    assert next_folio(0) == "RX-000001"


def test_next_folio_increments_from_existing_count() -> None:
    assert next_folio(41) == "RX-000042"


def test_allergy_summary_no_allergies() -> None:
    has_allergies, label = allergy_summary([])
    assert has_allergies is False
    assert label == ""


def test_allergy_summary_joins_labels() -> None:
    has_allergies, label = allergy_summary(["Penicilina", "Latex"])
    assert has_allergies is True
    assert label == "Penicilina, Latex"


def test_vital_signs_summary_values_with_all_data() -> None:
    result = vital_signs_summary_values(
        height_m=1.70, weight_kg=70.0, temperature=36.5, bp_systolic=120, bp_diastolic=80
    )
    assert result == {
        "talla": "1.70",
        "peso": "70.0",
        "imc": "24.2",
        "temperatura": "36.5",
        "tension": "120/80",
    }


def test_vital_signs_summary_values_missing_data_uses_placeholder() -> None:
    result = vital_signs_summary_values(
        height_m=None, weight_kg=None, temperature=None, bp_systolic=None, bp_diastolic=None
    )
    assert result == {
        "talla": "-",
        "peso": "-",
        "imc": "-",
        "temperatura": "-",
        "tension": "-",
    }
