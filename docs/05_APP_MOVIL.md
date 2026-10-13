# App móvil DENT-IA — guía completa

Desarrollo, pruebas, integración con Claude Code y publicación en Google Play.
Fecha de verificación de requisitos externos: **11 de octubre de 2026** (Google Play,
Expo y Claude Code cambian sus requisitos; revísalos de nuevo antes de publicar).

---

## 0. Decisiones de arquitectura

| Decisión | Elegido | Por qué |
|---|---|---|
| Tecnología | **Expo SDK 57 + React Native 0.86 + TypeScript** | El frontend web ya es React 18 + TS: mismos patrones (TanStack Query, Zustand, tema por variables). Un solo código para Android y, después, iOS. |
| Relación con el sistema | **Cliente del backend FastAPI** (`/api/v1`) | Cero lógica clínica duplicada: las reglas 1–10, permisos, auditoría y validaciones siguen en un solo lugar. |
| Datos en el teléfono | **Ninguno clínico** | Access token en memoria, refresh token cifrado (Android Keystore), caché solo en RAM, FLAG_SECURE, bloqueo a los 2 min. |
| Voz | Graba en el teléfono → **faster-whisper del servidor de la clínica** → Ollama local | Mismo principio de la web: el audio y el texto clínico nunca salen a un servicio de terceros. |
| Asistente "Dentia" | Órdenes con intérprete determinista + voz femenina local + **confirmación implícita de 3 s** | Respuesta en < 1 s para navegar; el dictado clínico sí pasa por Ollama y por revisión humana. |
| Conexión fuera de la clínica | **Tailscale** (VPN WireGuard) con certificado HTTPS | El servidor no se expone a internet; el teléfono "está en la red de la clínica" desde cualquier lugar. |

### 0.1 Marca DENT-IA en la app
Logo oficial aplicado (manual: `docs/MARCA_DENT-IA.md`, vista general: `docs/MARCA_DENT-IA.png`).

| Dónde | Qué se ve |
|---|---|
| Ícono en el teléfono | Isotipo (diente con circuitos) sobre blanco; ícono adaptable y **monocromo** para los íconos temáticos de Android 13+ |
| Pantalla de inicio (splash) | Logo completo sobre blanco; versión blanca sobre `#0B1A24` en modo oscuro |
| Servidor y login | Logo completo DENT-IA; si la clínica subió su logo, se muestra el suyo y abajo "con tecnología DENT-IA" |
| Botón de Dentia | Isotipo blanco sobre el primario |
| Bloqueo y Ajustes | Isotipo / logo |
| Colores | Preset `dentia`: primario `#0A5A8C`, secundario `#1690B6`, acento `#22AAC2`; en modo oscuro primario `#4FC3D9` |
| Tipografía | Montserrat en títulos, sistema en el resto |
| Nombre visible | **DENT-IA** (el asistente de voz se sigue llamando **Dentia**) |

Archivos: `assets/icon.png`, `assets/adaptive-icon.png`, `assets/adaptive-icon-monochrome.png`, `assets/splash.png`, `assets/splash-dark.png`, `assets/brand/*`. Código: `src/theme/theme.tsx` (`DENTIA_BRAND`, `BRAND_ASSETS`) y `src/components/Brand.tsx`. Los colores deben ser idénticos al preset `dentia` del sistema web (`CAMBIOS_WEB.md` W1).

### Qué hace la versión 1.1
Paridad con la web para el flujo completo de consulta (docs/06_APP_MOVIL_V1_1_PARIDAD.md, bloques M1–M8), además de lo ya existente en la v1.0:

