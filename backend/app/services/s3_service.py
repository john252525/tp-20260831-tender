import asyncio
import os
from pathlib import Path


class S3Service:
    """Локальная заглушка S3/MinIO.

    В проде замените на реальную интеграцию с S3.
    """

    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or os.getenv('LOCAL_STORAGE_DIR', '/app/data'))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def upload_bytes(self, key: str, content: bytes | str, bucket: str | None = None):
        loop = asyncio.get_running_loop()
        if isinstance(content, str):
            content = content.encode('utf-8')
        path = self.base_dir / key
        await loop.run_in_executor(None, self._write_bytes, path, content)
        return True, str(path)

    async def download_bytes(self, key: str, bucket: str | None = None):
        loop = asyncio.get_running_loop()
        path = self.base_dir / key
        return await loop.run_in_executor(None, self._read_bytes, path)

    @staticmethod
    def _write_bytes(path: Path, content: bytes):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    @staticmethod
    def _read_bytes(path: Path) -> bytes | None:
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None


s3_service = S3Service()
