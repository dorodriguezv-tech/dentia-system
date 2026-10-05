from app.modules.odontogram import rules


def test_permanent_catalog_has_32_teeth() -> None:
    assert len(rules.TOOTH_FDI_PERMANENT) == 32
    assert 11 in rules.TOOTH_FDI_PERMANENT
    assert 48 in rules.TOOTH_FDI_PERMANENT


def test_temporary_catalog_has_20_teeth() -> None:
    assert len(rules.TOOTH_FDI_TEMPORARY) == 20
    assert 51 in rules.TOOTH_FDI_TEMPORARY
    assert 85 in rules.TOOTH_FDI_TEMPORARY


def test_is_valid_tooth_accepts_permanent_and_temporary() -> None:
    assert rules.is_valid_tooth(36) is True
    assert rules.is_valid_tooth(55) is True


def test_is_valid_tooth_rejects_out_of_catalog_numbers() -> None:
    assert rules.is_valid_tooth(19) is False  # posicion 9 no existe
    assert rules.is_valid_tooth(59) is False
    assert rules.is_valid_tooth(0) is False
    assert rules.is_valid_tooth(99) is False


def test_is_temporary_tooth() -> None:
    assert rules.is_temporary_tooth(55) is True
    assert rules.is_temporary_tooth(16) is False


def test_is_upper_tooth() -> None:
    assert rules.is_upper_tooth(16) is True  # cuadrante 1
    assert rules.is_upper_tooth(26) is True  # cuadrante 2
    assert rules.is_upper_tooth(36) is False  # cuadrante 3
    assert rules.is_upper_tooth(46) is False  # cuadrante 4


def test_is_anterior_tooth() -> None:
    assert rules.is_anterior_tooth(11) is True  # incisivo central
    assert rules.is_anterior_tooth(13) is True  # canino
    assert rules.is_anterior_tooth(16) is False  # molar


def test_valid_surfaces_for_posterior_upper_tooth() -> None:
    assert rules.valid_surfaces_for_tooth(16) == frozenset({"M", "D", "V", "P", "O"})


def test_valid_surfaces_for_posterior_lower_tooth() -> None:
    assert rules.valid_surfaces_for_tooth(46) == frozenset({"M", "D", "V", "L", "O"})


def test_valid_surfaces_for_anterior_upper_tooth() -> None:
    assert rules.valid_surfaces_for_tooth(11) == frozenset({"M", "D", "V", "P", "I"})


def test_valid_surfaces_for_anterior_lower_tooth() -> None:
    assert rules.valid_surfaces_for_tooth(41) == frozenset({"M", "D", "V", "L", "I"})


def test_is_valid_surface_for_tooth_accepts_whole_tooth() -> None:
    assert rules.is_valid_surface_for_tooth(16, None) is True


def test_is_valid_surface_for_tooth_rejects_incompatible_surface() -> None:
    assert rules.is_valid_surface_for_tooth(16, "I") is False  # posterior no tiene incisal
    assert rules.is_valid_surface_for_tooth(11, "O") is False  # anterior no tiene oclusal
    assert rules.is_valid_surface_for_tooth(16, "L") is False  # pieza superior no tiene lingual
    assert rules.is_valid_surface_for_tooth(46, "P") is False  # pieza inferior no tiene palatino


def test_is_valid_surface_for_tooth_accepts_compatible_surface() -> None:
    assert rules.is_valid_surface_for_tooth(16, "O") is True
    assert rules.is_valid_surface_for_tooth(11, "I") is True
