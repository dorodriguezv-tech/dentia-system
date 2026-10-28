from app.core.config import Settings
from app.modules.version_info.schemas import VersionInfoOut


def get_version_info(settings: Settings) -> VersionInfoOut:
    """Funcion pura (sin BD): la version desplegada es 100% derivada de
    configuracion/entorno, nunca algo que la app escriba o lea de una tabla."""
    return VersionInfoOut(version=settings.app_version, environment=settings.environment)
