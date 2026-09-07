import pytest
import base64
from cryptography.fernet import Fernet
from app.core.config import settings
from app.services.encryption_service import encryption_service

@pytest.fixture(autouse=True)
def set_valid_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, 'encryption_key', key)
    # Сбрасываем кеш cipher, чтобы он использовал новый ключ
    encryption_service._cipher = None
    yield

def test_encrypt_decrypt_roundtrip():
    plaintext = 'secret-api-key'
    encrypted = encryption_service.encrypt(plaintext)
    assert encrypted != plaintext
    assert encryption_service.decrypt(encrypted) == plaintext

def test_decrypt_empty():
    assert encryption_service.decrypt('') == ''

def test_decrypt_invalid():
    assert encryption_service.decrypt('invalid') == ''
