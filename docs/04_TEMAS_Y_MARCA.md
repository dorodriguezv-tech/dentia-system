# Temas, colores y logo configurables

## 1. Requisito
El administrador de la clínica puede cambiar desde **Configuración → Apariencia**, sin programar:
- Nombre comercial y subtítulo
- Logo (PNG, JPG o SVG; máximo 1 MB). El SVG se sanitiza antes de guardarse.
- Favicon (se genera a partir del logo)
- Paleta: elegir un preset o personalizar los colores
- Modo claro u oscuro (opcional) y radio de bordes (suave o recto)

Los cambios se ven en vista previa y se aplican a todos los usuarios de la clínica (o sucursal).

Mientras la clínica no configure su marca, el sistema muestra la identidad del producto
**DENT-IA** (sección 7).

## 2. Tokens CSS (`frontend/src/theme/tokens.css`)
Valores de arranque = preset `dentia` (se reemplazan al llegar `GET /branding`):
```css
:root {
  --color-primary:        #0A5A8C;
  --color-primary-hover:  (derivado);
  --color-primary-soft:   (derivado);
  --color-secondary:      #1690B6;
  --color-accent:         #22AAC2;
  --color-bg:             #F5F9FC;
  --color-surface:        #FFFFFF;
  --color-border:         #D3E2EC;
  --color-text:           #0E2A3B;
  --color-text-muted:     #4F6676;
  --color-success:        #3BA55C;
  --color-warning:        #E0A100;
  --color-danger:         #D64545;   /* alertas clínicas */
  --radius:               10px;
  --font-family:          "Inter", "Segoe UI", system-ui, sans-serif;
  --font-heading:         "Montserrat", "Inter", "Segoe UI", system-ui, sans-serif;

  /* Marca del producto (fijos, no los cambia la clínica) */
  --brand-dentia-navy:     #004A73;
  --brand-dentia-cyan:     #22AAC2;
  --brand-dentia-gradient: linear-gradient(90deg, #22AAC2 0%, #0A5A8C 100%);
}
```
`ThemeProvider` lee `GET /api/v1/branding` al iniciar y escribe las variables en `document.documentElement.style`. Ningún componente usa colores fijos.

## 3. Presets amigables para clínica dental
| Preset | Primario | Secundario | Acento | Fondo | Sensación |
|---|---|---|---|---|---|
| **DENT-IA institucional (predeterminado)** | #0A5A8C | #1690B6 | #22AAC2 | #F5F9FC | Tecnológico, confiable — colores del logo |
| Menta clínica | #2BB3A3 | #4A90C2 | #F2A65A | #F7FAFA | Limpio, fresco |
| Azul sereno | #3A7FC1 | #5BBFD6 | #F4B860 | #F5F8FC | Confianza, calma |
| Aqua suave | #1FA2B8 | #7CC6A6 | #FF9F80 | #F4FAFB | Moderno, amable |
| Lavanda suave | #7B7FD4 | #5FB3C9 | #F2B5A0 | #F8F8FD | Cálido, infantil/estético |
| Verde salvia | #6A9E7F | #4F8FA8 | #E8B04B | #F6F9F6 | Natural, relajante |
| Grafito profesional | #37515F | #2BB3A3 | #F2A65A | #F6F7F8 | Sobrio, especialidades |

El preset `dentia` define además `dark_primary: #4FC3D9` (ver §4). Las sucursales creadas
antes de este cambio conservan el preset que ya tenían.

## 4. Reglas de accesibilidad
- Al guardar se calcula el contraste WCAG entre texto y fondo y entre el texto del botón y el primario. Si es menor de 4.5:1, se avisa y se propone un ajuste automático (oscurecer o aclarar).
- `--color-primary-hover` y `--color-primary-soft` se derivan automáticamente del primario (±12 % de luminosidad en HSL).
- **Modo oscuro:** si el preset trae `dark_primary`, se usa; si no, el primario se aclara hasta 4.5:1 sobre la superficie oscura. Un primario oscuro como `#0A5A8C` no se lee sobre fondo oscuro (2.2:1).
- El cian `#22AAC2` del logo es decorativo: no se usa para texto pequeño (2.8:1 sobre blanco).

## 5. Separación importante
Los **colores clínicos del odontograma** (caries roja, restauración azul, planificado en contorno, ausente en gris, etc.) **no** dependen de la marca. Tienen su propia configuración en **Configuración → Odontograma → Leyenda**, para que un cambio de imagen comercial nunca altere el significado clínico.

## 6. Datos
Tabla `clinic_branding`: `clinic_id, display_name, subtitle, logo_path, favicon_path, preset, colors jsonb, dark_mode bool, radius, updated_by, updated_at`. Cada cambio se audita.
`GET /branding` agrega `has_custom_logo` (calculado: `logo_path` no nulo).

## 7. Marca del producto: DENT-IA
Manual completo: `docs/MARCA_DENT-IA.md`.

- **Nombre:** DENT-IA (con guion). El asistente de voz se sigue llamando **Dentia**.
- **Logo oficial:** diente con circuitos dentro del nombre, anillo con degradado cian → azul y lema "Sistema Inteligente de Gestión Odontológica". Archivos en `frontend/src/assets/brand/`, `backend/app/modules/branding/default_assets/` y `mobile/assets/brand/`.
- **Por defecto:** si la sucursal no subió logo, `GET /branding/logo` y `/branding/favicon` devuelven los de DENT-IA (200, no 404); `display_name` por defecto "DENT-IA".
- **Marca blanca:** cuando la clínica usa su propio logo, DENT-IA aparece como "con tecnología DENT-IA" (isotipo + nombre) en el login, al pie de la barra lateral y en el pie de los PDFs.
- **PDFs:** logo de la clínica (o DENT-IA) en el encabezado; pie "Generado con DENT-IA · Sistema Inteligente de Gestión Odontológica". En consentimientos, el pie va fuera del contenido firmado para no alterar su hash (regla 7).
- **Tipografía:** Montserrat 600/700 para encabezados (local con `@fontsource/montserrat`, sin CDN); Inter para el resto.
- **Favicon, ícono PWA e ícono de la app:** isotipo DENT-IA.
- **App móvil:** mismo preset (`DENTIA_BRAND` en `mobile/src/theme/theme.tsx`), splash con el logo completo (versión blanca en modo oscuro), ícono adaptable con el isotipo e ícono temático monocromo.
