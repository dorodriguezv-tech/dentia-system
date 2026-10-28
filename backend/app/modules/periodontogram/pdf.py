"""PDF del Periodontograma completo (Fase G, docs/clinica -- ultimo slice del
proyecto). Mismo motor que odontological_history/pediatric_history/
endodontic_history (xhtml2pdf) y mismo encabezado compartido
(documents/pdf_header.py). Funcion pura: no toca la BD, recibe todo ya
resuelto por service.py para poder probarse sin fixtures.

Decision documentada (CLAUDE.md sec. 7, mismo criterio que el odontograma de
endodoncia de la Fase F listado como texto): la cuadricula de sondeo por
pieza/sitio se representa como una TABLA DE DATOS clara, no se replica el
dibujo grafico del odontograma de 32 piezas dentro de este PDF basado en
texto/xhtml2pdf -- el dibujo interactivo vive en el frontend."""

import html
import io
from dataclasses import dataclass, field

from xhtml2pdf import pisa

from app.modules.documents.pdf import FOOTER_TEXT
from app.modules.documents.pdf_header import PdfHeaderInfo, place_and_date_label, render_header_html


class PdfRenderError(Exception):
    """xhtml2pdf no pudo generar el PDF del Periodontograma."""


@dataclass
class PeriodontogramPdfData:
    header: PdfHeaderInfo
    date_label: str
    patient_full_name: str
    patient_expediente_number: str
    probing_rows: list[str] = field(default_factory=list)
    tooth_measurement_rows: list[str] = field(default_factory=list)
    plaque_index_rows: list[str] = field(default_factory=list)
    gingival_index_rows: list[str] = field(default_factory=list)
    plaque_summary_row: str | None = None
    gingival_summary_row: str | None = None
    occlusal_rows: list[str] = field(default_factory=list)
    observaciones_rows: list[str] = field(default_factory=list)


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


def build_periodontogram_pdf(data: PeriodontogramPdfData) -> bytes:
    header_html = render_header_html(data.header)
    place_date_html = place_and_date_label(data.header.place_label, data.date_label)

    patient_pairs = [
        ("Expediente", data.patient_expediente_number),
        ("Nombre", data.patient_full_name),
    ]

    summary_rows = [row for row in (data.plaque_summary_row, data.gingival_summary_row) if row]

    sections = "".join(
        [
            _section("Datos del paciente", _kv_table(patient_pairs)),
            _section(
                "Sondeo periodontal (6 sitios por pieza)",
                _bullet_list(data.probing_rows),
            ),
            _section(
                "Movilidad y furcacion por pieza",
                _bullet_list(data.tooth_measurement_rows),
            ),
            _section(
                "Indices calculados (encuentro mas reciente con datos)",
                _bullet_list(summary_rows),
            ),
            _section(
                "Indice de placa dentobacteriana -- detalle", _bullet_list(data.plaque_index_rows)
            ),
            _section("Indice gingival -- detalle", _bullet_list(data.gingival_index_rows)),
            _section("Tablas de oclusion (contactos marcados)", _bullet_list(data.occlusal_rows)),
            _section("Observaciones", _bullet_list(data.observaciones_rows)),
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
            PERIODONTOGRAMA
        </h2>
        <p style="margin:0 0 8px;">{html.escape(place_date_html)}</p>
        {sections}
    </body>
    </html>
    """

    buffer = io.BytesIO()
    result = pisa.CreatePDF(document, dest=buffer)
    if result.err:
        raise PdfRenderError("No se pudo generar el PDF del Periodontograma")
    return buffer.getvalue()
