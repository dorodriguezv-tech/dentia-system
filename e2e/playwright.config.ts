import { defineConfig, devices } from '@playwright/test'

/**
 * CLAUDE.md Fase 12: E2E del flujo completo contra un backend real (con el
 * asistente de IA en modo AI_FAKE_MODE -- ver backend/app/ai/ollama_client.py,
 * nunca requiere Ollama/Whisper reales ni red) y el frontend servido por Vite.
 * Ambos se levantan automaticamente (`webServer`) contra la misma base de datos
 * de desarrollo que usa `npm run dev` -- no hay una base separada para E2E
 * todavia (ver docs/PENDIENTES_CLINICOS.md).
 *
 * Correccion (Fase 12.1, docs/06): puertos propios (8011/5185), distintos de los
 * 8001/5174 que se usan para desarrollo manual. Antes, si ya habia un backend o
 * frontend de desarrollo corriendo en 8001/5174 (lo normal si alguien esta
 * probando la app a mano), `reuseExistingServer` lo reutilizaba tal cual -- sin
 * AI_FAKE_MODE=true, asi que el paso de dictado de full-flow.spec.ts intentaba
 * usar el Ollama real y fallaba de forma intermitente e imposible de diagnosticar
 * por el navegador. Puertos dedicados evitan el choque por completo.
 */
const BACKEND_PORT = 8011
const FRONTEND_PORT = 5185

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['list']],
  timeout: 60_000,
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: `"../backend/.venv/Scripts/python.exe" -m uvicorn app.main:app --port ${BACKEND_PORT}`,
      cwd: '../backend',
      url: `http://localhost:${BACKEND_PORT}/api/v1/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        AI_FAKE_MODE: 'true',
        // Fase 13.6 "Afinacion": mismo patron que AI_FAKE_MODE -- sin audio/
        // modelos reales, voice.spec.ts dispara "fake_wake"/"fake_order" por
        // el WebSocket real (ver window.__dentiaTestSend en
        // useVoiceSession.ts). Cuenta regresiva/seguimiento cortas para que
        // la prueba no tenga que esperar los 3 s/8 s reales de produccion.
        VOICE_FAKE_MODE: 'true',
        VOICE_CAPTURE_COUNTDOWN_S: '0.1',
        // Generoso (no 0.5 s) a proposito: voice.spec.ts necesita una ventana
        // real para que Playwright alcance a comprobar el estado "listening"
        // antes de que la sesion vuelva sola a pasivo.
        VOICE_FOLLOWUP_S: '8',
        // Sin esto, el backend solo acepta CORS desde :5174 (la lista blanca de
        // backend/app/core/config.py, estricta a proposito -- CLAUDE.md sec. 5) y
        // el navegador bloquea en silencio toda peticion del frontend E2E en :5185
        // (incluido el login, por eso fallaban tantas pruebas a la vez).
        CORS_ORIGINS: `["http://localhost:${FRONTEND_PORT}"]`,
      },
    },
    {
      command: `npm run dev -- --port ${FRONTEND_PORT} --strictPort`,
      cwd: '../frontend',
      url: `http://localhost:${FRONTEND_PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        VITE_API_URL: `http://localhost:${BACKEND_PORT}/api/v1`,
      },
    },
  ],
})
