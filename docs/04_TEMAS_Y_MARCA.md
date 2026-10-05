# Temas, colores y logo configurables

## 1. Requisito
El administrador de la clínica puede cambiar desde **Configuración → Apariencia**, sin programar:
- Nombre comercial y subtítulo
- Logo (PNG, JPG o SVG; máximo 1 MB). El SVG se sanitiza antes de guardarse.
- Favicon (se genera a partir del logo)
- Paleta: elegir un preset o personalizar los colores
- Modo claro u oscuro (opcional) y radio de bordes (suave o recto)

Los cambios se ven en vista previa y se aplican a todos los usuarios de la clínica (o sucursal).

## 2. Tokens CSS (`frontend/src/theme/tokens.css`)
```css
:root {
  --color-primary:        #2BB3A3;
  --color-primary-hover:  #23998B;
  --color-primary-soft:   #E6F6F4;
  --color-secondary:      #4A90C2;
  --color-accent:         #F2A65A;
  --color-bg:             #F7FAFA;
  --color-surface:        #FFFFFF;
  --color-border:         #DCE6E5;
  --color-text:           #1F2D2B;
  --color-text-muted:     #5E6E6C;
  --color-success:        #3BA55C;
  --color-warning:        #E0A100;
  --color-danger:         #D64545;   /* alertas clínicas */
  --radius:               10px;
  --font-family:          "Inter", "Segoe UI", system-ui, sans-serif;
}
```
`ThemeProvider` lee `GET /api/v1/branding` al iniciar y escribe las variables en `document.documentElement.style`. Ningún componente usa colores fijos.

## 3. Presets amigables para clínica dental
| Preset | Primario | Secundario | Acento | Fondo | Sensación |
|---|---|---|---|---|---|
| Menta clínica (predeterminado) | #2BB3A3 | #4A90C2 | #F2A65A | #F7FAFA | Limpio, fresco |
| Azul sereno | #3A7FC1 | #5BBFD6 | #F4B860 | #F5F8FC | Confianza, calma |
| Aqua suave | #1FA2B8 | #7CC6A6 | #FF9F80 | #F4FAFB | Moderno, amable |
| Lavanda suave | #7B7FD4 | #5FB3C9 | #F2B5A0 | #F8F8FD | Cálido, infantil/estético |
| Verde salvia | #6A9E7F | #4F8FA8 | #E8B04B | #F6F9F6 | Natural, relajante |
| Grafito profesional | #37515F | #2BB3A3 | #F2A65A | #F6F7F8 | Sobrio, especialidades |

## 4. Reglas de accesibilidad
- Al guardar se calcula el contraste WCAG entre texto y fondo y entre el texto del botón y el primario. Si es menor de 4.5:1, se avisa y se propone un ajuste automático (oscurecer o aclarar).
- `--color-primary-hover` y `--color-primary-soft` se derivan automáticamente del primario (±12 % de luminosidad en HSL).

## 5. Separación importante
Los **colores clínicos del odontograma** (caries roja, restauración azul, planificado en contorno, ausente en gris, etc.) **no** dependen de la marca. Tienen su propia configuración en **Configuración → Odontograma → Leyenda**, para que un cambio de imagen comercial nunca altere el significado clínico.

## 6. Datos
Tabla `clinic_branding`: `clinic_id, display_name, subtitle, logo_path, favicon_path, preset, colors jsonb, dark_mode bool, radius, updated_by, updated_at`. Cada cambio se audita.
