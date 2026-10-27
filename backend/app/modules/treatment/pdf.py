"""Generacion del PDF del presupuesto (CLAUDE.md Fase 7: "PDF del presupuesto con el
logo de la clinica"). Funcion pura de renderizado: no toca la BD, recibe todo ya
resuelto por el servicio/router para poder probarse sin fixtures de base de datos."""

import io
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.modules.documents.pdf_header import PdfHeaderInfo, place_and_date_label


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


# W3 (docs/CAMBIOS_WEB_MARCA.md): pie de pagina de marca en todos los PDF generados.
FOOTER_TEXT = "Generado con DENT-IA · Sistema Inteligente de Gestión Odontológica"
_FOOTER_COLOR = colors.HexColor("#4F6676")


def _draw_footer(canvas: Canvas, doc: SimpleDocTemplate) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(_FOOTER_COLOR)
    canvas.drawCentredString(doc.pagesize[0] / 2, 12 * mm, FOOTER_TEXT)
    canvas.restoreState()


def _logo_flowable(logo: tuple[bytes, str] | None) -> Image | None:
    if logo is None:
        return None
    logo_bytes, _content_type = logo
    try:
        return Image(io.BytesIO(logo_bytes), width=12 * mm, height=12 * mm, kind="proportional")
    except Exception:
        # El logo puede ser SVG (branding/document_settings lo aceptan); reportlab
        # solo dibuja rasters. Se omite en vez de romper la generacion del PDF.
        return None


def _header_table(header: PdfHeaderInfo, styles: dict[str, Any]) -> Table:
    """Logo izquierdo + titulo institucional + logo derecho (Fase A, decision
    confirmada #2: un unico par de logos para todos los documentos imprimibles)."""
    title_paragraph = Paragraph(header.institutional_title, styles["Heading1"])
    left_cell = _logo_flowable(header.logo_left) or ""
    right_cell = _logo_flowable(header.logo_right) or ""
    table = Table(
        [[left_cell, title_paragraph, right_cell]],
        colWidths=[16 * mm, None, 16 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("ALIGN", (2, 0), (2, 0), "RIGHT"),
            ]
        )
    )
    return table


def build_budget_pdf(
    *,
    header: PdfHeaderInfo,
    primary_color_hex: str,
    patient_name: str,
    plan_title: str,
    plan_status_label: str,
    created_at_label: str,
    phases: list[BudgetPhaseRow],
    grand_total: Decimal,
    acceptance_label: str | None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=14 * mm, bottomMargin=16 * mm)
    styles = getSampleStyleSheet()
    story = []

    story.append(_header_table(header, styles))
    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph(place_and_date_label(header.place_label, created_at_label), styles["Normal"])
    )
    story.append(Spacer(1, 3 * mm))

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

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return buffer.getvalue()
