"""Fase F (rediseno del expediente, docs/clinica): reglas de la Historia
Clinica de Endodoncia -- catalogos fijos (NO administrables) y validacion de
piezas FDI permanentes + codigos del odontograma de endodoncia (0-17)."""

from app.modules.endodontic_history import rules


def test_fixed_checklist_catalogs_are_non_empty_tuples() -> None:
    assert "caries" in rules.ANTECEDENTES_KEYS
    assert "tratamiento_conductos" in rules.ANTECEDENTES_KEYS
    assert "localizado" in rules.DOLOR_KEYS
    assert "frio" in rules.ESTIMULO_KEYS
    assert "exposicion_pulpar" in rules.EXAMEN_INTRABUCAL_KEYS
    assert "ganglios_linfaticos" in rules.EXAMEN_EXTRABUCAL_KEYS
    assert rules.PERCUSION_KEYS == ("fugaz", "persistente", "localizado", "irradiado")
    assert rules.MOVILIDAD_VALUES == ("positiva", "negativa")
    assert rules.MOVILIDAD_GRADOS == ("I", "II", "III")
    assert "normal" in rules.CAMARA_KEYS
    assert "obturado" in rules.CONDUCTO_KEYS
    assert "resorcion_apical" in rules.PERIODONTO_KEYS
    assert "biopulpectomia" in rules.TRATAMIENTO_KEYS
    assert "apicectomia" in rules.CIRUGIA_KEYS


def test_diagnostico_pulpar_and_periapical_are_closed_single_select_catalogs() -> None:
    assert len(rules.DIAGNOSTICO_PULPAR_VALUES) == 6
    assert "pulpitis_irreversible" in rules.DIAGNOSTICO_PULPAR_VALUES
    assert len(rules.DIAGNOSTICO_PERIAPICAL_VALUES) == 6
    assert "absceso_fenix_cronico" in rules.DIAGNOSTICO_PERIAPICAL_VALUES


def test_endodontic_tooth_codes_cover_0_to_17_and_are_independent_of_general_odontogram() -> None:
    # 18 codigos (0-17) propios de endodoncia (no toca app.modules.odontogram).
    assert len(rules.ENDODONTIC_TOOTH_CODES) == 18
    assert frozenset(range(18)) == rules.ENDODONTIC_TOOTH_CODE_VALUES
    assert rules.ENDODONTIC_TOOTH_CODE_LABELS[0] == "sano"
    assert rules.ENDODONTIC_TOOTH_CODE_LABELS[17] == "lesion_endoperiodontal"
    assert rules.is_valid_endodontic_tooth_code(0) is True
    assert rules.is_valid_endodontic_tooth_code(17) is True
    assert rules.is_valid_endodontic_tooth_code(18) is False
    assert rules.is_valid_endodontic_tooth_code(-1) is False


def test_endodontic_tooth_kinds_are_diagnostico_and_evolucion() -> None:
    assert rules.ENDODONTIC_TOOTH_KINDS == ("diagnostico", "evolucion")


def test_is_valid_permanent_tooth_code_rejects_temporary_and_unknown() -> None:
    # Solo piezas permanentes (el dibujo del PDF original no incluye
    # temporales), a diferencia del odontograma pediatrico de la Fase E.
    assert rules.is_valid_permanent_tooth_code("11") is True
    assert rules.is_valid_permanent_tooth_code("48") is True
    assert rules.is_valid_permanent_tooth_code("55") is False
    assert rules.is_valid_permanent_tooth_code("99") is False
    assert rules.is_valid_permanent_tooth_code("not-a-tooth") is False


def test_canal_keys_cover_all_documented_canals() -> None:
    assert rules.CANAL_KEYS == (
        "mesial",
        "mesiolingual",
        "mesiovestibular",
        "mesiopalatino",
        "distal",
        "distolingual",
        "distopalatino",
        "distovestibular",
        "palatino",
        "unico",
    )
