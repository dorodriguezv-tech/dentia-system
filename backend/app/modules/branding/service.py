import io
import uuid

from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.core.storage import StorageBackend
from app.modules.branding import color_utils
from app.modules.branding.models import ClinicBranding
from app.modules.branding.presets import DEFAULT_PRESET, full_palette
from app.modules.branding.schemas import (
    BrandingOut,
    BrandingUpdateRequest,
    ColorPalette,
    ContrastWarning,
)
from app.modules.branding.svg_sanitize import InvalidSvgError, sanitize_svg
from app.modules.iam.models import Clinic

MAX_LOGO_BYTES = 1_000_000
ALLOWED_LOGO_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/svg+xml": ".svg",
}
FAVICON_SIZE = (64, 64)

_LOGO_URL = "/api/v1/branding/logo"
_FAVICON_URL = "/api/v1/branding/favicon"


def _contrast_warnings(colors: ColorPalette) -> list[ContrastWarning]:
    warnings: list[ContrastWarning] = []

    text_bg_ratio = color_utils.contrast_ratio(colors.text, colors.bg)
    if text_bg_ratio < 4.5:
        suggested = color_utils.suggest_contrasting_color(colors.text, colors.bg)
        warnings.append(
            ContrastWarning(
                pair="texto/fondo", ratio=round(text_bg_ratio, 2), suggested_color=suggested
            )
        )

    button_ratio = color_utils.contrast_ratio("#FFFFFF", colors.primary)
    if button_ratio < 4.5:
        suggested = color_utils.suggest_contrasting_color(colors.primary, "#FFFFFF")
        warnings.append(
            ContrastWarning(
                pair="texto de boton/primario",
                ratio=round(button_ratio, 2),
                suggested_color=suggested,
            )
        )

    return warnings


async def get_default_clinic(db: AsyncSession) -> Clinic | None:
    """MVP de una sola clinica visible en el login; ver docs/PENDIENTES_CLINICOS.md."""
    stmt = select(Clinic).order_by(Clinic.created_at).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


def _asset_urls(branding: ClinicBranding | None) -> tuple[str | None, str | None]:
    if branding is None:
        return None, None
    logo_url = _LOGO_URL if branding.logo_path else None
    favicon_url = _FAVICON_URL if branding.favicon_path else None
    return logo_url, favicon_url


def _default_branding_out(display_name: str) -> BrandingOut:
    colors = ColorPalette.model_validate(full_palette(DEFAULT_PRESET))
    return BrandingOut(
        display_name=display_name,
        subtitle=None,
        preset=DEFAULT_PRESET,
        colors=colors,
        dark_mode=False,
        radius="soft",
        logo_url=None,
        favicon_url=None,
        contrast_warnings=_contrast_warnings(colors),
    )


async def get_branding(db: AsyncSession) -> BrandingOut:
    clinic = await get_default_clinic(db)
    if clinic is None:
        return _default_branding_out("DentalCare")

    branding = await db.get(ClinicBranding, clinic.id)
    if branding is None:
        return _default_branding_out(clinic.name)

    colors = ColorPalette.model_validate(branding.colors)
    logo_url, favicon_url = _asset_urls(branding)
    return BrandingOut(
        display_name=branding.display_name,
        subtitle=branding.subtitle,
        preset=branding.preset,
        colors=colors,
        dark_mode=branding.dark_mode,
        radius=branding.radius,
        logo_url=logo_url,
        favicon_url=favicon_url,
        contrast_warnings=_contrast_warnings(colors),
    )


async def _get_or_create(db: AsyncSession, clinic_id: uuid.UUID) -> ClinicBranding:
    branding = await db.get(ClinicBranding, clinic_id)
    if branding is None:
        clinic = await db.get(Clinic, clinic_id)
        assert clinic is not None
        branding = ClinicBranding(
            clinic_id=clinic_id,
            display_name=clinic.name,
            preset=DEFAULT_PRESET,
            colors=full_palette(DEFAULT_PRESET),
        )
        db.add(branding)
    return branding