- Configurar el servidor de la clínica, login con MFA, elegir sucursal.
- **Cerrar sesión** con confirmación ("si tienes una consulta abierta, quedará en borrador"); limpia sesión, caché y Dentia sin importar si el servidor respondió.
- **Mis preferencias** (todos los usuarios, sincronizadas entre dispositivos vía `GET/PUT /me/preferences`): Dentia activado/desactivado, voz/velocidad/volumen, tema (según el teléfono / claro / oscuro), tiempo de bloqueo. **Clínica** (servidor, estado de IA) separado y solo para `branding.manage`/`ai.configure`.
- **Agenda completa**: crear cita (buscar paciente o crear uno rápido, profesional, tipo de cita, horarios libres reales o hora manual), reprogramar, cancelar/no asistió con motivo, confirmar — solo las transiciones válidas según la máquina de estados del backend. Vista semana simple (7 días) además del día. Llamar/WhatsApp al paciente desde la cita.
- **Iniciar atención** de tres formas: desde una cita (Reservada/Confirmada/En sala, con confirmación si aún no ha pasado por sala), desde la ficha sin cita (urgencia), o recuperando la que ya tenías abierta (barra "En consulta" visible en toda la app). Solo una consulta abierta por profesional (aviso, no bloqueo del backend).
- **Pantalla Consulta** con Resumen (alertas, motivo, últimas atenciones, plan de tratamiento), Dictado (igual que antes) y Nota.
- **Odontograma** FDI táctil (permanente/temporal), selección de varias superficies o pieza completa, estado (diagnóstico/planificado/realizado), **cambiar** un hallazgo vigente, **anular con motivo obligatorio**, deshacer 5 s después de capturar, historial real por pieza (fecha, autor, origen).
- **Fotografía clínica** con la cámara → pestaña Imágenes del expediente.
- **Dictado con IA** en la atención: grabar → transcribir → interpretar → aceptar/rechazar propuestas (con aviso de alertas antes de aceptar procedimientos).
- **Nota de la consulta** (SOAP) prellenada con lo capturado ese día (motivo, hallazgos, procedimientos, propuestas de IA aceptadas); guardar borrador o finalizar. Finalizar **cierra la consulta** (marca la cita como Atendida) y muestra las validaciones del backend tal cual (propuestas sin revisar, alertas sin confirmar, nota sin finalizar). Una nota final no se edita en el teléfono ("Corregir en la web").
- **Próxima cita** al cerrar la consulta: agendar (fecha sugerida +7 días, con recordatorio por WhatsApp), dejar un pendiente para recepción, o marcar que no se requiere.
- **Dentia por voz**: "abre el expediente de…", "agenda de mañana", "¿quién sigue?", "Laura Sánchez ya llegó", "cancela".
- Seguridad: sin capturas de pantalla, bloqueo con huella/rostro/PIN, `https` obligatorio fuera de desarrollo.

