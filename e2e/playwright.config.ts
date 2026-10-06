import { defineConfig, devices } from '@playwright/test'

/**
 * CLAUDE.md Fase 12: E2E del flujo completo contra un backend real (con el
 * asistente de IA en modo AI_FAKE_MODE -- ver backend/app/ai/ollama_client.py,
 * nunca requiere Ollama/Whisper reales ni red) y el frontend servido por Vite.
 * Ambos se levantan automaticamente (`webServer`) contra la misma base de datos
 * de desarrollo que usa `npm run dev` -- no hay una base separada para E2E
 * todavia (ver docs/PENDIENTES_CLINICOS.md).
 */
export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['list']],
  timeout: 60_000,
  use: {
    baseURL: 'http://localhost:5174',
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
      command:
        '"../backend/.venv/Scripts/python.exe" -m uvicorn app.main:app --port 8001',
      cwd: '../backend',
      url: 'http://localhost:8001/api/v1/health',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        AI_FAKE_MODE: 'true',
      },
    },
    {
      command: 'npm run dev',
      cwd: '../frontend',
      url: 'http://localhost:5174',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
})
