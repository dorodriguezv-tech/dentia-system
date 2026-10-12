import io
from decimal import Decimal

from pypdf import PdfReader

from app.modules.treatment.pdf import FOOTER_TEXT, BudgetItemRow, BudgetPhaseRow, build_budget_pdf


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
        clinic_name="Clinica Dental Demo",
        primary_color_hex="#2BB3A3",
        logo=None,
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
        clinic_name="Clinica Dental Demo",
        primary_color_hex="#2BB3A3",
        logo=(b"not a real image", "image/svg+xml"),
        patient_name="Jose Perez",
        plan_title="Plan general",
        plan_status_label="Borrador",
        created_at_label="05/10/2026",
        phases=[],
        grand_total=Decimal("0"),
        acceptance_label=None,
    )
    assert pdf_bytes.startswith(b"%PDF")
