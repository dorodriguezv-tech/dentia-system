from app.modules.diagnosis import rules


def test_catalog_has_a_code_and_label_for_every_entry() -> None:
    assert len(rules.DIAGNOSIS_CATALOG) == len(rules.DIAGNOSIS_CODES)
    for code in rules.DIAGNOSIS_CODES:
        assert rules.DIAGNOSIS_CATALOG[code]


def test_common_diagnoses_are_present() -> None:
    assert "caries" in rules.DIAGNOSIS_CODES
    assert "pulpitis_irreversible" in rules.DIAGNOSIS_CODES
    assert "gingivitis" in rules.DIAGNOSIS_CODES
