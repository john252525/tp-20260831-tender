import base64
import structlog
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = structlog.get_logger()

class EncryptionService:
    """Шифрование строк с использованием Fernet. Ключ берётся из settings.encryption_key.
    В development при отсутствии/невалидном ключе используется временный ключ."""

    def __init__(self):
        self._cipher = None

    def _get_cipher(self) -> Fernet:
        if self._cipher is not None:
            return self._cipher

        key_str = settings.encryption_key
        if not key_str:
            if settings.app_env == 'development':
                key = Fernet.generate_key()
                logger.warning('encryption_service.temp_key_used',
                               message='Используется временный ключ шифрования; данные не переживут перезапуск.')
                self._cipher = Fernet(key)
                return self._cipher
            raise RuntimeError('ENCRYPTION_KEY is not configured')

        try:
            key = base64.urlsafe_b64decode(key_str.encode())
            if len(key) != 32:
                raise ValueError('Invalid key length')
            self._cipher = Fernet(base64.urlsafe_b64encode(key))
            return self._cipher
        except Exception as exc:
            if settings.app_env == 'development':
                key = Fernet.generate_key()
                logger.warning('encryption_service.invalid_key',
                               error=str(exc),
                               message='Ключ шифрования невалиден; используется временный ключ.')
                self._cipher = Fernet(key)
                return self._cipher
            raise

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ''
        cipher = self._get_cipher()
        return cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        if not encrypted:
            return ''
        cipher = self._get_cipher()
        try:
            return cipher.decrypt(encrypted.encode()).decode()
        except InvalidToken:
            return ''

encryption_service = EncryptionService()
