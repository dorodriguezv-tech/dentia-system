from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.deps import require_permission
from app.modules.iam.models import User
from app.modules.version_info import service
from app.modules.version_info.schemas import VersionInfoOut

router = APIRouter(tags=["version_info"])


@router.get("/version-info", response_model=VersionInfoOut)
async def get_version_info(
    _actor: User = Depends(require_permission("version_info.read")),
    settings: Settings = Depends(get_settings),
) -> VersionInfoOut:
    return service.get_version_info(settings)
