# DENT-IA — app móvil

Cliente Android (iOS listo para después) del Sistema Inteligente de Gestión Odontológica
DENT-IA. Expo SDK 57 · React Native 0.86 · TypeScript · expo-router.

**Guía completa (instalación, pruebas, Claude Code, Google Play):** [`docs/05_APP_MOVIL.md`](docs/05_APP_MOVIL.md)
**Reglas para Claude Code:** [`CLAUDE.md`](CLAUDE.md)

## Arranque rápido
```powershell
npm install
npx expo install --fix
npm run typecheck
npm test
eas init
eas build --profile development --platform android   # instala el APK en tu teléfono
npx expo start --dev-client
```
En la app: Servidor → `http://<IP-del-servidor>:8001` (solo en desarrollo) → login.

## Estructura
```
app/                     pantallas (expo-router)
  _layout.tsx            proveedores, tema, bloqueo
  index.tsx              puerta: servidor → login → sucursal → agenda
  servidor.tsx login.tsx sucursal.tsx
  (app)/                 pestañas: Agenda, Pacientes, Dentia, Ajustes
  paciente/[id].tsx      ficha, alertas, odontograma, foto
  atencion/[id].tsx      dictado IA y propuestas
src/api/                 cliente HTTP, endpoints, tipos
src/store/session.ts     sesión (SecureStore)
src/theme/               marca DENT-IA por defecto, marca de la clínica, modo oscuro
src/components/Brand.tsx logos DENT-IA / clínica, "con tecnología DENT-IA"
assets/brand/            logo oficial DENT-IA (color, blanco, isotipo)
src/components/          UI y odontograma SVG
src/voice/               Dentia: intérprete, voz, grabación, confirmación 3 s
src/security/            FLAG_SECURE, bloqueo, biometría
store-listing/           textos, ícono y gráfico para Google Play
```
