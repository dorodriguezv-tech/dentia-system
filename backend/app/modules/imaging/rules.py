"""Catalogo de tipos de estudio de imagenologia, aislado de la BD.

Catalogo configurable (CLAUDE.md sec. 7): valores por defecto razonables, a validar con
la clinica (ver docs/PENDIENTES_CLINICOS.md).
"""

STUDY_TYPE_LABELS: dict[str, str] = {
    "intraoral": "Intraoral",
    "extraoral": "Extraoral",
    "periapical": "Periapical",
    "bitewing": "Bitewing (aleta de mordida)",
    "panoramica": "Panoramica",
    "cefalometria": "Cefalometria",
}
STUDY_TYPES: tuple[str, ...] = tuple(STUDY_TYPE_LABELS.keys())

# Fase "Publicacion en Hostinger" sec. 6, cambio #6: 25 MB (antes 15), el limite
# que establece ese documento -- Cloudflare Free acepta hasta 100 MB por
# peticion, asi que esto es lo que realmente limita, no el proxy.
MAX_IMAGE_BYTES = 25_000_000

ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "application/pdf": ".pdf",
}

THUMBNAIL_SIZE = (320, 320)
