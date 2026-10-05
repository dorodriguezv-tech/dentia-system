"""Generacion del PDF del presupuesto (CLAUDE.md Fase 7: "PDF del presupuesto con el
logo de la clinica"). Funcion pura de renderizado: no toca la BD, recibe todo ya
resuelto por el servicio/router para poder probarse sin fixtures de base de datos."""

import io
from dataclasses import dataclass
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


@dataclass
class BudgetItemRow:
    procedure_name: str
    tooth_label: str
    quantity: int
    unit_price: Decimal
    discount: Decimal | None
    subtotal: Decimal


@dataclass
class BudgetPhaseRow:
    name: str
    items: list[BudgetItemRow]
    phase_total: Decimal


def _money(value: Decimal) -> str:
    return f"${value:,.2f}"


def build_budget_pdf(
    *,
    clinic_name: str,
    primary_color_hex: str,
    logo: tuple[bytes, str] | None,
    patient_name: str,
    plan_title: str,
    plan_status_label: str,
    created_at_label: str,
    phases: list[BudgetPhaseRow],
    grand_total: Decimal,
    acceptance_label: str | None,
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
            # dibuja rasters. Se omite en vez de romper la generacion del PDF.
            pass

    story.append(Paragraph(clinic_name, styles["Title"]))
    story.append(Paragraph(f"Presupuesto: {plan_title}", styles["Heading2"]))
    story.append(Paragraph(f"Paciente: {patient_name}", styles["Normal"]))
    story.append(Paragraph(f"Fecha: {created_at_label}", styles["Normal"]))
    story.append(Paragraph(f"Estado: {plan_status_label}", styles["Normal"]))
    story.append(Spacer(1, 8 * mm))

    header_color = colors.HexColor(primary_color_hex)
    for phase in phases:
        story.append(Paragraph(phase.name, styles["Heading3"]))
        data = [["Procedimiento", "Pieza", "Cant.", "Precio unit.", "Descuento", "Subtotal"]]
        for item in phase.items:
            data.append(
                [
                    item.procedure_name,
                    item.tooth_label,
                    str(item.quantity),
                    _money(item.unit_price),
                    _money(item.discount) if item.discount else "-",
                    _money(item.subtotal),
                ]
            )
        table = Table(data, colWidths=[55 * mm, 20 * mm, 15 * mm, 25 * mm, 25 * mm, 25 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), header_color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ]
            )
        )
        story.append(table)
        story.append(Paragraph(f"Total de la fase: {_money(phase.phase_total)}", styles["Normal"]))
        story.append(Spacer(1, 6 * mm))

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(f"<b>Total general: {_money(grand_total)}</b>", styles["Heading2"]))
    if acceptance_label:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(acceptance_label, styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()
