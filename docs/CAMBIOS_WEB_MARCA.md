# Aplicar la marca DENT-IA al sistema web

Este paquete trae los archivos listos y describe cada cambio de código. Como no tengo
acceso a tu equipo, los fragmentos de código siguen la estructura documentada en
`docs/02_ARQUITECTURA.md` §5.2 y `docs/04_TEMAS_Y_MARCA.md`; **Claude Code los adapta a los
nombres exactos de tu repositorio** (prompt al final).

## 0. Copiar archivos (desde la raíz del zip a `C:\workspace\dentia-system\`)

| Del paquete | Al repositorio |
|---|---|
| `frontend/public/*` (favicon.ico, favicon-64.png, apple-touch-icon.png, icon-192/512, icon-maskable-512, manifest.webmanifest) | `frontend/public/` (reemplaza el favicon actual) |
| `frontend/src/assets/brand/*` | `frontend/src/assets/brand/` |
| `backend/app/modules/branding/default_assets/*` | igual ruta en el backend |
| `docs/MARCA_DENT-IA.md` + `.png`, `docs/04_TEMAS_Y_MARCA.md` | `docs/` (el 04 reemplaza al actual) |
| `originales/` | `docs/marca/originales/` (no se sirve en la app) |

## 1. Backend

### W1 — Preset `dentia` y predeterminado (`backend/app/modules/branding/presets.py`)
Agregar como **primer** preset y usarlo como valor por defecto para sucursales nuevas:

```python
PRESETS["dentia"] = {
    "label": "DENT-IA (institucional)",
    "primary": "#0A5A8C",
    "secondary": "#1690B6",
    "accent": "#22AAC2",
    "background": "#F5F9FC",
    "surface": "#FFFFFF",
    "border": "#D3E2EC",
    "text": "#0E2A3B",
    "text_muted": "#4F6676",
    # nuevo y opcional para todos los presets: primario en modo oscuro
    "dark_primary": "#4FC3D9",
}
DEFAULT_PRESET = "dentia"   # antes: menta clínica
```
- **No** se migra la marca de las sucursales existentes: quien ya eligió "Menta clínica" la conserva. La migración Alembic solo cambia el `server_default` de `clinic_branding.preset` (si lo tiene) a `"dentia"`.
- `color_utils.py` debe aceptar `dark_primary` opcional; si un preset no lo trae, el frontend lo deriva aclarando el primario hasta 4.5:1 sobre la superficie oscura.
- Prueba: el preset `dentia` pasa la validación de contraste WCAG existente (botón y texto ≥ 4.5:1) sin `contrast_warnings`.

### W2 — Logo y favicon por defecto (`branding/service.py` + `router.py`)
- `GET /branding/logo`: si la sucursal **no** subió logo, responder `200` con `default_assets/dentia-logo.png` (hoy probablemente responde 404). Igual para `GET /branding/favicon` con `dentia-favicon.png`.
- `GET /branding`: `display_name` por defecto **"DENT-IA"** y `subtitle` por defecto **"Sistema Inteligente de Gestión Odontológica"**; agregar `has_custom_logo: bool` para que el frontend sepa si mostrar "con tecnología DENT-IA".
- Siguen siendo públicos (son imagen de marca, no datos clínicos), como ya documenta la Fase 2.
- Pruebas: sucursal sin logo → 200 `image/png`; sucursal con logo → su logo; `has_custom_logo` correcto.

### W3 — PDFs con la marca (`treatment/pdf.py`, recibo de `billing`, consentimiento de `documents`)
- Encabezado: logo de la clínica (`branding_service.read_logo`), y si no hay, el de DENT-IA (`default_assets/dentia-logo.png`, PNG raster: reportlab y xhtml2pdf lo dibujan sin problema).
- Pie de página, en gris `#4F6676`, 7 pt: **"Generado con DENT-IA · Sistema Inteligente de Gestión Odontológica"**.
- En el consentimiento, el pie va **fuera** del HTML firmado (en la plantilla de página de xhtml2pdf), para no alterar el contenido que se hashea (regla 7). Verificar que el `content_hash` de consentimientos ya firmados no cambia.
- Pruebas: las funciones puras de PDF generan el archivo con y sin logo de clínica.

### W4 — Textos
- `app/main.py`: `FastAPI(title="DENT-IA API", ...)`.
- Cualquier texto visible "DentalCare" o "DENTIA" → "DENT-IA" (correos, plantillas por defecto, `docs/MANUAL_TECNICO.md` que aún dice DentalCare). Identificadores técnicos sin cambio.

## 2. Frontend

### W5 — `frontend/index.html`
```html
<title>DENT-IA · Sistema Inteligente de Gestión Odontológica</title>
<meta name="theme-color" content="#0A5A8C" />
<link rel="icon" href="/favicon.ico" sizes="any" />
<link rel="icon" type="image/png" sizes="64x64" href="/favicon-64.png" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
<link rel="manifest" href="/manifest.webmanifest" />
```
`ThemeProvider` sigue cambiando el favicon al de la clínica cuando esta subió el suyo.

