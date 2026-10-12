# Manual breve de marca — DENT-IA

![Identidad visual DENT-IA](MARCA_DENT-IA.png)

## 1. Nombre
- Se escribe **DENT-IA** (mayúsculas, con guion). Nombre completo: **DENT-IA · Sistema Inteligente de Gestión Odontológica**.
- El **asistente de voz** se llama **Dentia** (así se pronuncia y así se activa por voz). No se escribe "Dent-IA" en los mensajes del asistente.
- Los identificadores técnicos no cambian: base de datos `dentia`, paquete `mx.dentia.app`, carpetas, variables.

## 2. Arquitectura de marca
| Nivel | Qué es | Dónde se ve |
|---|---|---|
| **Producto: DENT-IA** | El software | Favicon, ícono de la app, splash, pantalla de login cuando la clínica no subió logo, pie de PDFs, Google Play |
| **Clínica** (marca blanca) | Nombre, logo y colores que el admin sube en *Configuración → Apariencia* | Barra lateral, login, PDFs, app móvil |

Cuando la clínica usa su propia marca, DENT-IA aparece discretamente como **"con tecnología DENT-IA"** (isotipo + nombre) en el login, al pie de la barra lateral y en el pie de los PDFs.

## 3. Versiones del logo
| Archivo | Uso |
|---|---|
| `dentia-logo.png` (color, fondo transparente) | Fondos blancos o claros |
| `dentia-logo-blanco.png` | Fondos oscuros, modo oscuro, splash oscuro |
| `dentia-isotipo.png` / `.svg` (diente con circuitos) | Favicon, ícono de app, espacios pequeños, "con tecnología" |
| `dentia-isotipo-blanco.png` | Isotipo sobre azul (botón de Dentia, íconos temáticos de Android) |
| `originales/` | Versiones de alta resolución (2001 px) y el archivo recibido |

- **Área de protección:** deja alrededor del logo un espacio libre igual a la altura de la letra "D".
- **Tamaño mínimo:** logo completo 160 px de ancho en pantalla (el lema deja de leerse debajo); isotipo 16 px.
- **No** cambies sus colores, no lo estires, no le pongas sombra ni lo coloques sobre fotografías o fondos de contraste medio (por ejemplo, sobre el cian).

> Los PNG se generaron del archivo recibido (768 × 582 px) con reconstrucción de bordes. Para impresión grande (lonas, fachada) pide al diseñador el logo **vectorial** (SVG/AI/PDF). El `dentia-isotipo.svg` incluido es un trazado automático apto para pantalla.

## 4. Color (preset `dentia`)
| Token | Hex | Uso | Contraste |
|---|---|---|---|
| Azul DENT-IA | `#004A73` | Letras del logo, títulos de marca | blanco encima 9.4:1 |
| **Primario** | `#0A5A8C` | Botones, enlaces, elementos activos | blanco encima 7.4:1 · sobre fondo 7.0:1 |
| Secundario (azul circuito) | `#1690B6` | Insignias, gráficos, texto grande | blanco encima 3.7:1 (solo texto ≥ 18 px negrita) |
| Acento (cian circuito) | `#22AAC2` | Decoración, franjas, ilustraciones | **no** para texto (2.8:1) |
| Degradado de marca | `#22AAC2 → #0A5A8C` | Franja superior, encabezados decorativos | — |
| Fondo | `#F5F9FC` | Fondo general claro | — |
| Superficie | `#FFFFFF` | Tarjetas | — |
| Borde | `#D3E2EC` | Divisiones | — |
| Texto | `#0E2A3B` | Texto principal | 14:1 sobre fondo |
| Texto secundario | `#4F6676` | Ayudas, metadatos | 5.7:1 sobre fondo |
| Primario en modo oscuro | `#4FC3D9` | Botones/enlaces en oscuro | 7.7:1 sobre `#13242F` |
| Fondo oscuro / superficie oscura | `#0B1A24` / `#13242F` | Modo oscuro | — |

Éxito, advertencia y peligro **no cambian** (`#3BA55C`, `#E0A100`, `#D64545`), y los colores clínicos del odontograma siguen siendo independientes de la marca (docs/04 §5).

## 5. Tipografía
- **Montserrat** (600 y 700) para encabezados y el nombre DENT-IA en texto — es la familia geométrica más cercana a la del logo. Licencia OFL, gratuita.
- **Inter** se mantiene para el texto de la interfaz.
- En la web se instala local (`@fontsource/montserrat`), no desde el CDN de Google: el sistema corre en la red de la clínica y debe funcionar sin internet.
- En la app móvil va empaquetada (`@expo-google-fonts/montserrat`).