async def update_branding(
    db: AsyncSession, *, clinic_id: uuid.UUID, data: BrandingUpdateRequest, actor_id: uuid.UUID
) -> BrandingOut:
    colors = full_palette(data.preset) if data.preset != "custom" else data.colors
    assert colors is not None
    palette = ColorPalette.model_validate(colors) if isinstance(colors, dict) else colors

    branding = await _get_or_create(db, clinic_id)
    branding.display_name = data.display_name
    branding.subtitle = data.subtitle
    branding.preset = data.preset
    branding.colors = palette.model_dump()
    branding.dark_mode = data.dark_mode
    branding.radius = data.radius
    branding.updated_by = actor_id

    await audit_service.log(
        db,
        action="branding.updated",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="clinic_branding",
        entity_id=str(clinic_id),
        details={"preset": data.preset},
    )
    await db.commit()

    logo_url, favicon_url = _asset_urls(branding)
    return BrandingOut(
        display_name=branding.display_name,
        subtitle=branding.subtitle,
        preset=branding.preset,
        colors=palette,
        dark_mode=branding.dark_mode,
        radius=branding.radius,
        logo_url=logo_url,
        favicon_url=favicon_url,
        contrast_warnings=_contrast_warnings(palette),
    )


def _make_favicon(data: bytes, content_type: str) -> tuple[bytes, str]:
    if content_type == "image/svg+xml":
        return data, ".svg"

    with Image.open(io.BytesIO(data)) as image:
        rgba_image = image.convert("RGBA")
        rgba_image.thumbnail(FAVICON_SIZE)
        canvas = Image.new("RGBA", FAVICON_SIZE, (0, 0, 0, 0))
        offset = (
            (FAVICON_SIZE[0] - rgba_image.width) // 2,
            (FAVICON_SIZE[1] - rgba_image.height) // 2,
        )
        canvas.paste(rgba_image, offset)
        buffer = io.BytesIO()
        canvas.save(buffer, format="PNG")
        return buffer.getvalue(), ".png"


async def upload_logo(
    db: AsyncSession,
    storage: StorageBackend,
    *,
    clinic_id: uuid.UUID,
    filename: str,
    content_type: str,
    data: bytes,
    actor_id: uuid.UUID,
) -> BrandingOut:
    if len(data) > MAX_LOGO_BYTES:
        raise AppError("FILE_TOO_LARGE", "El logo no puede pesar mas de 1 MB", status_code=400)

    suffix = ALLOWED_LOGO_TYPES.get(content_type)
    if suffix is None:
        raise AppError("INVALID_FILE_TYPE", "El logo debe ser PNG, JPG o SVG", status_code=400)

    if content_type == "image/svg+xml":
        try:
            data = sanitize_svg(data)
        except InvalidSvgError as exc:
            raise AppError("INVALID_SVG", str(exc), status_code=400) from exc
    else:
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
        except Exception as exc:
            raise AppError(
                "INVALID_IMAGE", "El archivo no es una imagen valida", status_code=400
            ) from exc

    branding = await _get_or_create(db, clinic_id)

    logo_key = storage.save(data, subdir=f"branding/{clinic_id}", suffix=suffix)
    favicon_bytes, favicon_suffix = _make_favicon(data, content_type)
    favicon_key = storage.save(
        favicon_bytes, subdir=f"branding/{clinic_id}", suffix=f".favicon{favicon_suffix}"
    )

    old_logo, old_favicon = branding.logo_path, branding.favicon_path
    branding.logo_path = logo_key
    branding.favicon_path = favicon_key
    branding.updated_by = actor_id

    await audit_service.log(
        db,
        action="branding.logo_updated",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="clinic_branding",
        entity_id=str(clinic_id),
    )
    await db.commit()

    for old_key in (old_logo, old_favicon):
        if old_key:
            storage.delete(old_key)

    colors = ColorPalette.model_validate(branding.colors)
    return BrandingOut(
        display_name=branding.display_name,
        subtitle=branding.subtitle,
        preset=branding.preset,
        colors=colors,
        dark_mode=branding.dark_mode,
        radius=branding.radius,
        logo_url=_LOGO_URL,
        favicon_url=_FAVICON_URL,
        contrast_warnings=_contrast_warnings(colors),
    )


async def read_logo(db: AsyncSession, storage: StorageBackend) -> tuple[bytes, str] | None:
    return await _read_asset(db, storage, favicon=False)


async def read_favicon(db: AsyncSession, storage: StorageBackend) -> tuple[bytes, str] | None:
    return await _read_asset(db, storage, favicon=True)


async def _read_asset(
    db: AsyncSession, storage: StorageBackend, *, favicon: bool
) -> tuple[bytes, str] | None:
    clinic = await get_default_clinic(db)
    if clinic is None:
        return None
    branding = await db.get(ClinicBranding, clinic.id)
    if branding is None:
        return None

    key = branding.favicon_path if favicon else branding.logo_path
    if not key:
        return None

    content_type = _guess_content_type(key)
    return storage.read(key), content_type


def _guess_content_type(key: str) -> str:
    if key.endswith(".svg"):
        return "image/svg+xml"
    if key.endswith(".jpg") or key.endswith(".jpeg"):
        return "image/jpeg"
    return "image/png"
