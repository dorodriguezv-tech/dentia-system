"""C3 del doc 06 (Fase 13): extraccion del vocabulario odontologico desde un
PDF. No usa el PDF real (lento, y acopla la prueba a su contenido exacto) --
pdfplumber.open se mockea con paginas de texto controladas, igual que
AI_FAKE_MODE mockea Ollama en otras pruebas de este modulo."""

from pathlib import Path

import pytest

from app.ai.vocab import build


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakePdf:
    def __init__(self, pages_text: list[str]) -> None:
        self.pages = [_FakePage(t) for t in pages_text]

    def __enter__(self) -> "_FakePdf":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def _fake_open(pages_text: list[str]):
    def _open(_path: Path) -> _FakePdf:
        return _FakePdf(pages_text)

    return _open


def test_extract_terms_parses_basic_entries(monkeypatch) -> None:
    text = (
        "Odontologia: diccionario\n"
        "ABSCESO. Inflamacion de un tejido con pus.\n"
        "ABRASIVOS. Sustancias empleadas para tallar y pulir.\n"
    )
    monkeypatch.setattr(build.pdfplumber, "open", _fake_open([text] * 5))

    terms = build.extract_terms(Path("fake.pdf"))

    assert "absceso" in terms
    assert "abrasivos" in terms


def test_extract_terms_splits_comma_separated_synonyms(monkeypatch) -> None:
    # "A-" por si sola queda en un solo caracter tras quitarle el guion de
    # prefijo -- se descarta a proposito (termino demasiado corto para servir
    # de vocabulario); "AN-" si tiene longitud util.
    text = "PERI-, AN-. (como prefijos) Alrededor / ausencia.\n" * 5
    monkeypatch.setattr(build.pdfplumber, "open", _fake_open([text] * 5))

    terms = build.extract_terms(Path("fake.pdf"))

    assert "peri" in terms
    assert "an" in terms


def test_extract_terms_keeps_a_short_parenthetical_category(monkeypatch) -> None:
    text = "ANISO. (como prefijo) Desigual.\n" * 5
    monkeypatch.setattr(build.pdfplumber, "open", _fake_open([text] * 5))

    terms = build.extract_terms(Path("fake.pdf"))

    assert terms["aniso"] == "como prefijo"


def test_extract_terms_does_not_treat_a_cross_reference_as_a_category(monkeypatch) -> None:
    text = "ABRASION. (ver DEGASTE ABRASIVO) Perdida de tejido.\n" * 5
    monkeypatch.setattr(build.pdfplumber, "open", _fake_open([text] * 5))

    terms = build.extract_terms(Path("fake.pdf"))

    assert terms["abrasion"] is None


def test_extract_terms_does_not_merge_a_lone_section_letter_into_the_next_entry(
    monkeypatch,
) -> None:
    """Bug real encontrado construyendo este extractor: una letra sola en su
    propio renglon (divisor alfabetico de seccion, p.ej. "B") se fusionaba
    con la entrada siguiente si el separador de sinonimos permitia saltos de
    linea -- "bandas" se perdia por completo."""
    text = "...texto previo.\nB\nBANDAS. Elementos metalicos para ortodoncia.\n" * 5
    monkeypatch.setattr(build.pdfplumber, "open", _fake_open([text] * 5))

    terms = build.extract_terms(Path("fake.pdf"))

    assert "bandas" in terms


def test_extract_terms_stops_at_the_bibliography_heading(monkeypatch) -> None:
    text = (
        "ABSCESO. Inflamacion de un tejido con pus.\n"
        "B I B L I O G R A F I A\n"
        "NOTAUTOR. Cita bibliografica cualquiera.\n"
    )
    monkeypatch.setattr(build.pdfplumber, "open", _fake_open([text] * 5))

    terms = build.extract_terms(Path("fake.pdf"))

    assert "absceso" in terms
    assert "notautor" not in terms


def test_extract_terms_ignores_the_word_bibliografia_in_normal_prose(monkeypatch) -> None:
    """A diferencia del encabezado espaciado, la palabra normal
    "bibliografia" dentro de una oracion no debe truncar nada."""
    text = (
        "De forma analoga, a la hora de consultar bibliografia para\n"
        "realizar un trabajo.\n"
        "ABSCESO. Inflamacion de un tejido con pus.\n"
    )
    monkeypatch.setattr(build.pdfplumber, "open", _fake_open([text] * 5))

    terms = build.extract_terms(Path("fake.pdf"))

    assert "absceso" in terms


def test_extract_terms_raises_for_a_scanned_pdf_without_text(monkeypatch) -> None:
    monkeypatch.setattr(build.pdfplumber, "open", _fake_open(["" for _ in range(20)]))

    with pytest.raises(ValueError, match="escaneado"):
        build.extract_terms(Path("fake.pdf"))


def test_write_outputs_writes_a_sorted_txt_and_a_json_with_categories(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(build, "_TERMS_TXT", tmp_path / "terminos_dentales.txt")
    monkeypatch.setattr(build, "_TERMS_JSON", tmp_path / "terminos_dentales.json")

    build.write_outputs({"caries": None, "absceso": "ejemplo"})

    lines = (tmp_path / "terminos_dentales.txt").read_text(encoding="utf-8").splitlines()
    assert lines == ["absceso", "caries"]

    import json

    data = json.loads((tmp_path / "terminos_dentales.json").read_text(encoding="utf-8"))
    assert data == {"caries": None, "absceso": "ejemplo"}


def test_is_noise_rejects_a_spaced_out_heading() -> None:
    assert build._is_noise("B I B L I O G R A F I A") is True


def test_is_noise_accepts_a_normal_multi_word_term() -> None:
    assert build._is_noise("ACEROS INOXIDABLES") is False