### Qué queda para después (y por qué)
- Editar el contenido de una propuesta de IA (hoy: aceptar/rechazar; editar en la web).
- Agendar una cita por voz ("Dentia, agenda a Laura mañana a las 10"): el intérprete de órdenes de Dentia todavía no tiene esa intención.
- Una cuadrícula de horas tocable como la de la web (`CalendarGrid.tsx`) y una vista semana con esa misma cuadrícula: por ahora la hora se elige de los huecos libres reales o se escribe a mano.
- Selector de idioma y de tamaño de letra propios de la app: se guardan como preferencia, pero ni la web ni el teléfono tienen todavía textos en otro idioma que no sea español (docs/PENDIENTES_CLINICOS.md #50).
- Consentimientos con firma, cobranza y reportes: se usan mejor en la computadora; la app es para el sillón y la recepción.
- Palabra de activación "Dentia" siempre escuchando → §9.

---

## 1. Software a instalar (Windows, máquina de desarrollo)

Instala en este orden. Los comandos `winget` van en **PowerShell** (no requiere administrador salvo donde se indica).

| # | Software | Para qué | Cómo |
|---|---|---|---|
| 1 | **Node.js 22 LTS** | Expo CLI, npm | `winget install OpenJS.NodeJS.LTS` → verifica `node -v` |
| 2 | **Git for Windows** | Control de versiones; Claude Code lo usa para su herramienta Bash | `winget install Git.Git` |
| 3 | **Microsoft OpenJDK 17** | Compilar Android en local | `winget install Microsoft.OpenJDK.17` (o `choco install -y microsoft-openjdk17`) |
| 4 | **Android Studio** | SDK de Android, emulador, `adb` | `winget install Google.AndroidStudio` |
| 5 | **EAS CLI** | Compilar en la nube de Expo y subir a Google Play | `npm install -g eas-cli` → `eas login` |
| 6 | **Claude Code** | Programar con Claude en el repo | `irm https://claude.ai/install.ps1 \| iex` (ver §2) |
| 7 | **VS Code** (ya lo usas) + extensiones *Expo Tools*, *ESLint*, *Claude Code* | Editor | Marketplace de VS Code |
| 8 | **Tailscale** (servidor de la clínica y teléfonos) | Acceso seguro sin abrir puertos | `winget install Tailscale.Tailscale`; en Android, Google Play |
| 9 | *(opcional)* **scrcpy** | Ver la pantalla del teléfono en la PC para demos | `winget install Genymobile.scrcpy` |

### 1.1 Configurar Android Studio (una sola vez)
1. Abre Android Studio → **More Actions → SDK Manager**.
2. Pestaña **SDK Platforms**: marca **Android 16 (Baklava) → Android SDK Platform 36** y *Sources for Android 36*.
3. Pestaña **SDK Tools**: **Android SDK Build-Tools 36**, **Android Emulator**, **Android SDK Platform-Tools**.
4. Variables de entorno de usuario (*Editar las variables de entorno de esta cuenta*):
   - `ANDROID_HOME` = `%LOCALAPPDATA%\Android\Sdk`
   - Agrega a `Path`: `%LOCALAPPDATA%\Android\Sdk\platform-tools`
5. Abre una PowerShell **nueva** y verifica: `adb --version`, `java -version` (17).
6. **Device Manager → Create device** → Pixel 8 con imagen **API 36 "Google Play"** (para probar como un teléfono real).

### 1.2 Teléfono Android de pruebas
1. *Ajustes → Acerca del teléfono →* toca **Número de compilación** 7 veces.
2. *Opciones de desarrollador →* **Depuración USB** (y *Depuración inalámbrica* si quieres sin cable).
3. Conéctalo y acepta la huella RSA; `adb devices` debe listarlo.
4. Instala **Tailscale** desde Google Play y entra con la cuenta de la clínica (§4.2).
5. Prueba también en un teléfono modesto (Android 10–12, 3–4 GB RAM): la app soporta desde Android 8 (minSdk 26).

---

## 2. Integrar el proyecto y Claude Code

### 2.1 Ubicación en el repositorio
Copia la carpeta del zip como **`C:\workspace\dentia-system\mobile\`**, al lado de `backend/`, `frontend/` y `e2e/`:

```
dentia-system/
├─ backend/          FastAPI (sin cambios salvo §7)
├─ frontend/         React web
├─ e2e/              Playwright
├─ mobile/           ← app nueva (Expo)
│   ├─ CLAUDE.md     reglas específicas del móvil
│   └─ .claude/settings.json
├─ docs/
│   └─ 05_APP_MOVIL.md  ← copia este archivo aquí
└─ CLAUDE.md         reglas generales (ya existe)
```

### 2.2 Instalar Claude Code
```powershell
irm https://claude.ai/install.ps1 | iex
# abre una PowerShell nueva
claude --version
claude doctor          # diagnóstico de instalación y configuración
```
- Requiere plan **Pro, Max, Team, Enterprise o una cuenta de Console** (el plan gratuito no incluye Claude Code).
- La primera vez, `claude` abre el navegador para iniciar sesión.
- Con Git for Windows instalado, Claude Code usa Git Bash; sin él, PowerShell.
- Alternativas: `winget install Anthropic.ClaudeCode` (no se actualiza solo) o la app de escritorio de Claude.

### 2.3 Cómo trabaja Claude Code con este proyecto
- Al ejecutar `claude` dentro de `C:\workspace\dentia-system`, lee el `CLAUDE.md` de la raíz; cuando trabaja en `mobile/` también toma `mobile/CLAUDE.md`.
- `mobile/.claude/settings.json` ya permite sin preguntar los comandos seguros (`npm run typecheck`, `npm test`, `npx expo install`, `npx expo-doctor`), **pregunta** antes de `eas build`/`eas submit`/`git push` y **prohíbe** leer `.env`, `secrets/` y llaves de firma.

### 2.4 Primeras instrucciones para Claude Code (cópialas en orden)
```text
1) Lee mobile/CLAUDE.md y docs/05_APP_MOVIL.md. En mobile/ corre "npm install" y
   "npx expo install --fix", luego "npm run typecheck" y corrige todos los errores.

2) Con el backend corriendo en localhost:8001, genera src/api/schema.d.ts con
   openapi-typescript y compara contra src/api/types.ts y cada VERIFICAR de
   src/api/endpoints.ts. Dime qué no coincide antes de cambiar nada.

3) Implementa los cambios B1–B5 de docs/05_APP_MOVIL.md §7 en el backend, cada uno
   con su prueba pytest, sin romper las 298 pruebas existentes ni el frontend web.

4) Corre npm test y npx expo-doctor en mobile/ y deja todo en verde.

