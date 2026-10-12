"""Genera los tamanos derivados de marca DENT-IA para backend/frontend a partir de
los PNG oficiales que ya usa la app movil (mobile/assets/brand/*). No inventa un
logo nuevo: solo redimensiona/compone el isotipo y el logo completo ya aprobados
(ver mobile/docs/MARCA_DENT-IA.png).

Uso unico, no se importa desde la app. Ejecutar desde la raiz del repo:
    python scripts/generate_brand_assets.py
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MOBILE_BRAND = ROOT / "mobile" / "assets" / "brand"
BACKEND_DEFAULTS = ROOT / "backend" / "app" / "modules" / "branding" / "default_assets"
FRONTEND_BRAND = ROOT / "frontend" / "src" / "assets" / "brand"
FRONTEND_PUBLIC = ROOT / "frontend" / "public"

PRIMARY = (10, 90, 140, 255)  # #0A5A8C


def square_canvas(im: Image.Image, size: int, bg=None, pad_ratio: float = 0.0) -> Image.Image:
    im = im.convert("RGBA")
    inner = int(size * (1 - pad_ratio * 2))
    im.thumbnail((inner, inner), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), bg if bg else (0, 0, 0, 0))
    offset = ((size - im.width) // 2, (size - im.height) // 2)
    canvas.paste(im, offset, im)
    return canvas


def main() -> None:
    BACKEND_DEFAULTS.mkdir(parents=True, exist_ok=True)
    FRONTEND_BRAND.mkdir(parents=True, exist_ok=True)
    FRONTEND_PUBLIC.mkdir(parents=True, exist_ok=True)

    logo = Image.open(MOBILE_BRAND / "dentia-logo.png")
    logo_white = Image.open(MOBILE_BRAND / "dentia-logo-blanco.png")
    isotipo = Image.open(MOBILE_BRAND / "dentia-isotipo.png")
    isotipo_white = Image.open(MOBILE_BRAND / "dentia-isotipo-blanco.png")

    # ---- backend/app/modules/branding/default_assets (W2) ----
    logo.save(BACKEND_DEFAULTS / "dentia-logo.png")
    square_canvas(isotipo, 64).save(BACKEND_DEFAULTS / "dentia-favicon.png")

    # ---- frontend/src/assets/brand (W7) ----
    logo.save(FRONTEND_BRAND / "dentia-logo.png")
    logo_white.save(FRONTEND_BRAND / "dentia-logo-blanco.png")
    isotipo.save(FRONTEND_BRAND / "dentia-isotipo.png")
    isotipo_white.save(FRONTEND_BRAND / "dentia-isotipo-blanco.png")

    # ---- frontend/public (W5): favicon e iconos PWA ----
    square_canvas(isotipo, 64, bg=(255, 255, 255, 255)).save(FRONTEND_PUBLIC / "favicon-64.png")
    sizes_ico = [square_canvas(isotipo, s, bg=(255, 255, 255, 255)) for s in (16, 32, 48)]
    sizes_ico[-1].save(
        FRONTEND_PUBLIC / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)]
    )
    square_canvas(isotipo, 180, bg=(255, 255, 255, 255)).save(
        FRONTEND_PUBLIC / "apple-touch-icon.png"
    )
    square_canvas(isotipo, 192, bg=(255, 255, 255, 255)).save(FRONTEND_PUBLIC / "icon-192.png")
    square_canvas(isotipo, 512, bg=(255, 255, 255, 255)).save(FRONTEND_PUBLIC / "icon-512.png")
    # Maskable: relleno generoso (zona segura ~40% de radio) sobre el primario DENT-IA.
    square_canvas(isotipo_white, 512, bg=PRIMARY, pad_ratio=0.22).save(
        FRONTEND_PUBLIC / "icon-maskable-512.png"
    )

    print("Listo:", BACKEND_DEFAULTS, FRONTEND_BRAND, FRONTEND_PUBLIC)


if __name__ == "__main__":
    main()
