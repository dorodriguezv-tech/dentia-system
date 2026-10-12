import io
from decimal import Decimal

from pypdf import PdfReader

from app.modules.billing.pdf import FOOTER_TEXT, AllocationRow, build_receipt_pdf


def test_build_receipt_pdf_returns_a_valid_pdf_with_brand_footer() -> None:
    pdf_bytes = build_receipt_pdf(
        clinic_name="Clinica Dental Demo",
        logo=None,
        patient_name="Jose Perez",
        payment_id="abc12345",
        method_label="Efectivo",
        reference=None,
        received_at_label="05/10/2026",
        amount=Decimal("500.00"),
        allocations=[AllocationRow(description="Resina 36", amount=Decimal("500.00"))],
        unallocated_amount=Decimal("0"),
        received_by_name="Admin",
    )

    assert pdf_bytes.startswith(b"%PDF")
    # W3 (docs/CAMBIOS_WEB_MARCA.md): pie de pagina de marca en todos los PDF.
    text = PdfReader(io.BytesIO(pdf_bytes)).pages[0].extract_text()
    assert FOOTER_TEXT in text


def test_build_receipt_pdf_skips_unreadable_logo_without_crashing() -> None:
    pdf_bytes = build_receipt_pdf(
        clinic_name="Clinica Dental Demo",
        logo=(b"not a real image", "image/svg+xml"),
        patient_name="Jose Perez",
        payment_id="abc12345",
        method_label="Efectivo",
        reference=None,
        received_at_label="05/10/2026",
        amount=Decimal("500.00"),
        allocations=[],
        unallocated_amount=Decimal("0"),
        received_by_name="Admin",
    )
    assert pdf_bytes.startswith(b"%PDF")
