from pydantic import BaseModel


class VersionInfoOut(BaseModel):
    """Version de DentalCare corriendo en este backend, derivada de
    configuracion/entorno (nunca de una tabla -- no hay nada que persistir).

    `version` viene de `Settings.app_version` (variable de entorno VERSION,
    la misma que `deploy/vps/scripts/deploy.sh` escribe en cada despliegue).
    `environment` viene de `Settings.environment` (ENVIRONMENT en
    docker-compose.yml, "production" en el VPS, "development" en local).
    """

    version: str
    environment: str
