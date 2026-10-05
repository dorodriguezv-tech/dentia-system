import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings


class StorageBackend(Protocol):
    def save(self, data: bytes, *, subdir: str, suffix: str) -> str:
        """Guarda los bytes y devuelve una clave relativa para leerlos despues."""
        ...

    def read(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


class LocalStorageBackend:
    """Carpeta local storage/ (CLAUDE.md sec. 3). Mas adelante: S3/MinIO."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, *, subdir: str, suffix: str) -> str:
        directory = self.base_dir / subdir
        directory.mkdir(parents=True, exist_ok=True)
        key = f"{subdir}/{uuid.uuid4().hex}{suffix}"
        self._safe_path(key).write_bytes(data)
        return key

    def read(self, key: str) -> bytes:
        return self._safe_path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._safe_path(key).unlink(missing_ok=True)

    def _safe_path(self, key: str) -> Path:
        path = (self.base_dir / key).resolve()
        if path != self.base_dir and self.base_dir not in path.parents:
            raise ValueError("Ruta de almacenamiento invalida")
        return path


def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    storage_dir = Path(settings.storage_dir)
    if not storage_dir.is_absolute():
        backend_dir = Path(__file__).resolve().parents[2]
        storage_dir = (backend_dir / storage_dir).resolve()
    return LocalStorageBackend(storage_dir)
