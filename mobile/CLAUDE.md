# CLAUDE.md — App móvil DENT-IA (`mobile/`)

Este archivo complementa el `CLAUDE.md` de la raíz del repositorio (reglas clínicas 1–10,
seguridad, temas). Todo lo de la raíz aplica aquí también. Lo de abajo es lo específico
del cliente móvil.

## 1. Qué es
App Android (iOS después) en **Expo SDK 57 + React Native 0.86 + TypeScript estricto +
expo-router**. Es un **cliente** del backend FastAPI existente (`backend/`, `/api/v1`):
no tiene base de datos propia ni lógica clínica propia. Toda regla clínica vive en el
backend; la app solo la respeta y la muestra.

Pantallas: servidor → login (+MFA) → sucursal → pestañas Agenda | Pacientes | Dentia | Ajustes,
más Ficha del paciente (alertas, odontograma, foto) y Atención (dictado + propuestas IA).

## 2. Reglas que NO se negocian
1. **La IA nunca guarda sola** (regla 9): el dictado produce `AiSuggestion` PENDING; el
   usuario acepta o rechaza cada una. Nunca llames a un endpoint clínico de escritura
   con datos que vinieron del modelo sin pasar por `/ai/suggestions/{id}/accept`.
2. **Nada clínico a disco en el teléfono.** Access token solo en memoria; refresh token en
   `expo-secure-store`; la caché de TanStack Query es en memoria (no agregues
   `persistQueryClient`, AsyncStorage ni SQLite con datos de pacientes).
3. **Nada clínico a internet de terceros.** Audio → `/ai/transcribe` del servidor de la
   clínica (faster-whisper). No uses reconocimiento de voz de Google/Apple ni APIs de
   nube para dictado. La síntesis de voz usa voces locales del teléfono.
4. **Sin colores fijos en componentes**: usa `useTheme()`. Excepción: `FINDING_COLORS` y
   `STATUS_COLORS` en `src/theme/theme.tsx` (semánticos, igual que la web).
5. **Objetivos táctiles ≥ 48 dp**, `accessibilityLabel` en todo control sin texto.
6. **Permisos**: muestra/oculta acciones con `hasPermission('modulo.accion')`, pero el
   backend es quien autoriza; un 403 siempre se muestra como error, nunca se ignora.
7. `http://` solo en el build `development` (`usesCleartextTraffic`). preview/production
   exigen `https://`.
8. Nunca cambies `android.package` en `app.config.ts` después del primer envío a Google Play.
9. **Marca DENT-IA** (logo oficial en `assets/brand/`, manual en `docs/MARCA_DENT-IA.md`):
   - El nombre visible del producto se escribe **DENT-IA** (con guion). El asistente de voz
     sigue llamándose **Dentia** (así se pronuncia y así se activa). Los identificadores
     técnicos (`dentia`, `mx.dentia.app`, rutas) no cambian.
   - Usa `<DentiaLogo/>`, `<ClinicLogo/>` y `<PoweredByDentia/>` de `src/components/Brand.tsx`;
     nunca un `require` suelto del PNG ni el logo redibujado.
   - La paleta del preset `dentia` vive en `DENTIA_BRAND` (`src/theme/theme.tsx`) y debe ser
     idéntica a `presets.py`/`presets.ts` del sistema web.
   - El cian `#22AAC2` es decorativo: nunca para texto pequeño (contraste 2.8:1).
   - En modo oscuro: logo blanco y primario `#4FC3D9`.

## 3. Mapa del código
| Ruta | Qué hay |
|---|---|
| `app/` | Rutas de expo-router (cada archivo = pantalla) |
| `src/api/client.ts` | fetch con JWT, `X-Clinic-Id`, refresh single-flight, timeouts |
| `src/api/endpoints.ts` | Una función por endpoint. Comentarios `VERIFICAR` = confirmar contra el backend |
| `src/api/types.ts` | Tipos escritos a mano → reemplazar por `schema.d.ts` generado (tarea 1) |
| `src/store/session.ts` | Zustand + SecureStore |
| `src/theme/theme.tsx` | Tema desde `GET /branding`, preset DENT-IA por defecto, modo oscuro, contraste |
| `src/components/Brand.tsx` | Logo DENT-IA, logo de la clínica con respaldo, "con tecnología DENT-IA", franja de degradado |
| `src/components/Odontogram.tsx` | Odontograma FDI con react-native-svg |
| `src/voice/intents.ts` | Intérprete determinista de órdenes de Dentia (con pruebas) |
| `src/voice/useVoiceCapture.ts` | Grabar (expo-audio) + transcribir en el servidor |
| `src/voice/useImplicitConfirm.ts` | Confirmación implícita de 3 s |
| `src/security/appLock.tsx` | FLAG_SECURE, bloqueo tras 2 min en segundo plano + biometría |

## 4. Comandos
```bash
npm install && npx expo install --fix   # alinear versiones con SDK 57
npm run typecheck                        # tsc --noEmit (debe quedar en 0 errores)
npm test                                 # Jest (jest-expo)
npx expo-doctor                          # salud del proyecto
npx expo start --dev-client              # servidor Metro para el dev build
npx expo run:android                     # build local con Android Studio + USB
eas build --profile development|preview|production --platform android
```
Antes de dar por terminada cualquier tarea: `npm run typecheck && npm test && npx expo-doctor`.

## 5. Tareas pendientes (en orden)
1. **Contrato con el backend.** Con el backend corriendo en desarrollo:
   `npx openapi-typescript http://localhost:8001/api/v1/openapi.json -o src/api/schema.d.ts`
   (o `/openapi.json`, según `docs_urls` en `backend/app/core/config.py`). Compara cada
   tipo de `src/api/types.ts` y cada `VERIFICAR` de `src/api/endpoints.ts` contra el
   router real; ajusta la app (preferido) o propón el cambio mínimo al backend.
2. **Cambios al backend B1–B5** de `docs/05_APP_MOVIL.md` §7 (tokens en el cuerpo para
   `X-Client: dentia-mobile`, aceptar `audio/mp4` en `/ai/transcribe`, campos que falten
   en `/appointments` y `/me/clinics`). Cada uno con su prueba pytest.
3. `npm run typecheck` en 0 y `npm test` en verde.
4. Probar el flujo completo en un teléfono real (checklist de docs/05 §6).
5. Fase 2: palabra de activación "Dentia" en el dispositivo (docs/05 §9).

## 6. Estilo
- Español en UI, comentarios y mensajes de error dirigidos al usuario.
- Mensajes de error accionables ("¿Estás en la red de la clínica?"), nunca un stack trace.
- Componentes pequeños; lógica pura (sin React Native) en archivos aparte con pruebas.
