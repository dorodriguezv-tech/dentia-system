"""Generacion de PDF de receta (reportlab/platypus, igual patron que
`treatment/pdf.py`) y de referencia/contrarreferencia (xhtml2pdf, igual
patron que `documents/pdf.py`) -- Fase D (docs/clinica).

Funciones puras: no tocan la BD, reciben todo ya resuelto por el servicio
para poder probarse sin fixtures (mismo criterio que el resto del sistema)."""

import html
import io
from dataclasses import dataclass
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepInFrame,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.modules.documents.pdf_header import PdfHeaderInfo, place_and_date_label, render_header_html

FOOTER_TEXT = "Generado con DENT-IA · Sistema Inteligente de Gestión Odontológica"
_FOOTER_COLOR = colors.HexColor("#4F6676")


# --------------------------------------------------------------------------- receta


@dataclass
class PrescriptionMedicationRow:
    nombre: str
    detalle: str


@dataclass
class PrescriptionPdfData:
    header: PdfHeaderInfo
    date_label: str
    folio: str
    patient_name: str
    patient_birth_date_label: str
    patient_age: int
    patient_sex_label: str
    allergies_label: str
    talla: str
    peso: str
    imc: str
    temperatura: str
    tension: str
    diagnostico: str
    medications: list[PrescriptionMedicationRow]
    professional_name: str
    professional_license: str
    clinic_address: str
    clinic_phone: str


def _draw_footer(canvas: Canvas, doc: SimpleDocTemplate) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(_FOOTER_COLOR)
    canvas.drawCentredString(doc.pagesize[0] / 2, 6 * mm, FOOTER_TEXT)
    canvas.restoreState()


def _logo_flowable(logo: tuple[bytes, str] | None, *, size_mm: float) -> Image | None:
    if logo is None:
        return None
    logo_bytes, _content_type = logo
    try:
        return Image(
            io.BytesIO(logo_bytes), width=size_mm * mm, height=size_mm * mm, kind="proportional"
        )
    except Exception:
        # El logo puede ser SVG; reportlab solo dibuja rasters (mismo criterio que
        # treatment/pdf.py::_logo_flowable) -- se omite en vez de romper el PDF.
        return None


def _block_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("RxTitle", parent=base["Heading2"], fontSize=11, leading=13),
        "normal": ParagraphStyle("RxNormal", parent=base["Normal"], fontSize=8.5, leading=10.5),
        "small": ParagraphStyle("RxSmall", parent=base["Normal"], fontSize=7.5, leading=9),
        "cellHeader": ParagraphStyle(
            "RxCellHeader", parent=base["Normal"], fontSize=8, leading=9.5, textColor=colors.white
        ),
    }


