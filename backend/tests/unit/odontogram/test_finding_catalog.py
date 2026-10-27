from app.modules.odontogram.finding_catalog import FINDING_CATALOG, FINDING_CODES
from app.seed import CATALOG_SEEDS

# Reconciliacion con la leyenda oficial de docs/clinica (Fase B): Rojo = caries,
# Azul = protesis y restauraciones, Negro = ausente/restos radiculares,
# Verde = biopelicula y tartaro dental.


def test_biopelicula_tartaro_exists_and_is_green() -> None:
    assert "biopelicula_tartaro" in FINDING_CODES
    item = FINDING_CATALOG["biopelicula_tartaro"]
    assert item["color"] == "#6AB04C"
    assert item["label"] == "Biopelicula y tartaro dental"
    assert item["symbol"]


def test_ausente_is_black_not_gray() -> None:
    item = FINDING_CATALOG["ausente"]
    assert item["color"] == "#1A1A1A"
    assert item["color"] != "#8C8C8C"  # gris viejo, ya no vigente


def test_sellador_no_longer_shares_the_green_reserved_for_the_official_legend() -> None:
    sellador = FINDING_CATALOG["sellador"]
    biopelicula = FINDING_CATALOG["biopelicula_tartaro"]
    assert sellador["color"] != biopelicula["color"]
    assert sellador["color"] not in {"#D64545", "#1A1A1A"}  # ni rojo ni negro (reservados)


def test_restauracion_and_protesis_fija_share_the_same_blue_family() -> None:
    """La leyenda oficial agrupa 'protesis y restauraciones' en un solo color azul."""
    assert FINDING_CATALOG["restauracion"]["color"] == "#4A90C2"
    assert FINDING_CATALOG["protesis_fija"]["color"] == "#3A7FC1"


def test_caries_and_extraccion_indicada_share_the_official_red() -> None:
    assert FINDING_CATALOG["caries"]["color"] == FINDING_CATALOG["extraccion_indicada"]["color"]
    assert FINDING_CATALOG["caries"]["color"] == "#D64545"


def test_unrelated_findings_keep_their_original_color() -> None:
    """El usuario pidio explicitamente dejar el resto igual."""
    assert FINDING_CATALOG["sano"]["color"] == "#A9C6B8"
    assert FINDING_CATALOG["corona"]["color"] == "#E0A100"
    assert FINDING_CATALOG["endodoncia"]["color"] == "#7B5EA7"
    assert FINDING_CATALOG["implante"]["color"] == "#2BB3A3"
    assert FINDING_CATALOG["fractura"]["color"] == "#B8460E"
    assert FINDING_CATALOG["movilidad"]["color"] == "#C77D1E"


def test_every_catalog_entry_has_label_color_and_symbol_key() -> None:
    for code in FINDING_CODES:
        item = FINDING_CATALOG[code]
        assert "label" in item
        assert "color" in item and item["color"].startswith("#")
        assert "symbol" in item


def test_app_seed_matches_finding_catalog_for_odontogram_findings() -> None:
    """app/seed.py::CATALOG_SEEDS (lo que ve una clinica NUEVA) y
    odontogram/finding_catalog.py (plantilla/fallback de Python) son dos de los 5 lugares
    que hay que mantener en sincrono al cambiar un color (ver docstring de
    finding_catalog.py) -- esta prueba evita que se desincronicen en silencio."""
    seeded_findings = {
        code: extra
        for catalog_type, code, _name, _order, extra in CATALOG_SEEDS
        if catalog_type == "odontogram_finding"
    }
    assert set(seeded_findings) == set(FINDING_CODES)
    for code, extra in seeded_findings.items():
        assert extra["color"] == FINDING_CATALOG[code]["color"], code
        assert extra["symbol"] == FINDING_CATALOG[code]["symbol"], code
