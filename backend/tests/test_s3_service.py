import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.s3_service import S3Service, s3_service

@pytest.mark.asyncio
async def test_s3_upload_bytes_success(monkeypatch):
    # Мокаем boto3 client внутри s3_service
    fake_client = MagicMock()
    fake_client.put_object = MagicMock()

    service = S3Service()
    # Вручную устанавливаем клиента
    service._client = fake_client
    monkeypatch.setattr(service, '_ensure_client', lambda: fake_client)

    success, path = await service.upload_bytes('test/key.txt', b'hello', 'text/plain')
    assert success is True
    assert path == 'test/key.txt'
    # Проверяем, что put_object вызывался в отдельном потоке (asyncio.to_thread)
    fake_client.put_object.assert_called_once()

@pytest.mark.asyncio
async def test_s3_download_bytes_success(monkeypatch):
    fake_response = {'Body': MagicMock(read=MagicMock(return_value=b'hello'))}
    fake_client = MagicMock()
    fake_client.get_object = MagicMock(return_value=fake_response)

    service = S3Service()
    service._client = fake_client
    monkeypatch.setattr(service, '_ensure_client', lambda: fake_client)

    content = await service.download_bytes('test/key.txt')
    assert content == b'hello'

@pytest.mark.asyncio
async def test_s3_no_config():
    # При неполной конфигурации _ensure_client вернёт None, upload_bytes вернёт False
    service = S3Service()
    service._client = None
    # Патчим settings, чтобы endpoint пуст
    monkeypatch.setattr('app.services.s3_service.settings.s3_endpoint', '')
    success, path = await service.upload_bytes('key', b'data')
    assert success is False
    assert path == ''

@pytest.mark.asyncio
async def test_s3_download_no_config(monkeypatch):
    service = S3Service()
    service._client = None
    monkeypatch.setattr('app.services.s3_service.settings.s3_endpoint', '')
    content = await service.download_bytes('key')
    assert content is None
