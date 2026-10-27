import io
from decimal import Decimal

from pypdf import PdfReader

from app.modules.documents.pdf_header import PdfHeaderInfo
from app.modules.treatment.pdf import FOOTER_TEXT, BudgetItemRow, BudgetPhaseRow, build_budget_pdf


def _header(**overrides: object) -> PdfHeaderInfo:
    defaults: dict[str, object] = {
        "institutional_title": "Clinica Dental Demo",
        "place_label": None,
        "logo_left": None,
        "logo_right": None,
    }
    defaults.update(overrides)
    return PdfHeaderInfo(**defaults)  # type: ignore[arg-type]


def test_build_budget_pdf_returns_a_valid_pdf_document() -> None:
    phase = BudgetPhaseRow(
        name="Fase 1",
        items=[
            BudgetItemRow(
                procedure_name="Resina oclusal",
                tooth_label="Pieza 36 (O)",
                quantity=1,
                unit_price=Decimal("500.00"),
                discount=None,
                subtotal=Decimal("500.00"),
            )
        ],
        phase_total=Decimal("500.00"),
    )

    pdf_bytes = build_budget_pdf(
        header=_header(),
        primary_color_hex="#2BB3A3",
        patient_name="Jose Perez",
        plan_title="Plan general",
        plan_status_label="Presentado",
        created_at_label="05/10/2026",
        phases=[phase],
        grand_total=Decimal("500.00"),
        acceptance_label=None,
    )

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500
    # W3 (docs/CAMBIOS_WEB_MARCA.md): pie de pagina de marca en todos los PDF.
    text = PdfReader(io.BytesIO(pdf_bytes)).pages[0].extract_text()
    assert FOOTER_TEXT in text


def test_build_budget_pdf_skips_unreadable_logo_without_crashing() -> None:
    pdf_bytes = build_budget_pdf(
        header=_header(logo_left=(b"not a real image", "image/svg+xml")),
        primary_color_hex="#2BB3A3",
        patient_name="Jose Perez",
        plan_title="Plan general",
        plan_status_label="Borrador",
        created_at_label="05/10/2026",
        phases=[],
        grand_total=Decimal("0"),
        acceptance_label=None,
    )
    assert pdf_bytes.startswith(b"%PDF")


def test_build_budget_pdf_shows_institutional_title_and_place() -> None:
    """Fase A (rediseno del expediente, docs/clinica): el encabezado ahora trae
    titulo institucional (no solo clinic_name) y la linea "Lugar y fecha"."""
    pdf_bytes = build_budget_pdf(
        header=_header(
            institutional_title="Clinica Odontologica Escuela Militar",
            place_label="Ciudad de Mexico",
        ),
        primary_color_hex="#2BB3A3",
        patient_name="Jose Perez",
        plan_title="Plan general",
        plan_status_label="Presentado",
        created_at_label="05/10/2026",
        phases=[],
        grand_total=Decimal("0"),
        acceptance_label=None,
    )
    text = PdfReader(io.BytesIO(pdf_bytes)).pages[0].extract_text()
    assert "Clinica Odontologica Escuela Militar" in text
    assert "Lugar y fecha: Ciudad de Mexico a 05/10/2026" in text
