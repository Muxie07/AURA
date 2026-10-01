import uuid
from abc import ABC, abstractmethod
from pathlib import Path

import aiofiles  # type: ignore


class FileStorage(ABC):
    """Abstract interface for file storage (Local vs S3)."""

    @abstractmethod
    async def save_file(self, file_content: bytes, filename: str) -> str:
        """Saves a file and returns its URI or path."""
        pass

    @abstractmethod
    async def load_file(self, path: str) -> bytes:
        """Loads file content."""
        pass

    @abstractmethod
    async def delete_file(self, path: str) -> None:
        """Deletes a file."""
        pass


class LocalFileStorage(FileStorage):
    """
    Local filesystem storage.
    Useful for local dev or Phase 3 prototyping.
    Production will use S3.
    """

    def __init__(self, base_dir: str = "data/uploads"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_safe_path(self, path: str) -> Path:
        """Prevent directory traversal."""
        full_path = (self.base_dir / path).resolve()
        if not str(full_path).startswith(str(self.base_dir.resolve())):
            raise ValueError("Invalid file path: path traversal detected.")
        return full_path

    async def save_file(self, file_content: bytes, filename: str) -> str:
        # Generate a unique path to prevent collisions
        unique_name = f"{uuid.uuid4()}_{filename}"
        file_path = self.base_dir / unique_name

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)

        return str(file_path)

    async def load_file(self, path: str) -> bytes:
        safe_path = self._get_safe_path(path)
        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(safe_path, "rb") as f:
            return await f.read()

    async def delete_file(self, path: str) -> None:
        safe_path = self._get_safe_path(path)
        if safe_path.exists():
            safe_path.unlink()
