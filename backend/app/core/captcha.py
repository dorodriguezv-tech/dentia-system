"""Verificacion de Cloudflare Turnstile para el login (Fase 13, "Publicacion web").

Protege /auth/login contra intentos automatizados (bots/fuerza bruta) sobre
cualquiera de las 3 cuentas de la clinica, administrador incluido -- Turnstile no
puede condicionarse por rol porque el rol se conoce despues de autenticar.
Complementa, sin reemplazar, el limite de 5 intentos/15 min por correo
(app/modules/iam/rules.py::MAX_LOGIN_FAILURES).

Sin TURNSTILE_SECRET_KEY configurada (desarrollo/pruebas) la verificacion se
omite por completo -- no se exige turnstile_token en el login.
"""

import httpx

from app.core.config import get_settings


async def verify_turnstile(token: str | None, *, remote_ip: str | None) -> bool:
    settings = get_settings()
    if not settings.turnstile_secret_key:
        return True
    if not token:
        return False

    data = {"secret": settings.turnstile_secret_key, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(settings.turnstile_verify_url, data=data)
        response.raise_for_status()
        return bool(response.json().get("success"))
    except httpx.HTTPError:
        # Cloudflare inalcanzable: falla cerrado (no se deja pasar un login sin
        # verificar) -- mismo criterio que un token invalido.
        return False
