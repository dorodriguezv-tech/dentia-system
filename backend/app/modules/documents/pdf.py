"""Genera el PDF final de un consentimiento (plantilla ya resuelta + firma), con
xhtml2pdf -- a diferencia del presupuesto de la Fase 7 (reportlab/platypus armado a
mano), aqui la plantilla es HTML de verdad (docs/09), asi que se necesita un renderizador
de HTML a PDF. Funcion pura: sin acceso a BD, se prueba sin fixtures."""

import base64
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


def build_consent_pdf(
    *,
    html_content: str,
    variables: Mapping[str, object],
    signature_png: bytes,
    clinic_name: str,
    signer_name: str,
    signer_relationship_label: str,
    signed_at_label: str,
    logo: tuple[bytes, str] | None = None,
) -> bytes:
    body = render_template(html_content, variables)
    signature_b64 = base64.b64encode(signature_png).decode()

    logo_html = ""
    if logo is not None:
        logo_bytes, logo_content_type = logo
        if logo_content_type != "image/svg+xml":
            logo_b64 = base64.b64encode(logo_bytes).decode()
            logo_html = (
                f'<img src="data:{logo_content_type};base64,{logo_b64}" '
                f'style="max-height:60px;max-width:200px;" />'
            )

    document = f"""
    <html>
    <head>
    <meta charset="utf-8" />
    <style>
        @page {{
            size: letter;
            @frame content_frame {{
                top: 15mm; left: 20mm; right: 20mm; bottom: 22mm;
            }}
            @frame footer_frame {{
                -pdf-frame-content: footer_content;
                bottom: 10mm; left: 20mm; right: 20mm; height: 10mm;
            }}
        }}
    </style>
    </head>
    <body style="font-family: Helvetica, Arial, sans-serif; font-size: 11pt;">
        <div id="footer_content" style="text-align:center;color:#4F6676;font-size:7pt;">
            {FOOTER_TEXT}
        </div>
        <div style="text-align:center;margin-bottom:12px;">
            {logo_html}
            <h2>{clinic_name}</h2>
        </div>
        <div>{body}</div>
        <div style="margin-top:40px;">
            <p>Firma de: {signer_name} ({signer_relationship_label})</p>
            <img src="data:image/png;base64,{signature_b64}" style="max-height:120px;" />
            <p>Fecha y hora: {signed_at_label}</p>
        </div>
    </body>
    </html>
    """

    buffer = io.BytesIO()
    result = pisa.CreatePDF(document, dest=buffer)
    if result.err:
        raise PdfRenderError("No se pudo generar el PDF del consentimiento")
    return buffer.getvalue()
