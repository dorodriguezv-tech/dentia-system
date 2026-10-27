"""Fase E (rediseno del expediente, docs/clinica): reglas de la Historia
Clinica Pediatrica -- catalogos por defecto y validacion de piezas FDI
(permanentes Y temporales, a diferencia del diagnostico/plan por organo
dental de Fase C que solo admite permanentes)."""

from app.modules.pediatric_history import rules


def test_default_catalogs_are_non_empty_tuples() -> None:
    assert "apatico" in rules.PEDIATRIC_CHARACTER_OPTIONS
    assert "hiperactivo" in rules.PEDIATRIC_CHARACTER_OPTIONS
    assert "recto" in rules.TERMINAL_PLANE_OPTIONS
    assert "mesial" in rules.TERMINAL_PLANE_OPTIONS
    assert "distal" in rules.TERMINAL_PLANE_OPTIONS
    assert "normal" in rules.LINEA_MEDIA_OPTIONS
    assert "I" in rules.CLASIFICACION_ANGLE_OPTIONS


def test_pediatric_tooth_anomaly_options_include_both_absent_variants() -> None:
    # Nota de correccion del plan original: la distincion congenito/adquirida
    # NO vive en el catalogo global `odontogram_finding` (Fase B) -- es
    # exclusiva de este catalogo `pediatric_tooth_anomaly`.
    assert len(rules.PEDIATRIC_TOOTH_ANOMALY_OPTIONS) == 10
    assert "ausente_congenito" in rules.PEDIATRIC_TOOTH_ANOMALY_CODES
    assert "ausente_adquirida" in rules.PEDIATRIC_TOOTH_ANOMALY_CODES
    assert "diente_fusionado" in rules.PEDIATRIC_TOOTH_ANOMALY_CODES
    assert "inflamacion_gingival" in rules.PEDIATRIC_TOOTH_ANOMALY_CODES


def test_is_valid_tooth_code_accepts_permanent_and_temporary_fdi() -> None:
    assert rules.is_valid_tooth_code("11") is True
    assert rules.is_valid_tooth_code("48") is True
    assert rules.is_valid_tooth_code("55") is True
    assert rules.is_valid_tooth_code("85") is True
    assert rules.is_valid_tooth_code("99") is False
    assert rules.is_valid_tooth_code("not-a-tooth") is False


def test_eruption_chronology_reference_tables_are_documentation_only() -> None:
    # Contenido fijo de referencia (no estructura de BD) -- ver nota en rules.py.
    assert len(rules.PRIMARY_TOOTH_ERUPTION_CHRONOLOGY) == 5
    assert all(
        {"diente", "erupcion", "caida"} <= set(row)
        for row in rules.PRIMARY_TOOTH_ERUPTION_CHRONOLOGY
    )
    assert len(rules.PERMANENT_TOOTH_ERUPTION_CHRONOLOGY) == 8