5) Aplica la marca DENT-IA al sistema web siguiendo CAMBIOS_WEB.md (bloques W1–W7)
   y confirma que el preset "dentia" del backend y del frontend tiene exactamente los
   mismos colores que DENTIA_BRAND en mobile/src/theme/theme.tsx.
```
Pide **un paso a la vez** y revisa el diff de cada uno (`git diff`) antes de seguir; es el mismo "vertical slice" que usaste en las fases 0–12.

---

## 3. Primer arranque

```powershell
cd C:\workspace\dentia-system\mobile
npm install
npx expo install --fix        # ajusta cada paquete a la versión exacta de SDK 57
npm run typecheck
npm test                      # pruebas del intérprete de órdenes de Dentia
npx expo-doctor
eas init                      # crea el proyecto en expo.dev y guarda su projectId
```

> **Antes del primer build:** cambia `BASE_PACKAGE` en `app.config.ts` (`mx.dentia.app`) por un identificador tuyo, p. ej. `mx.tuclinica.dentia`. **Google Play no permite cambiarlo después.**

La marca DENT-IA ya está aplicada (§0.1): no reemplaces los íconos ni el splash salvo que cambie el logo oficial.

---

## 4. Conectar el teléfono con el servidor de la clínica

### 4.1 En desarrollo (misma Wi-Fi)
1. En el servidor, arranca el backend escuchando en la red, no solo en localhost:
   ```powershell
   uvicorn app.main:app --host 0.0.0.0 --port 8001
   ```
2. Abre el puerto en el Firewall de Windows (PowerShell **como administrador**):
   ```powershell
   New-NetFirewallRule -DisplayName "DENT-IA API 8001" -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow -Profile Private
   ```
3. Averigua la IP del servidor (`ipconfig`, p. ej. `192.168.1.50`).
4. En la app (build **development**): *Servidor* → `http://192.168.1.50:8001` → **Probar y guardar**.

El build de desarrollo es el único que acepta `http://`. Los builds `preview` y `production` exigen `https://` (Android bloquea texto plano y no queremos datos clínicos sin cifrar en la Wi-Fi).

### 4.2 En pruebas y producción (recomendado: Tailscale)
1. Crea una cuenta de Tailscale para la clínica; instala Tailscale en el **servidor** y en cada **teléfono**.
2. En la consola de Tailscale: activa **MagicDNS** y **HTTPS Certificates**.
3. En el servidor, publica la API solo dentro de tu red privada con HTTPS:
   ```powershell
   tailscale serve --bg 8001
   ```
   Queda en `https://<nombre-servidor>.<tu-red>.ts.net` con certificado válido.
4. En la app: *Servidor* → `https://<nombre-servidor>.<tu-red>.ts.net`.

Así el odontólogo puede revisar la agenda desde casa sin que el servidor quede expuesto a internet. **No uses `tailscale funnel`** con datos reales: eso sí lo publica a internet (solo es aceptable para el servidor de demostración de §8.5, con datos ficticios).

Alternativa si la clínica ya tiene dominio: un proxy inverso (Caddy o IIS) con certificado válido dentro de la red local y DNS interno. Los certificados autofirmados **no** funcionan en Android sin configuración extra; evítalos.

---

## 5. Formas de ejecutar la app

| Opción | Cuándo usarla | Cómo |
|---|---|---|
| **A. Development build con EAS** (recomendado) | Día a día, en tu teléfono real | `eas build --profile development --platform android` → instala el APK que te da el enlace/QR → `npx expo start --dev-client` → abre la app y elige tu PC |
| **B. Build local** | Sin esperar la nube, con cable USB | `npx expo run:android` (requiere §1.1) |
| **C. Emulador** | Probar pantallas sin teléfono | Inicia el AVD API 36 y corre `npx expo run:android` |
| **D. APK de pruebas (preview)** | Que la doctora y recepción lo prueben sin Metro | `eas build --profile preview --platform android` → comparte el enlace |

Tras instalar un development build, los cambios de código se ven al instante (Fast Refresh). Solo necesitas otro build cuando cambias `app.config.ts`, permisos o agregas un paquete con código nativo.

> En el emulador, `localhost` es el propio emulador: para llegar al backend de tu PC usa `http://10.0.2.2:8001`.

---

## 6. Plan de pruebas

