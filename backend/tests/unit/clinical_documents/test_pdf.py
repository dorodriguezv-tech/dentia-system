import io

from pypdf import PdfReader

from app.modules.clinical_documents.pdf import (
    CounterReferralPdfData,
    PatientHeaderPdfData,
    PrescriptionMedicationRow,
    PrescriptionPdfData,
    ReferralPdfData,
    build_counter_referral_pdf,
    build_prescription_pdf,
    build_referral_pdf,
)
from app.modules.documents.pdf_header import PdfHeaderInfo


def _header(**overrides: object) -> PdfHeaderInfo:
    defaults: dict[str, object] = {
        "institutional_title": "Clinica Dental Demo",
        "place_label": None,
        "logo_left": None,
        "logo_right": None,
    }
    defaults.update(overrides)
    return PdfHeaderInfo(**defaults)  # type: ignore[arg-type]


def _prescription_data(**overrides: object) -> PrescriptionPdfData:
    defaults: dict[str, object] = dict(
        header=_header(),
        date_label="05/10/2026",
        folio="RX-000001",
        patient_name="Jose Perez",
        patient_birth_date_label="20/05/1990",
        patient_age=35,
        patient_sex_label="Masculino",
        allergies_label="No",
        talla="1.70",
        peso="70.0",
        imc="24.2",
        temperatura="36.5",
        tension="120/80",
        diagnostico="Caries en pieza 36",
        medications=[
            PrescriptionMedicationRow(nombre="Amoxicilina 500mg", detalle="Cada 8 horas por 7 dias")
        ],
        professional_name="Dra. Ana Lopez",
        professional_license="1234567",
        clinic_address="Av. Siempre Viva 123",
        clinic_phone="555-1234",
    )
    defaults.update(overrides)
    return PrescriptionPdfData(**defaults)  # type: ignore[arg-type]


def test_build_prescription_pdf_returns_valid_pdf_with_two_copies() -> None:
    pdf_bytes = build_prescription_pdf(_prescription_data())
    assert pdf_bytes.startswith(b"%PDF")

    reader = PdfReader(io.BytesIO(pdf_bytes))
    # Decision confirmada con el usuario: 2 recetas identicas en UNA sola hoja.
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert text.count("RX-000001") == 2
    assert text.count("Amoxicilina 500mg") == 2
    assert "Caries en pieza 36" in text


def test_build_prescription_pdf_with_many_medications_still_fits_one_page() -> None:
    many_meds = [
        PrescriptionMedicationRow(nombre=f"Medicamento {i}", detalle="Indicacion " * 10)
        for i in range(12)
    ]
    pdf_bytes = build_prescription_pdf(_prescription_data(medications=many_meds))
    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) == 1


def _patient_header(**overrides: object) -> PatientHeaderPdfData:
    defaults: dict[str, object] = dict(
        patient_name="Jose Perez",
        patient_address="Calle Falsa 123",
        patient_phone="555-0000",
        talla="1.70",
        peso="70.0",
        imc="24.2",
        temperatura="36.5",
        tension="120/80",
    )
    defaults.update(overrides)
    return PatientHeaderPdfData(**defaults)  # type: ignore[arg-type]


def test_build_referral_pdf_returns_valid_pdf() -> None:
    data = ReferralPdfData(
        patient=_patient_header(),
        diagnosticos="Caries multiple",
        medicamentos_texto="Ninguno",
        alergias_texto="Ninguna",
        tratamientos_texto="Limpieza dental",
        observaciones="Paciente cooperador",
        motivo_interconsulta="Valoracion por endodoncia en pieza 36",
        establecimiento_receptor="Clinica Especializada XYZ",
        dentist_name="Dr. Juan Gomez",
        date_label="05/10/2026",
    )
    pdf_bytes = build_referral_pdf(_header(), data)
    assert pdf_bytes.startswith(b"%PDF")
    text = PdfReader(io.BytesIO(pdf_bytes)).pages[0].extract_text()
    assert "HOJA DE REFERENCIA" in text
    assert "Valoracion por endodoncia en pieza 36" in text
    assert "Clinica Especializada XYZ" in text


def test_build_counter_referral_pdf_returns_valid_pdf() -> None:
    data = CounterReferralPdfData(
        patient=_patient_header(),
        motivo_contrarreferencia="Tratamiento de endodoncia concluido sin complicaciones",
        tratamientos_texto="Endodoncia pieza 36",
        observaciones="Sin datos relevantes",
        motivo_interconsulta_original="Valoracion por endodoncia",
        establecimiento_emisor="Clinica Especializada XYZ",
        dentist_name="Dr. Juan Gomez",
        date_label="05/10/2026",
    )
    pdf_bytes = build_counter_referral_pdf(_header(), data)
    assert pdf_bytes.startswith(b"%PDF")
    text = PdfReader(io.BytesIO(pdf_bytes)).pages[0].extract_text()
    assert "HOJA DE CONTRARREFERENCIA" in text
    assert "Tratamiento de endodoncia concluido sin complicaciones" in text
