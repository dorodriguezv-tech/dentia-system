import io

from PIL import Image
from pypdf import PdfReader

from app.modules.documents.pdf import FOOTER_TEXT, build_consent_pdf
from app.modules.documents.pdf_header import PdfHeaderInfo


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (100, 40), (10, 10, 10)).save(buffer, format="PNG")
    return buffer.getvalue()


def _header(**overrides: object) -> PdfHeaderInfo:
    defaults: dict[str, object] = {
        "institutional_title": "Clinica de prueba",
        "place_label": None,
        "logo_left": None,
        "logo_right": None,
    }
    defaults.update(overrides)
    return PdfHeaderInfo(**defaults)  # type: ignore[arg-type]


def test_build_consent_pdf_returns_valid_pdf_bytes() -> None:
    pdf = build_consent_pdf(
        template_name="Consentimiento general",
        html_content="<p>Autorizo el procedimiento en la pieza {{paciente.nombre}}.</p>",
        variables={"paciente": {"nombre": "Jose Perez"}},
        signature_png=_png_bytes(),
        header=_header(),
        patient_name="Jose Perez",
        signer_name="Jose Perez",
        signer_relationship_label="Paciente",
        signed_at_label="05/10/2026 10:00",
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500
    # W3 (docs/CAMBIOS_WEB_MARCA.md): pie de pagina de marca, fuera del contenido firmado.
    text = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    assert FOOTER_TEXT in text
    # A peticion del operador: titulo en mayusculas y nombre del paciente por
    # default, sin depender de que la plantilla de la clinica lo incluya.
    assert "CONSENTIMIENTO GENERAL" in text
    assert "Jose Perez" in text


def test_build_consent_pdf_without_logo_does_not_crash() -> None:
    pdf = build_consent_pdf(
        template_name="General",
        html_content="<p>Texto simple</p>",
        variables={},
        signature_png=_png_bytes(),
        header=_header(),
        patient_name="Ana Lopez",
        signer_name="Ana",
        signer_relationship_label="Tutor",
        signed_at_label="05/10/2026 10:00",
    )
    assert pdf.startswith(b"%PDF")


def test_build_consent_pdf_with_logo() -> None:
    pdf = build_consent_pdf(
        template_name="General",
        html_content="<p>Texto</p>",
        variables={},
        signature_png=_png_bytes(),
        header=_header(logo_left=(_png_bytes(), "image/png")),
        patient_name="Ana Lopez",
        signer_name="Ana",
        signer_relationship_label="Paciente",
        signed_at_label="05/10/2026 10:00",
    )
    assert pdf.startswith(b"%PDF")


def test_build_consent_pdf_with_both_logos_institutional_title_and_place() -> None:
    """Fase A (rediseno del expediente, docs/clinica): el encabezado ahora trae
    2 logos + titulo institucional + "Lugar y fecha", no solo 1 logo + nombre
    comercial."""
    pdf = build_consent_pdf(
        template_name="General",
        html_content="<p>Texto</p>",
        variables={},
        signature_png=_png_bytes(),
        header=_header(
            institutional_title="Clinica Odontologica Escuela Militar",
            place_label="Ciudad de Mexico",
            logo_left=(_png_bytes(), "image/png"),
            logo_right=(_png_bytes(), "image/png"),
        ),
        patient_name="Ana Lopez",
        signer_name="Ana",
        signer_relationship_label="Paciente",
        signed_at_label="05/10/2026 10:00",
        date_label="05/10/2026",
    )
    assert pdf.startswith(b"%PDF")
    text = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    assert "Clinica Odontologica Escuela Militar" in text
    assert "Lugar y fecha: Ciudad de Mexico a 05/10/2026" in text