### 6.1 Automáticas
```powershell
npm run typecheck     # TypeScript estricto, 0 errores
npm test              # 75 casos: intérprete de Dentia, logout, agenda, odontograma, nota, preferencias, etc.
npx expo-doctor       # dependencias alineadas con SDK 57
```
Y en el backend, `pytest` completo (834 pruebas al cierre de la v1.1, incluye B7–B12 del contrato móvil).

### 6.2 Checklist manual (teléfono real, en la Wi-Fi de la clínica y luego por Tailscale)

**v1.0**
- [ ] Servidor: dirección mala → mensaje claro; buena → pasa a login.
- [ ] Login correcto, contraseña mala, 6 intentos (rate limit), **MFA** con `admin_clinica`.
- [ ] Cerrar la app y volver a abrirla → entra sin pedir contraseña (refresh). Esperar > 8 h → pide login.
- [ ] Dejar la app en segundo plano más que el tiempo de bloqueo elegido en Mis preferencias → pide huella/PIN.
- [ ] Intentar captura de pantalla en la ficha → Android la bloquea.
- [ ] Usuario de **recepción**: ve agenda y "Llegó", **no** ve "Iniciar atención" ni "Dictar"; la cita muestra "Lo inicia el odontólogo".
- [ ] Agenda: hoy/mañana/ayer, deslizar para actualizar, "Llegó" cambia a *En sala* también en la web.
- [ ] "Iniciar atención" abre la pantalla Consulta (Resumen/Dictado/Nota).
- [ ] Ficha: barra de alertas visible con un paciente alérgico; al abrir Consulta, tarjeta de alertas bloqueante hasta tocar "Enterado".
- [ ] Odontograma: tocar pieza y superficie, registrar caries en 36-O, verla en la web; pieza "Ausente" dibuja recuadro completo; historial muestra autor/IA.
- [ ] Foto: tomarla y verla en la pestaña Imágenes de la web.
- [ ] Dictado: el ejemplo de docs/03 §1 genera propuestas; aceptar una alergia la agrega al expediente; rechazar no guarda nada; procedimiento con paciente alérgico muestra la alerta antes.
- [ ] Apagar Ollama → mensaje claro y el texto se conserva.
- [ ] Dentia: "abre el expediente de *nombre*" (1 resultado → abre tras 3 s; varios → lista), decir "cancela" dentro de los 3 s, "agenda de mañana", "¿quién sigue?", "*nombre* ya llegó".
- [ ] Marca: ícono y splash DENT-IA (claro y oscuro), ícono temático monocromo (Android 13+: *Fondo de pantalla y estilo → Íconos temáticos*), logo de la clínica en el login cuando la sucursal subió uno, y "con tecnología DENT-IA".
- [ ] Modo oscuro del teléfono, letra grande (Ajustes → Pantalla → Tamaño de fuente) y TalkBack leen bien los botones.
- [ ] Sin red → mensaje "¿Estás en la red de la clínica o en la VPN?".

**v1.1 (docs/06_APP_MOVIL_V1_1_PARIDAD.md)**
- [ ] **Cerrar sesión** con red, sin red y con token vencido → Login; reabrir la app pide contraseña.
- [ ] Recepción cambia idioma (texto informativo) y voz de Dentia; no ve "Clínica".
- [ ] Recepción crea cita desde el botón "+ Nueva cita"; conflicto de horario muestra alternativas.
- [ ] Reprogramar y cancelar (con motivo) se reflejan en la web.
- [ ] Odontólogo inicia atención: desde cita Reservada/Confirmada (con "¿ya está en el sillón?"), desde cita En sala, desde la ficha sin cita, por voz.
- [ ] Con una consulta ya abierta, intentar iniciar otra → "¿Volver a ella o dejarla en borrador?".
- [ ] Barra "En consulta" visible al navegar a otras pantallas y al reabrir la app.
- [ ] Al iniciar se muestran alertas y hay que tocar "Enterado".
- [ ] Odontograma: registrar caries en 36-O y 36-M a la vez, cambiarla a obturación, anular otra con motivo, deshacer en los primeros 5 s; todo con historial en la web.
- [ ] Sin consulta abierta el odontograma muestra el botón "Iniciar atención para editar".
- [ ] Nota: prellenada al entrar con el motivo, hallazgos y propuestas aceptadas del día; guardar borrador y volver después.
- [ ] Cerrar consulta con propuestas IA pendientes → mensaje del backend tal cual, sin cerrar.
- [ ] Cerrar consulta con alertas sin confirmar o sin nota finalizada → mensaje del backend tal cual.
- [ ] Finalizar nota → no editable en el teléfono; la cita pasa a Atendida en la web.
- [ ] Al cerrar aparece "¿Agendar la próxima cita?": agendar con fecha +7 días sugerida y WhatsApp, "Recordar después" (aparece en la lista de espera de la web), "No requiere".
- [ ] Botón Atrás de Android en Consulta → "¿Salir de la consulta?" (no la cierra).
- [ ] Ficha del paciente: botones rápidos Iniciar atención/Dictar, Nueva cita, Llamar (si el paciente tiene teléfono), Tomar foto.

