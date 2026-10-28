"""PDF de la nota de evolucion (docs/clinica/nota_evolucion.pdf) -- Fase D.

`ClinicalNote` ya es conceptualmente la nota de evolucion (SOAP + los campos
complementarios agregados en esta fase); este modulo solo la imprime. Usa
xhtml2pdf (como `documents/pdf.py`) porque es, igual que un consentimiento,
un documento de texto corrido de una sola hoja -- sin tablas de layout
preciso."""

import html
import io

from xhtml2pdf import pisa

from app.modules.documents.pdf_header import PdfHeaderInfo, place_and_date_label, render_header_html

FOOTER_TEXT = "Generado con DENT-IA · Sistema Inteligente de Gestión Odontológica"


class PdfRenderError(Exception):
    """xhtml2pdf no pudo generar el PDF."""


def _field(label: str, value: str | None) -> str:
    if not value:
        return ""
    escaped_label = html.escape(label)
    escaped_value = html.escape(value)
    return f'<p style="margin:0 0 6px;"><strong>{escaped_label}:</strong> {escaped_value}</p>'


def build_clinical_note_pdf(
    *,
    header: PdfHeaderInfo,
    date_label: str,
    patient_name: str,
    patient_birth_date_label: str,
    patient_age: int,
    patient_sex_label: str,
    expediente_number: str,
    professional_name: str,
    status_label: str,
    version: int,
    talla: str,
    peso: str,
    imc: str,
    temperatura: str,
    tension: str,
    soap_s: str | None,
    soap_o: str | None,
    soap_a: str | None,
    soap_p: str | None,
    free_text: str | None,
    interrogatorio: str | None,
    medicamentos: str | None,
    estudios_radiograficos: str | None,
    descripcion_procedimiento: str | None,
    pronostico_evolucion: str | None,
    indicaciones: str | None,
    plan_proxima_cita: str | None,
    fecha_proxima_cita: str | None,
    evaluacion_actualizacion: str | None,
) -> bytes:
    header_html = render_header_html(header)
    place_date_text = html.escape(place_and_date_label(header.place_label, date_label))

    body = "".join(
        [
            _field("Interrogatorio", interrogatorio),
            _field("Subjetivo", soap_s),
            _field("Objetivo", soap_o),
            _field("Analisis", soap_a),
            _field("Plan", soap_p),
            _field("Medicamentos", medicamentos),
            _field("Estudios radiograficos", estudios_radiograficos),
            _field("Descripcion del procedimiento", descripcion_procedimiento),
            _field("Pronostico / evolucion", pronostico_evolucion),
            _field("Notas adicionales", free_text),
            _field("Indicaciones", indicaciones),
            _field("Plan para proxima cita", plan_proxima_cita),
            _field("Fecha de proxima cita", fecha_proxima_cita),
            _field("Evaluacion / actualizacion", evaluacion_actualizacion),
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
        <h2 style="text-align:center;font-size:13pt;margin:2px 0 10px;">NOTA DE EVOLUCION</h2>
        <p style="margin:0 0 8px;">{place_date_text}</p>
        <p style="margin:0 0 4px;">
            <strong>Paciente:</strong> {html.escape(patient_name)} &nbsp;
            <strong>Expediente:</strong> {html.escape(expediente_number)}
        </p>
        <p style="margin:0 0 4px;">
            <strong>Fecha de nacimiento:</strong> {html.escape(patient_birth_date_label)} &nbsp;
            <strong>Edad:</strong> {patient_age} &nbsp;
            <strong>Sexo:</strong> {html.escape(patient_sex_label)}
        </p>
        <p style="margin:0 0 8px;">
            <strong>Signos vitales:</strong> Talla {talla} m, Peso {peso} kg, IMC {imc},
            Temp {temperatura} °C, T.A. {tension} mmHg
        </p>
        {body}
        <p style="margin:16px 0 0;">
            <strong>Profesional:</strong> {html.escape(professional_name)} &nbsp;
            <strong>Estado:</strong> {html.escape(status_label)} (version {version})
        </p>
    </body>
    </html>
    """

    buffer = io.BytesIO()
    result = pisa.CreatePDF(document, dest=buffer)
    if result.err:
        raise PdfRenderError("No se pudo generar el PDF de la nota de evolucion")
    return buffer.getvalue()
