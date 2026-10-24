"""Genera el PDF final de un consentimiento (plantilla ya resuelta + firma), con
xhtml2pdf -- a diferencia del presupuesto de la Fase 7 (reportlab/platypus armado a
mano), aqui la plantilla es HTML de verdad (docs/09), asi que se necesita un renderizador
de HTML a PDF. Funcion pura: sin acceso a BD, se prueba sin fixtures."""

import base64
import html
import io
from collections.abc import Mapping

from xhtml2pdf import pisa

from app.modules.documents.rules import render_template


class PdfRenderError(Exception):
    """xhtml2pdf no pudo generar el PDF (HTML invalido en la plantilla)."""


# W3 (docs/CAMBIOS_WEB_MARCA.md): pie de pagina de marca. Va en un @frame estatico de
# xhtml2pdf, fuera de `<div>{body}</div>` (el contenido firmado que se hashea), para
# no mezclarse visualmente con lo que el paciente/tutor efectivamente firmo.
FOOTER_TEXT = "Generado con DENT-IA · Sistema Inteligente de Gestión Odontológica"

# A peticion del operador: el logo se veia inmenso y centrado, empujando el
# contenido a una segunda hoja -- pequeno y a la izquierda en todos los PDF del
# sistema (ver tambien treatment/pdf.py y billing/pdf.py).
LOGO_MAX_HEIGHT_PX = 28
LOGO_MAX_WIDTH_PX = 90


def _logo_html(logo: tuple[bytes, str] | None) -> str:
    if logo is None:
        return ""
    logo_bytes, logo_content_type = logo
    if logo_content_type == "image/svg+xml":
        return ""
    logo_b64 = base64.b64encode(logo_bytes).decode()
    return (
        f'<img src="data:{logo_content_type};base64,{logo_b64}" '
        f'style="max-height:{LOGO_MAX_HEIGHT_PX}px;max-width:{LOGO_MAX_WIDTH_PX}px;" />'
    )


def build_consent_pdf(
    *,
    template_name: str,
    html_content: str,
    variables: Mapping[str, object],
    signature_png: bytes,
    clinic_name: str,
    patient_name: str,
    signer_name: str,
    signer_relationship_label: str,
    signed_at_label: str,
    logo: tuple[bytes, str] | None = None,
) -> bytes:
    body = render_template(html_content, variables)
    signature_b64 = base64.b64encode(signature_png).decode()
    logo_html = _logo_html(logo)

    # Margenes y tipografia compactos (a peticion del operador: "todo en una
    # hoja") -- un consentimiento tipico (2-3 parrafos) cabe completo en carta.
    # Un texto de plantilla deliberadamente muy largo si puede seguir
    # ocupando una segunda hoja; xhtml2pdf pagina automaticamente en ese caso.
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
    <body style="font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.35;">
        <div id="footer_content" style="text-align:center;color:#4F6676;font-size:7pt;">
            {FOOTER_TEXT}
        </div>
        <table style="width:100%;border-collapse:collapse;margin-bottom:6px;">
            <tr>
                <td style="width:100px;vertical-align:middle;">{logo_html}</td>
                <td style="vertical-align:middle;text-align:left;">
                    <div style="font-size:10pt;font-weight:bold;">{html.escape(clinic_name)}</div>
                </td>
            </tr>
        </table>
        <h2 style="text-align:center;font-size:13pt;margin:2px 0 10px;">
            {html.escape(template_name.upper())}
        </h2>
        <p style="margin:0 0 8px;"><strong>Paciente:</strong> {html.escape(patient_name)}</p>
        <div>{body}</div>
        <div style="margin-top:24px;">
            <p style="margin:0 0 4px;">
                Firma de: {html.escape(signer_name)} ({html.escape(signer_relationship_label)})
            </p>
            <img src="data:image/png;base64,{signature_b64}"
                 style="max-height:90px;max-width:90px;" />
            <p style="margin:4px 0 0;">Fecha y hora: {html.escape(signed_at_label)}</p>
        </div>
    </body>
    </html>
    """

    buffer = io.BytesIO()
    result = pisa.CreatePDF(document, dest=buffer)
    if result.err:
        raise PdfRenderError("No se pudo generar el PDF del consentimiento")
    return buffer.getvalue()