def _prescription_header_table(header: PdfHeaderInfo, styles: dict[str, ParagraphStyle]) -> Table:
    title = Paragraph(html.escape(header.institutional_title), styles["title"])
    left_cell = _logo_flowable(header.logo_left, size_mm=10) or ""
    right_cell = _logo_flowable(header.logo_right, size_mm=10) or ""
    table = Table([[left_cell, title, right_cell]], colWidths=[14 * mm, None, 14 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


def _build_prescription_block(data: PrescriptionPdfData) -> list[Any]:
    styles = _block_styles()
    story: list[Any] = []

    story.append(_prescription_header_table(data.header, styles))
    story.append(
        Paragraph(place_and_date_label(data.header.place_label, data.date_label), styles["small"])
    )
    story.append(Paragraph(f"<b>Folio:</b> {html.escape(data.folio)}", styles["small"]))
    story.append(Spacer(1, 1.5 * mm))

    patient_table = Table(
        [
            [
                Paragraph(f"<b>Paciente:</b> {html.escape(data.patient_name)}", styles["normal"]),
                Paragraph(f"<b>Edad:</b> {data.patient_age}", styles["normal"]),
                Paragraph(f"<b>Sexo:</b> {html.escape(data.patient_sex_label)}", styles["normal"]),
            ],
            [
                Paragraph(
                    f"<b>Fecha de nacimiento:</b> {html.escape(data.patient_birth_date_label)}",
                    styles["normal"],
                ),
                Paragraph(
                    f"<b>Alergias:</b> {html.escape(data.allergies_label)}", styles["normal"]
                ),
                "",
            ],
        ],
        colWidths=[72 * mm, 58 * mm, 40 * mm],
    )
    patient_table.setStyle(
        TableStyle([("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)])
    )
    story.append(patient_table)

    vitals_table = Table(
        [
            [
                Paragraph(f"<b>Talla (m):</b> {data.talla}", styles["small"]),
                Paragraph(f"<b>Peso (kg):</b> {data.peso}", styles["small"]),
                Paragraph(f"<b>IMC:</b> {data.imc}", styles["small"]),
                Paragraph(f"<b>Temp (°C):</b> {data.temperatura}", styles["small"]),
                Paragraph(f"<b>T.A. (mmHg):</b> {data.tension}", styles["small"]),
            ]
        ],
        colWidths=[34 * mm] * 5,
    )
    vitals_table.setStyle(
        TableStyle([("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)])
    )
    story.append(vitals_table)
    story.append(Spacer(1, 1.5 * mm))

    story.append(
        Paragraph(f"<b>Diagnostico:</b> {html.escape(data.diagnostico)}", styles["normal"])
    )
    story.append(Spacer(1, 1.5 * mm))

    med_header = [
        Paragraph("Medicamento", styles["cellHeader"]),
        Paragraph("Indicaciones", styles["cellHeader"]),
    ]
    med_rows = [med_header] + [
        [
            Paragraph(html.escape(m.nombre), styles["small"]),
            Paragraph(html.escape(m.detalle), styles["small"]),
        ]
        for m in data.medications
    ]
    med_table = Table(med_rows, colWidths=[45 * mm, 125 * mm], repeatRows=1)
    med_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F6676")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(med_table)
    story.append(Spacer(1, 3 * mm))

    footer_table = Table(
        [
            [
                Paragraph(
                    "_______________________________<br/>"
                    f"{html.escape(data.professional_name)}<br/>"
                    f"Cedula profesional: {html.escape(data.professional_license or '-')}",
                    styles["small"],
                ),
                Paragraph(
                    f"{html.escape(data.clinic_address or '-')}<br/>"
                    f"Tel: {html.escape(data.clinic_phone or '-')}",
                    styles["small"],
                ),
            ]
        ],
        colWidths=[95 * mm, 75 * mm],
    )
    story.append(footer_table)

    return story


def build_prescription_pdf(data: PrescriptionPdfData) -> bytes:
    """Dos copias IDENTICAS de la misma receta, apiladas en una sola hoja
    carta (decision confirmada con el usuario, ver clinical_documents/models.py
    docstring de Prescription). `KeepInFrame` con mode="shrink" garantiza que
    cada mitad quepa en su marco sin impoter cuantos medicamentos tenga la
    receta -- si el contenido es demasiado largo, se reduce de tamaño en vez
    de desbordar a una tercera hoja."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=8 * mm,
        bottomMargin=10 * mm,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
    )

    block_content = _build_prescription_block(data)
    frame_width = doc.width
    frame_height = 123 * mm

    # Linea punteada al centro: guia de corte entre las dos copias identicas
    # (decision confirmada con el usuario: 2 recetas iguales en una sola hoja).
    cut_line = HRFlowable(width="100%", thickness=0.5, color=colors.grey, dash=(3, 2))

    story = [
        KeepInFrame(frame_width, frame_height, content=list(block_content), mode="shrink"),
        Spacer(1, 3 * mm),
        cut_line,
        Spacer(1, 3 * mm),
        KeepInFrame(frame_width, frame_height, content=list(block_content), mode="shrink"),
    ]

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return buffer.getvalue()


# ------------------------------------------------------- referencia / contrarreferencia


@dataclass
class PatientHeaderPdfData:
    """Encabezado compartido por referencia y contrarreferencia: datos del
    paciente + signos vitales vigentes (autollenados, ver clinical_documents/
    service.py)."""

    patient_name: str
    patient_address: str
    patient_phone: str
    talla: str
    peso: str
    imc: str
    temperatura: str
    tension: str


def _patient_header_html(patient: PatientHeaderPdfData) -> str:
    return f"""
    <p style="margin:0 0 4px;"><strong>Paciente:</strong> {html.escape(patient.patient_name)}</p>
    <p style="margin:0 0 4px;">
        <strong>Domicilio:</strong> {html.escape(patient.patient_address or '-')} &nbsp;
        <strong>Telefono:</strong> {html.escape(patient.patient_phone or '-')}
    </p>
    <p style="margin:0 0 8px;">
        <strong>Signos vitales:</strong>
        Talla {patient.talla} m, Peso {patient.peso} kg, IMC {patient.imc},
        Temp {patient.temperatura} °C, T.A. {patient.tension} mmHg
    </p>
    """


def _field_block(label: str, value: str | None) -> str:
    text = html.escape(value) if value else "-"
    return f'<p style="margin:0 0 6px;"><strong>{html.escape(label)}:</strong> {text}</p>'


@dataclass
class ReferralPdfData:
    patient: PatientHeaderPdfData
    diagnosticos: str | None
    medicamentos_texto: str | None
    alergias_texto: str | None
    tratamientos_texto: str | None
    observaciones: str | None
    motivo_interconsulta: str
    establecimiento_receptor: str
    dentist_name: str
    date_label: str


def build_referral_pdf(header: PdfHeaderInfo, data: ReferralPdfData) -> bytes:
    header_html = render_header_html(header)
    place_date_text = html.escape(place_and_date_label(header.place_label, data.date_label))

    body = "".join(
        [
            _patient_header_html(data.patient),
            _field_block("Diagnostico(s)", data.diagnosticos),
            _field_block("Medicamentos", data.medicamentos_texto),
            _field_block("Alergias", data.alergias_texto),
            _field_block("Tratamientos odontologicos realizados", data.tratamientos_texto),
            _field_block("Observaciones del Cirujano Dentista", data.observaciones),
            _field_block("Motivo de interconsulta", data.motivo_interconsulta),
            _field_block("Establecimiento receptor", data.establecimiento_receptor),
        ]
    )

    document = f"""
    <html>
    <head><meta charset="utf-8" />
    <style>
        @page {{
            size: letter;
            @frame content_frame {{ top: 12mm; left: 16mm; right: 16mm; bottom: 15mm; }}
            @frame footer_frame {{
                -pdf-frame-content: footer_content;
                bottom: 7mm; left: 16mm; right: 16mm; height: 8mm;
            }}
        }}
    </style>
    </head>
    <body style="font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.35;">
        <div id="footer_content" style="text-align:center;color:#4F6676;font-size:7pt;">
            {FOOTER_TEXT}
        </div>
        {header_html}
        <h2 style="text-align:center;font-size:13pt;margin:2px 0 10px;">
            HOJA DE REFERENCIA / INTERCONSULTA
        </h2>
        <p style="margin:0 0 8px;">{place_date_text}</p>
        {body}
        <div style="margin-top:20px;">
            <p style="margin:0 0 30px;">
                _______________________________<br/>
                Nombre y firma del Dentista tratante: {html.escape(data.dentist_name)}
            </p>
            <p style="margin:0;">
                _______________________________<br/>
                Nombre y firma de recibido
            </p>
        </div>
    </body>
    </html>
    """

    return _render_xhtml2pdf(document)


@dataclass
class CounterReferralPdfData:
    patient: PatientHeaderPdfData
    motivo_contrarreferencia: str
    tratamientos_texto: str | None
    observaciones: str | None
    motivo_interconsulta_original: str | None
    establecimiento_emisor: str
    dentist_name: str
    date_label: str


def build_counter_referral_pdf(header: PdfHeaderInfo, data: CounterReferralPdfData) -> bytes:
    header_html = render_header_html(header)
    place_date_text = html.escape(place_and_date_label(header.place_label, data.date_label))

    body = "".join(
        [
            _patient_header_html(data.patient),
            _field_block("Motivo de la contrarreferencia", data.motivo_contrarreferencia),
            _field_block("Tratamientos odontologicos realizados", data.tratamientos_texto),
            _field_block("Observaciones del clinico", data.observaciones),
            _field_block("Motivo de interconsulta (original)", data.motivo_interconsulta_original),
            _field_block("Establecimiento que emite", data.establecimiento_emisor),
        ]
    )

    document = f"""
    <html>
    <head><meta charset="utf-8" />
    <style>
        @page {{
            size: letter;
            @frame content_frame {{ top: 12mm; left: 16mm; right: 16mm; bottom: 15mm; }}
            @frame footer_frame {{
                -pdf-frame-content: footer_content;
                bottom: 7mm; left: 16mm; right: 16mm; height: 8mm;
            }}
        }}
    </style>
    </head>
    <body style="font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.35;">
        <div id="footer_content" style="text-align:center;color:#4F6676;font-size:7pt;">
            {FOOTER_TEXT}
        </div>
        {header_html}
        <h2 style="text-align:center;font-size:13pt;margin:2px 0 10px;">
            HOJA DE CONTRARREFERENCIA
        </h2>
        <p style="margin:0 0 8px;">{place_date_text}</p>
        {body}
        <div style="margin-top:20px;">
            <p style="margin:0 0 30px;">
                _______________________________<br/>
                Nombre y firma del Dentista tratante: {html.escape(data.dentist_name)}
            </p>
            <p style="margin:0;">
                _______________________________<br/>
                Nombre y firma de recibido
            </p>
        </div>
    </body>
    </html>
    """

    return _render_xhtml2pdf(document)


class PdfRenderError(Exception):
    """xhtml2pdf no pudo generar el PDF."""


def _render_xhtml2pdf(document: str) -> bytes:
    from xhtml2pdf import pisa

    buffer = io.BytesIO()
    result = pisa.CreatePDF(document, dest=buffer)
    if result.err:
        raise PdfRenderError("No se pudo generar el PDF del documento")
    return buffer.getvalue()