### W6 — Tokens y presets (`frontend/src/theme/tokens.css`, `presets.ts`)
Valores de arranque (antes de que llegue `GET /branding`) = preset `dentia`:
```css
:root {
  --color-primary:    #0A5A8C;
  --color-secondary:  #1690B6;
  --color-accent:     #22AAC2;
  --color-bg:         #F5F9FC;
  --color-surface:    #FFFFFF;
  --color-border:     #D3E2EC;
  --color-text:       #0E2A3B;
  --color-text-muted: #4F6676;
  /* marca del producto: fijos, no los cambia la clínica */
  --brand-dentia-navy: #004A73;
  --brand-dentia-cyan: #22AAC2;
  --brand-dentia-gradient: linear-gradient(90deg, #22AAC2 0%, #0A5A8C 100%);
  --font-heading: "Montserrat", "Inter", "Segoe UI", system-ui, sans-serif;
}
h1, h2, h3, .brand-title { font-family: var(--font-heading); }
```
- `presets.ts`: copia exacta del preset de W1 (mismo patrón espejo que ya usan).
- Modo oscuro: si el preset trae `dark_primary`, úsalo en lugar del primario; si no, derivarlo en `theme/colorUtils.ts` (aclarar hasta 4.5:1 sobre la superficie oscura).
- `npm install @fontsource/montserrat` e importar `@fontsource/montserrat/600.css` y `/700.css` en `main.tsx`.

### W7 — Componentes de marca (`frontend/src/components/brand/`)
- `<DentiaLogo variant="color|white" />` (blanco en modo oscuro), `<DentiaIsotipo />` (usa el SVG), `<PoweredByDentia />` ("con tecnología" + isotipo + DENT-IA).
- **Login:** logo de la clínica si `has_custom_logo`; si no, `<DentiaLogo />` grande (ya incluye nombre y lema, no repetir el texto). Franja de 4 px con `var(--brand-dentia-gradient)` arriba de la tarjeta. `<PoweredByDentia />` al pie cuando hay logo propio.
- **Barra lateral:** logo de la clínica (o DENT-IA) arriba; `<PoweredByDentia />` pequeño al pie.
- **Configuración → Apariencia:** el preset "DENT-IA (institucional)" primero en la lista, con el isotipo en su muestra; botón "Restablecer" vuelve a este preset.
- Usar el logo como `<img>` normal: los archivos de `src/assets/brand/` son públicos (no es la foto del paciente, que sí va por `apiRequestBlobUrl`).
- El script de lint que prohíbe `#hex` fuera de `theme/` debe seguir pasando: los colores de marca solo viven en `tokens.css`/`presets.ts`.

## 3. Pruebas y documentación
- `pytest` (las 298 existentes + las nuevas de W1–W3), `ruff`, `black`, `mypy`.
- `npm run test`, `npm run lint`, `npm run build`.
- Playwright: `accessibility.spec.ts` debe seguir sin violaciones `serious/critical` con la paleta nueva; actualizar textos esperados "DENTIA"/"DentalCare" en `full-flow.spec.ts`; regenerar capturas del manual con `CAPTURE_SCREENSHOTS=1`.
- Actualizar `docs/02_ARQUITECTURA.md` §5.2 (preset `dentia`, `dark_primary`, `has_custom_logo`, logo por defecto) y `docs/MANUAL_USUARIO.md` (capturas).

## 4. Prompt para Claude Code
Copia y pega en `claude`, desde `C:\workspace\dentia-system`, **un bloque a la vez**:

```text
Vamos a aplicar la marca DENT-IA. Lee docs/MARCA_DENT-IA.md, docs/04_TEMAS_Y_MARCA.md y
CAMBIOS_WEB.md (está en la raíz del paquete que copié; si no, en docs/). Antes de editar,
muéstrame en qué archivos reales viven presets.py, presets.ts, tokens.css, ThemeProvider,
la pantalla de login, la barra lateral, branding/service.py y los tres generadores de PDF,
y dime qué difiere de lo que describe CAMBIOS_WEB.md.
```
```text
Implementa W1 y W2 en el backend con sus pruebas pytest y la migración Alembic mínima.
No cambies la marca de sucursales existentes. Corre pytest, ruff, black y mypy.
```
```text
Implementa W3 y W4. Verifica explícitamente que el content_hash de un consentimiento ya
firmado no cambia y que los PDFs se generan con y sin logo de clínica.
```
```text
Implementa W5, W6 y W7 en el frontend. Corre npm run lint, npm run test y npm run build,
y después la suite de Playwright de accesibilidad. Muéstrame el login en claro y oscuro.
```
```text
Actualiza docs/02_ARQUITECTURA.md §5.2, docs/MANUAL_TECNICO.md (DentalCare → DENT-IA) y
regenera las capturas del manual. Haz un commit por bloque (W1–W2, W3–W4, W5–W7, docs).
```
