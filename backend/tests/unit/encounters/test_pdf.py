import io

from pypdf import PdfReader

from app.modules.documents.pdf_header import PdfHeaderInfo
from app.modules.encounters.pdf import build_clinical_note_pdf


def _header(**overrides: object) -> PdfHeaderInfo:
    defaults: dict[str, object] = {
        "institutional_title": "Clinica Dental Demo",
        "place_label": None,
        "logo_left": None,
        "logo_right": None,
    }
    defaults.update(overrides)
    return PdfHeaderInfo(**defaults)  # type: ignore[arg-type]


def _base_kwargs(**overrides: object) -> dict[str, object]:
    defaults: dict[str, object] = dict(
        header=_header(),
        date_label="05/10/2026",
        patient_name="Jose Perez",
        patient_birth_date_label="20/05/1990",
        patient_age=35,
        patient_sex_label="Masculino",
        expediente_number="EXP-0001",
        professional_name="Dra. Ana Lopez",
        status_label="Finalizada",
        version=1,
        talla="1.70",
        peso="70.0",
        imc="24.2",
        temperatura="36.5",
        tension="120/80",
        soap_s="Dolor en pieza 36",
        soap_o="Caries visible",
        soap_a="Caries profunda",
        soap_p="Obturacion",
        free_text=None,
        interrogatorio="Sin antecedentes relevantes",
        medicamentos=None,
        estudios_radiograficos="Radiografia periapical normal",
        descripcion_procedimiento="Obturacion con resina",
        pronostico_evolucion="Favorable",
        indicaciones="Evitar alimentos duros",
        plan_proxima_cita="Control en 1 mes",
        fecha_proxima_cita="2026-11-05",
        evaluacion_actualizacion=None,
    )
    defaults.update(overrides)
    return defaults


def test_build_clinical_note_pdf_returns_valid_pdf() -> None:
    pdf_bytes = build_clinical_note_pdf(**_base_kwargs())
    assert pdf_bytes.startswith(b"%PDF")
    text = PdfReader(io.BytesIO(pdf_bytes)).pages[0].extract_text()
    assert "NOTA DE EVOLUCION" in text
    assert "Obturacion con resina" in text
    assert "Evitar alimentos duros" in text


def test_build_clinical_note_pdf_omits_empty_fields() -> None:
    pdf_bytes = build_clinical_note_pdf(**_base_kwargs(medicamentos=None, free_text=None))
    text = PdfReader(io.BytesIO(pdf_bytes)).pages[0].extract_text()
    assert "Medicamentos:" not in text