---

## 7. Cambios necesarios en el backend

La documentación del backend no fija algunos detalles que el móvil necesita. Pídeselos a Claude Code (§2.4, paso 3), **cada uno con prueba**:

| # | Cambio | Motivo |
|---|---|---|
| **B1** | Si llega el encabezado `X-Client: dentia-mobile`, `/auth/login`, `/auth/login/mfa` y `/auth/refresh` devuelven `access_token` **y** `refresh_token` en el JSON; `/auth/refresh` y `/auth/logout` aceptan `{"refresh_token": "..."}` en el cuerpo. | Una app nativa no maneja cookies httpOnly como el navegador. Si hoy ya van en el cuerpo, no hay nada que hacer. La rotación y el hash SHA-256 del refresh se mantienen igual. |
| **B2** | `/ai/transcribe` acepta `audio/mp4`, `audio/m4a` y `audio/aac` además de `audio/webm` (y el campo multipart `audio`, o ajustar la app al nombre real). | Android graba AAC en contenedor MP4; `faster-whisper` lo decodifica con `av` sin cambios. |
| **B3** | `GET /appointments` acepta `date_from`/`date_to` y cada cita incluye `patient_name` y `provider_name`. | Evita una petición por cita para pintar la agenda. |
| **B4** | `GET /me/clinics` incluye `clinic_name`, `role` y la lista `permissions` de esa sucursal. | La app oculta botones según permisos (el backend sigue autorizando). |
| **B5** | `/auth/login` con MFA devuelve `{"mfa_required": true, "mfa_token": "..."}` y `/auth/login/mfa` recibe `{mfa_token, code}`. | Si el flujo actual usa otros nombres, se ajusta la app en lugar del backend. |
| **B6** | Servidor de **demostración** (base `dentia_demo`, `python -m app.seed`, usuario de revisión) accesible por HTTPS público. | Google revisa la app iniciando sesión (§8.5). |

No se necesita CORS para la app nativa (no envía `Origin`). Mantén `CORS_ORIGINS` como está.

---

## 8. Publicar en Google Play, paso a paso

### 8.1 Antes de empezar: ¿pública o privada?
- **Pública en Google Play** (lo que sigue): cualquier clínica puede descargarla; cada una configura su propio servidor.
- **Privada (Managed Google Play)**: si la app es solo para tu clínica, se puede publicar como app privada para la organización. Evita la revisión pública y las apps permanentemente privadas quedan exentas del requisito de API objetivo, pero requiere administrar los teléfonos con Android Enterprise. Para varias clínicas, la pública es más simple.

### 8.2 Cuenta de desarrollador
1. Entra a **play.google.com/console** con una cuenta de Google de la empresa (no personal del día a día).
2. Pago único de **25 USD**.
3. Tipo de cuenta:
   - **Organización** (recomendado si la clínica o empresa está constituida): pide **D-U-N-S Number** (gratuito, se tramita en dnb.com; tarda días o semanas), sitio web y verificación de la organización. **No** tiene el requisito de 12 testers.
   - **Personal**: identificación oficial. Las cuentas personales creadas después del 13-nov-2023 deben hacer una **prueba cerrada con al menos 12 testers durante 14 días seguidos** antes de poder publicar en producción.
4. Completa la verificación de identidad y, en el inicio de Play Console, revisa que la app quede **registrada** en *Android developer verification* (Google la exige y registra automáticamente la mayoría de las apps de Play).

