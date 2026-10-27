"""Encabezado compartido de TODO PDF del sistema (Fase A del rediseno del
expediente, docs/clinica, punto 2 de las decisiones confirmadas con el
usuario): logo izquierdo + logo derecho + titulo institucional + lugar.

Se divide en dos partes:
- `get_pdf_header_info` (impura: lee BD y storage) resuelve los datos de la
  sucursal, con los fallbacks razonables para no romper los PDF existentes:
  * si "Formatos de documentos" no tiene logo izquierdo, se usa el logo unico
    de Marca y Temas (branding) como logo izquierdo.
  * si no hay titulo institucional, se usa el `display_name` de branding
    (lo que ya mostraban documents/pdf.py y treatment/pdf.py antes de esta
    fase).
  * el logo derecho y el lugar no tienen un equivalente previo: si no estan
    configurados, simplemente no se dibujan.
- El resto de funciones son puras (reciben los bytes ya resueltos) para que
  documents/pdf.py y treatment/pdf.py las puedan usar sin tocar la BD, igual
  que el resto de ese modulo (se prueban sin fixtures).
"""

import base64
import html
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import StorageBackend
from app.modules.branding import service as branding_service
from app.modules.document_settings import service as document_settings_service

Logo = tuple[bytes, str]

# A peticion del operador: el logo se veia inmenso y centrado, empujando el
# contenido a una segunda hoja -- pequeno y a la izquierda/derecha en todo PDF
# basado en xhtml2pdf del sistema (documents/pdf.py, records/pdf.py).
LOGO_MAX_HEIGHT_PX = 28
LOGO_MAX_WIDTH_PX = 90


@dataclass
class PdfHeaderInfo:
    institutional_title: str
    place_label: str | None
    logo_left: Logo | None
    logo_right: Logo | None


async def get_pdf_header_info(
    db: AsyncSession, storage: StorageBackend, *, clinic_id: object
) -> PdfHeaderInfo:
    branding = await branding_service.get_branding(db)
    doc_settings = await document_settings_service.get_document_settings(db, clinic_id=clinic_id)  # type: ignore[arg-type]

    logo_left = await document_settings_service.read_logo(
        db, storage, clinic_id=clinic_id, side="left"  # type: ignore[arg-type]
    )
    if logo_left is None:
        # Fallback: el logo unico de branding, para que los documentos
        # existentes (consentimientos, presupuesto) no queden sin logo hasta
        # que la clinica configure "Formatos de documentos".
        logo_left = await branding_service.read_logo(db, storage)

    logo_right = await document_settings_service.read_logo(
        db, storage, clinic_id=clinic_id, side="right"  # type: ignore[arg-type]
    )

    institutional_title = doc_settings.institutional_title or branding.display_name

    return PdfHeaderInfo(
        institutional_title=institutional_title,
        place_label=doc_settings.place_label,
        logo_left=logo_left,
        logo_right=logo_right,
    )


def place_and_date_label(place_label: str | None, date_label: str) -> str:
    """ "Lugar y fecha: {lugar} a {fecha}" (formatos oficiales, docs/clinica) --
    sin lugar configurado, cae a solo la fecha (no bloquea la impresion)."""
    if place_label:
        return f"Lugar y fecha: {place_label} a {date_label}"
    return f"Fecha: {date_label}"


def render_logo_html(logo: Logo | None) -> str:
    """Helper para los PDF basados en xhtml2pdf (documents/pdf.py,
    records/pdf.py) -- reportlab (treatment/pdf.py) usa su propio flowable
    Image, no HTML."""
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


def render_header_html(header: "PdfHeaderInfo") -> str:
    """Logo izquierdo + titulo institucional + logo derecho (Fase A, decision
    confirmada #2: un unico par de logos para todos los documentos imprimibles),
    como tabla HTML para los PDF basados en xhtml2pdf."""
    return f"""
    <table style="width:100%;border-collapse:collapse;margin-bottom:6px;">
        <tr>
            <td style="width:100px;vertical-align:middle;">{render_logo_html(header.logo_left)}</td>
            <td style="vertical-align:middle;text-align:center;">
                <div style="font-size:10pt;font-weight:bold;">
                    {html.escape(header.institutional_title)}
                </div>
            </td>
            <td style="width:100px;vertical-align:middle;text-align:right;">
                {render_logo_html(header.logo_right)}
            </td>
        </tr>
    </table>
    """
