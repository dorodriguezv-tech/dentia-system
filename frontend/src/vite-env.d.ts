/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  // Cloudflare Turnstile (Fase 13, "Publicacion web"): clave publica (sitekey),
  // segura de exponer en el bundle. Sin ella, el login no muestra el captcha --
  // debe coincidir con TURNSTILE_SECRET_KEY del backend (o ambas vacias).
  readonly VITE_TURNSTILE_SITE_KEY?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