### 8.3 Requisitos técnicos (ya resueltos en el proyecto)
- **targetSdkVersion 36** (Android 16): obligatorio para apps nuevas y actualizaciones desde el 31-ago-2026 → `expo-build-properties` en `app.config.ts`.
- Formato **Android App Bundle (.aab)** → perfil `production` de `eas.json`.
- **Firma**: deja que EAS genere y guarde la llave de subida (*upload key*) y activa **Play App Signing** (Google firma lo que se instala). Respalda las credenciales con `eas credentials` y guárdalas fuera del repo.
- Permisos mínimos: solo `RECORD_AUDIO` y `CAMERA`; se bloquean almacenamiento, ubicación y ventanas superpuestas.
- `allowBackup: false` para que los datos de la app no se copien a respaldos.

### 8.4 Crear la app en Play Console
*Inicio → Crear app*: nombre **DENT-IA: Gestión Odontológica**, idioma **Español (Latinoamérica)**, **App**, **Gratis**, acepta políticas.

### 8.5 Contenido de la app (*Política → Contenido de la app*)
| Formulario | Qué responder |
|---|---|
| **Política de privacidad** | URL pública (página en el sitio de la clínica). Plantilla en `store-listing/politica-privacidad.md`. Obligatoria por manejar datos de salud. |
| **Acceso a la app** | "Todas o algunas funciones están restringidas" → instrucciones: dirección del **servidor de demostración** (B6), usuario y contraseña de un **odontólogo de prueba sin MFA**, y que los datos son ficticios. Sin esto Google rechaza la app porque no puede entrar. |
| **Anuncios** | No contiene anuncios. |
| **Clasificación de contenido** | Cuestionario IARC; categoría "Referencia, noticias o educativo" / utilidad; sin violencia, etc. |
| **Público objetivo** | Solo **18 años o más** (uso profesional). |
| **Seguridad de los datos** | Ver tabla 8.6. |
| **Apps de salud** (*Health apps declaration*) | Obligatoria. Marca la categoría de gestión de servicios de salud / expediente clínico que más se ajuste; **no** "dispositivo médico" salvo que tengas registro sanitario como tal. |
| **Apps gubernamentales, financieras, etc.** | No aplica. |

Si no declaras la app como dispositivo médico, la **descripción** debe incluir un aviso claro de que la app no es un dispositivo médico y no diagnostica, trata, cura ni previene ninguna condición (ya incluido en `store-listing/ficha-google-play.md`).

### 8.6 Seguridad de los datos (respuestas sugeridas)
- ¿Recopila o comparte datos? **Sí recopila**, **no comparte** con terceros.
- ¿Cifrado en tránsito? **Sí** (HTTPS obligatorio en producción).
- ¿El usuario puede pedir que se borren? **Sí**, mediante la clínica (administrador del servidor). Indica el correo de contacto.
- Tipos de datos (todos con propósito **"Funcionalidad de la app"**, recopilados, no compartidos, no opcionales):
  - Información personal: nombre, correo (del usuario profesional).
  - **Información de salud** (expedientes de pacientes que el profesional consulta y captura).
  - **Audio**: grabaciones de voz (dictado), enviadas al servidor de la clínica y descartadas tras transcribir.
  - **Fotos**: fotografías clínicas.
- Aclara en la política que los datos se guardan en el **servidor de cada clínica**, no en servidores del desarrollador.

### 8.7 Ficha de la tienda (*Crecer → Presencia en la tienda → Ficha principal*)
Textos listos en `store-listing/ficha-google-play.md`. Recursos gráficos:
- Ícono 512×512 PNG → `store-listing/icono-512.png` (isotipo DENT-IA, ya generado).
- Gráfico destacado 1024×500 → `store-listing/grafico-destacado-1024x500.png` (logo DENT-IA con franja de degradado, ya generado).
- **2 a 8 capturas de teléfono** (y de tablet de 7" y 10" si quieres aparecer en tablets): tómalas del **servidor de demostración** con pacientes ficticios — nunca con datos reales. Desactiva temporalmente `SecureScreen` en un build de demo o usa el emulador, porque FLAG_SECURE bloquea capturas.
- Categoría: **Medicina**. Correo de contacto obligatorio.

### 8.8 Compilar y subir
```powershell
eas build --profile production --platform android     # genera el .aab firmado, versionCode automático
```
- **Primera subida: manual.** Play Console → *Pruebas → Pruebas internas → Crear versión* → sube el `.aab` descargado de expo.dev. (La API de Google no acepta la primera versión de una app.)
- Siguientes subidas, automáticas:
  1. Google Cloud Console → crea una **cuenta de servicio** y descarga su llave JSON.
  2. Play Console → *Usuarios y permisos* → invita el correo de esa cuenta de servicio con permiso de **lanzar versiones**.
  3. Guarda la llave en `mobile/secrets/play-service-account.json` (ya está en `.gitignore` y bloqueada para Claude Code).
  4. `eas submit --profile production --platform android` → la sube como **borrador** a la pista interna.

