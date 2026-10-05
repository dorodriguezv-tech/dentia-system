import io

from PIL import Image

from app.modules.documents.pdf import build_consent_pdf


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (100, 40), (10, 10, 10)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_build_consent_pdf_returns_valid_pdf_bytes() -> None:
    pdf = build_consent_pdf(
        html_content="<p>Autorizo el procedimiento en la pieza {{paciente.nombre}}.</p>",
        variables={"paciente": {"nombre": "Jose Perez"}},
        signature_png=_png_bytes(),
        clinic_name="Clinica de prueba",
        signer_name="Jose Perez",
        signer_relationship_label="Paciente",
        signed_at_label="05/10/2026 10:00",
        logo=None,
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500


def test_build_consent_pdf_without_logo_does_not_crash() -> None:
    pdf = build_consent_pdf(
        html_content="<p>Texto simple</p>",
        variables={},
        signature_png=_png_bytes(),
        clinic_name="Clinica",
        signer_name="Ana",
        signer_relationship_label="Tutor",
        signed_at_label="05/10/2026 10:00",
        logo=None,
    )
    assert pdf.startswith(b"%PDF")


def test_build_consent_pdf_with_logo() -> None:
    pdf = build_consent_pdf(
        html_content="<p>Texto</p>",
        variables={},
        signature_png=_png_bytes(),
        clinic_name="Clinica",
        signer_name="Ana",
        signer_relationship_label="Paciente",
        signed_at_label="05/10/2026 10:00",
        logo=(_png_bytes(), "image/png"),
    )
    assert pdf.startswith(b"%PDF")
