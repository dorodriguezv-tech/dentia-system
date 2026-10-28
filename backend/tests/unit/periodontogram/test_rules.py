"""Fase G (rediseno del expediente, docs/clinica -- ultimo slice del
proyecto): reglas del Periodontograma completo -- catalogos fijos y los
calculos derivados que NUNCA se persisten (CAL, indice de placa
dentobacteriana, indice gingival de Loe-Silness)."""

from app.modules.periodontogram import rules


def test_probing_sites_are_the_6_standard_sites() -> None:
    assert rules.PROBING_SITES == (
        "mesiovestibular",
        "vestibular",
        "distovestibular",
        "mesiolingual",
        "lingual",
        "distolingual",
    )
    assert set(rules.PROBING_SITE_LABELS.keys()) == set(rules.PROBING_SITES)


def test_probing_depth_and_recession_ranges() -> None:
    assert (rules.PROBING_DEPTH_MM_MIN, rules.PROBING_DEPTH_MM_MAX) == (0, 15)
    # La recesion puede ser negativa (agrandamiento/cobertura gingival).
    assert (rules.RECESSION_MM_MIN, rules.RECESSION_MM_MAX) == (-5, 15)


def test_mobility_and_furcation_grade_ranges() -> None:
    assert (rules.MOBILITY_GRADE_MIN, rules.MOBILITY_GRADE_MAX) == (0, 3)
    assert (rules.FURCATION_GRADE_MIN, rules.FURCATION_GRADE_MAX) == (0, 3)


def test_index_types_and_surfaces() -> None:
    assert rules.INDEX_TYPES == ("placa", "gingival")
    assert rules.INDEX_SURFACES == ("vestibular", "lingual")
    assert set(rules.INDEX_SURFACE_LABELS.keys()) == set(rules.INDEX_SURFACES)
    assert (rules.INDEX_GRADE_MIN, rules.INDEX_GRADE_MAX) == (0, 3)


def test_plaque_and_gingival_grade_labels_cover_0_to_3() -> None:
    assert set(rules.PLAQUE_GRADE_LABELS.keys()) == {0, 1, 2, 3}
    assert set(rules.GINGIVAL_GRADE_LABELS.keys()) == {0, 1, 2, 3}
    assert rules.PLAQUE_GRADE_LABELS[0] == "Ausencia de placa"
    assert rules.GINGIVAL_GRADE_LABELS[0] == "Normal (encia sana)"


def test_occlusal_movements_are_the_4_documented() -> None:
    assert rules.OCCLUSAL_MOVEMENTS == (
        "centrica",
        "lateralidad_izquierda",
        "protrusion",
        "lateralidad_derecha",
    )
    assert set(rules.OCCLUSAL_MOVEMENT_LABELS.keys()) == set(rules.OCCLUSAL_MOVEMENTS)


def test_is_valid_permanent_tooth_code_rejects_temporary_and_unknown() -> None:
    # Solo piezas permanentes (el dibujo del PDF original no incluye
    # temporales), mismo criterio que endodontic_history.
    assert rules.is_valid_permanent_tooth_code("11") is True
    assert rules.is_valid_permanent_tooth_code("48") is True
    assert rules.is_valid_permanent_tooth_code("55") is False
    assert rules.is_valid_permanent_tooth_code("99") is False
    assert rules.is_valid_permanent_tooth_code("not-a-tooth") is False


def test_clinical_attachment_level_is_depth_plus_recession() -> None:
    assert rules.clinical_attachment_level_mm(3, 0) == 3
    assert rules.clinical_attachment_level_mm(3, 2) == 5
    # Recesion negativa (cobertura gingival) reduce el CAL.
    assert rules.clinical_attachment_level_mm(3, -1) == 2


def test_compute_plaque_index_ratio_of_pigmented_faces() -> None:
    total, pigmented, index = rules.compute_plaque_index([0, 1, 2, 0])
    assert total == 4
    assert pigmented == 2
    assert index == 0.5


def test_compute_plaque_index_with_no_data_returns_none_not_zero() -> None:
    total, pigmented, index = rules.compute_plaque_index([])
    assert (total, pigmented, index) == (0, 0, None)


def test_compute_plaque_index_all_clean() -> None:
    total, pigmented, index = rules.compute_plaque_index([0, 0, 0])
    assert (total, pigmented, index) == (3, 0, 0.0)


def test_compute_gingival_index_is_arithmetic_mean() -> None:
    total, index = rules.compute_gingival_index([0, 1, 2, 3])
    assert total == 4
    assert index == 1.5


def test_compute_gingival_index_with_no_data_returns_none_not_zero() -> None:
    total, index = rules.compute_gingival_index([])
    assert (total, index) == (0, None)