### 8.9 Pistas de prueba y producción
1. **Prueba interna** (hasta 100 testers, sin revisión, minutos): tú, la doctora, recepción.
2. **Prueba cerrada** (*Alpha*): crea la lista de correos de Google de los testers y comparte el enlace de participación. Con cuenta **personal**: mínimo **12 testers que acepten y sigan inscritos 14 días seguidos** — recluta 15–20 (si bajas de 12, el conteo se reinicia). Pide que la abran y la usen; Google pregunta después qué probaron.
3. **Solicitar acceso a producción** (aparece en el panel al cumplir lo anterior) → responde el cuestionario.
4. **Producción**: crea la versión, elige países (México y los que quieras) y usa **lanzamiento por etapas** (20 % → 50 % → 100 %).
5. La revisión de Google tarda de horas a varios días; con apps de salud, cuenta con más.

Calendario realista con cuenta personal nueva: **3–4 semanas** desde la primera subida hasta producción.

### 8.10 Actualizaciones
- Cambios solo de JavaScript (pantallas, textos, lógica): puedes usar **EAS Update** para corregir sin pasar por la tienda (opcional; agrega `expo-updates`).
- Cambios nativos (permisos, paquetes nuevos, SDK): nuevo `eas build` + `eas submit`.
- Cada agosto Google sube el **API objetivo**: actualiza al SDK de Expo vigente con `npx expo install expo@latest --fix` antes de esa fecha.

---

## 9. Fase 2: "Dentia" siempre escuchando en el teléfono

En la web, Dentia escucha al iniciar sesión. En un teléfono eso implica: un **servicio en primer plano de micrófono** con notificación permanente, más batería, y justificarlo ante Google Play. Plan propuesto:
1. Detector de palabra de activación **en el dispositivo** (p. ej. Porcupine de Picovoice con la palabra personalizada "Dentia" en español, o un modelo openWakeWord): solo detecta la palabra; no envía audio a nadie.
2. Al detectarla, se usa el mismo flujo de hoy (grabar → servidor → intérprete → 3 s).
3. Activo solo con la app abierta en la **tablet del consultorio** (modo kiosco), no en segundo plano en teléfonos personales.
Requiere un development build nuevo (módulo nativo) y un ADR en `docs/adr/`.

---

## 10. Problemas comunes

| Síntoma | Causa probable y solución |
|---|---|
| "No se pudo conectar con el servidor" | Teléfono fuera de la Wi-Fi/VPN; uvicorn sin `--host 0.0.0.0`; firewall; en el emulador usar `10.0.2.2`. |
| Funciona con `http://` en dev pero no en preview | Esperado: preview/production exigen `https://` (§4.2). |
| Login correcto pero "no devolvió el token de sesión" | Falta el cambio **B1** en el backend. |
| Dictado: error 415/422 en `/ai/transcribe` | Falta **B2** (formato m4a o nombre del campo). |
| Dentia habla con voz masculina o en inglés | Ajustes → Voz de Dentia; o instala datos de voz en español en *Ajustes de Android → Texto a voz*. |
| `npx expo run:android` falla con JDK | `java -version` debe ser 17 y `JAVA_HOME` apuntar a esa instalación. |
| `SDK location not found` | Falta `ANDROID_HOME` (§1.1). Abre una terminal nueva. |
| Google rechaza: "no pudimos acceder" | Servidor demo caído o credenciales de *Acceso a la app* incorrectas (§8.5). |
| Google rechaza por permisos | Asegúrate de que solo estén `RECORD_AUDIO` y `CAMERA` y que la política de privacidad explique ambos. |

---

## 11. Costos

| Concepto | Costo |
|---|---|
| Cuenta de Google Play | 25 USD, pago único |
| EAS Build/Submit | Plan gratuito con builds limitados y en cola; planes de pago si compilas mucho |
| Claude Code | Incluido en planes Pro/Max/Team/Enterprise de Claude |
| Tailscale | Plan gratuito para equipos pequeños |
| D-U-N-S (cuenta de organización) | Gratuito |
