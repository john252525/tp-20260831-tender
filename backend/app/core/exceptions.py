class AppException(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: dict = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

class UnauthorizedError(AppException):
    def __init__(self):
        super().__init__(401, 'UNAUTHORIZED', 'Invalid or expired API token')

class NotFoundError(AppException):
    def __init__(self, message='Сущность не найдена'):
        super().__init__(404, 'NOT_FOUND', message)

class ConflictError(AppException):
    def __init__(self, message, code='CONFLICT', details=None):
        super().__init__(409, code, message, details)

class ValidationError(AppException):
    def __init__(self, message, details=None):
        super().__init__(422, 'VALIDATION_ERROR', message, details)
