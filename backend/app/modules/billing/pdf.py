"""Generacion del recibo de pago en PDF (CLAUDE.md Fase 10: "recibo PDF con logo").
Funcion pura de renderizado: no toca la BD, recibe todo ya resuelto por el servicio/
router para poder probarse sin fixtures de base de datos. A diferencia del
consentimiento (Fase 9, plantilla HTML con xhtml2pdf), un recibo es un documento
estructurado fijo: se arma con reportlab/platypus, igual que el presupuesto (Fase 7)."""

import io
from dataclasses import dataclass
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


@dataclass
class AllocationRow:
    description: str
    amount: Decimal


def _money(value: Decimal) -> str:
    return f"${value:,.2f}"


def build_receipt_pdf(
    *,
    clinic_name: str,
    logo: tuple[bytes, str] | None,
    patient_name: str,
    payment_id: str,
    method_label: str,
    reference: str | None,
    received_at_label: str,
    amount: Decimal,
    allocations: list[AllocationRow],
    unallocated_amount: Decimal,
    received_by_name: str,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    story = []

    if logo is not None:
        logo_bytes, _content_type = logo
        try:
            story.append(
                Image(io.BytesIO(logo_bytes), width=30 * mm, height=30 * mm, kind="proportional")
            )
            story.append(Spacer(1, 4 * mm))
        except Exception:
            # El logo puede ser SVG (branding lo acepta, Fase 2); reportlab solo
            # dibuja rasters. Se omite en vez de romper la generacion del recibo.
            pass

    story.append(Paragraph(clinic_name, styles["Title"]))
    story.append(Paragraph(f"Recibo de pago #{payment_id[:8]}", styles["Heading2"]))
    story.append(Paragraph(f"Paciente: {patient_name}", styles["Normal"]))
    story.append(Paragraph(f"Fecha: {received_at_label}", styles["Normal"]))
    story.append(Paragraph(f"Metodo: {method_label}", styles["Normal"]))
    if reference:
        story.append(Paragraph(f"Referencia: {reference}", styles["Normal"]))
    story.append(Paragraph(f"Recibido por: {received_by_name}", styles["Normal"]))
    story.append(Spacer(1, 8 * mm))

    if allocations:
        data = [["Aplicado a", "Monto"]]
        for row in allocations:
            data.append([row.description, _money(row.amount)])
        table = Table(data, colWidths=[110 * mm, 40 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2bb3a3")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 6 * mm))

    if unallocated_amount > 0:
        story.append(
            Paragraph(
                f"Anticipo (sin aplicar a un cargo): {_money(unallocated_amount)}", styles["Normal"]
            )
        )
        story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(f"<b>Total pagado: {_money(amount)}</b>", styles["Heading2"]))

    doc.build(story)
    return buffer.getvalue()
