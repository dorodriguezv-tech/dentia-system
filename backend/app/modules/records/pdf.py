"""PDF de la Historia Clinica General completa (paciente + heredofamiliares +
antecedentes personales patologicos/no patologicos + aparatos y sistemas +
alergias/medicamentos/signos vitales ya existentes + odontograma de diagnostico
actual tal cual existe hoy, SIN rediseñarlo -- eso es la Fase B). Mismo motor
que documents/pdf.py (xhtml2pdf) y mismo encabezado compartido
(documents/pdf_header.py). Funcion pura: no toca la BD, recibe todo ya resuelto
por el router para poder probarse sin fixtures."""

import html
import io
from dataclasses import dataclass, field
from typing import Any

from xhtml2pdf import pisa

from app.modules.documents.pdf import FOOTER_TEXT
from app.modules.documents.pdf_header import PdfHeaderInfo, place_and_date_label, render_header_html


class PdfRenderError(Exception):
    """xhtml2pdf no pudo generar el PDF de la Historia Clinica General."""


@dataclass
class GeneralHistoryPdfData:
    header: PdfHeaderInfo
    date_label: str
    patient_full_name: str
    patient_expediente_number: str
    patient_age: int
    patient_sex_label: str
    patient_extra_fields: dict[str, str] = field(default_factory=dict)
    family_history_rows: list[dict[str, Any]] = field(default_factory=list)
    pathological_rows: list[str] = field(default_factory=list)
    non_pathological_rows: list[str] = field(default_factory=list)
    systems_review_rows: list[str] = field(default_factory=list)
    allergy_rows: list[str] = field(default_factory=list)
    medication_rows: list[str] = field(default_factory=list)
    vital_signs_rows: list[str] = field(default_factory=list)
    odontogram_rows: list[str] = field(default_factory=list)


def _kv_table(pairs: list[tuple[str, str]]) -> str:
    if not pairs:
        return "<p>Sin datos capturados.</p>"
    rows = "".join(
        f"<tr><td style='font-weight:bold;padding:2px 8px 2px 0;white-space:nowrap;'>"
        f"{html.escape(label)}</td><td style='padding:2px 0;'>{html.escape(str(value))}</td></tr>"
        for label, value in pairs
    )
    return f"<table style='width:100%;font-size:9pt;'>{rows}</table>"


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "<p>Sin datos capturados.</p>"
    rows = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    return f"<ul style='margin:4px 0 0 16px;padding:0;font-size:9pt;'>{rows}</ul>"


def _section(title: str, body_html: str) -> str:
    return (
        f"<h3 style='font-size:11pt;margin:14px 0 4px;border-bottom:1px solid #999;"
        f"padding-bottom:2px;'>{html.escape(title)}</h3>{body_html}"
    )


def build_general_history_pdf(data: GeneralHistoryPdfData) -> bytes:
    header_html = render_header_html(data.header)
    place_date_html = place_and_date_label(data.header.place_label, data.date_label)

    patient_pairs = [
        ("Expediente", data.patient_expediente_number),
        ("Nombre", data.patient_full_name),
        ("Edad", f"{data.patient_age} anos"),
        ("Sexo", data.patient_sex_label),
        *data.patient_extra_fields.items(),
    ]

    sections = "".join(
        [
            _section("Datos del paciente", _kv_table(patient_pairs)),
            _section(
                "Antecedentes heredofamiliares",
                _bullet_list(
                    [
                        f"{row['relationship']}: {row['status']} -- "
                        + (
                            ", ".join(row["conditions"])
                            if row["conditions"]
                            else "sin condiciones marcadas"
                        )
                        for row in data.family_history_rows
                    ]
                ),
            ),
            _section(
                "Antecedentes personales patologicos",
                _bullet_list(data.pathological_rows),
            ),
            _section(
                "Antecedentes personales no patologicos",
                _bullet_list(data.non_pathological_rows),
            ),
            _section(
                "Interrogatorio por aparatos y sistemas",
                _bullet_list(data.systems_review_rows),
            ),
            _section("Alergias", _bullet_list(data.allergy_rows)),
            _section("Medicamentos", _bullet_list(data.medication_rows)),
            _section("Signos vitales", _bullet_list(data.vital_signs_rows)),
            _section(
                "Odontograma de diagnostico actual",
                _bullet_list(data.odontogram_rows),
            ),
        ]
    )

    document = f"""
    <html>
    <head>
    <meta charset="utf-8" />
    <style>
        @page {{
            size: letter;
            @frame content_frame {{
                top: 12mm; left: 16mm; right: 16mm; bottom: 15mm;
            }}
            @frame footer_frame {{
                -pdf-frame-content: footer_content;
                bottom: 7mm; left: 16mm; right: 16mm; height: 8mm;
            }}
        }}
    </style>
    </head>
    <body style="font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.3;">
        <div id="footer_content" style="text-align:center;color:#4F6676;font-size:7pt;">
            {FOOTER_TEXT}
        </div>
        {header_html}
        <h2 style="text-align:center;font-size:13pt;margin:2px 0 6px;">
            HISTORIA CLINICA GENERAL
        </h2>
        <p style="margin:0 0 8px;">{html.escape(place_date_html)}</p>
        {sections}
    </body>
    </html>
    """

    buffer = io.BytesIO()
    result = pisa.CreatePDF(document, dest=buffer)
    if result.err:
        raise PdfRenderError("No se pudo generar el PDF de la Historia Clinica General")
    return buffer.getvalue()
