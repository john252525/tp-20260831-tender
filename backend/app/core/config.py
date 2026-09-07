from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    app_env: str = 'development'
    app_debug: bool = True
    app_secret_key: str = 'change-me'

    postgres_host: str = 'postgres'
    postgres_port: int = 5432
    postgres_db: str = 'tender_pipeline'
    postgres_user: str = 'tender_user'
    postgres_password: str = 'change-me'

    redis_url: str = 'redis://redis:6379/0'

    llm_api_key: str = ''
    llm_api_base: str = 'https://api.openai.com/v1'
    llm_model_chat: str = 'gpt-4o-mini'
    llm_model_embedding: str = 'text-embedding-3-small'
    llm_embedding_dimensions: int = 768
    embedding_service_url: str = 'http://ollama:11434'
    search_api_url: str = 'https://2222.apitter.com/search/api.php'

    google_search_api_key: str = ''
    google_search_cx: str = ''
    google_search_max_results: int = 10

    smtp_host: str = ''
    smtp_port: int = 587
    smtp_user: str = ''
    smtp_password: str = ''
    smtp_use_tls: bool = True

    imap_host: str = ''
    imap_port: int = 993
    imap_user: str = ''
    imap_password: str = ''
    imap_use_ssl: bool = True

    telegram_bot_token: str = ''

    s3_endpoint: str = 'http://localhost:9000'
    s3_access_key: str = 'minioadmin'
    s3_secret_key: str = 'minioadmin'
    s3_bucket: str = 'tender-files'
    s3_use_ssl: bool = False

    encryption_key: str = ''

    cors_origins: List[str] = ['*']
    auth_exempt_paths: List[str] = [
        '/api/v1/health',
        '/api/v1/metrics',
        '/docs',
        '/redoc',
        '/openapi.json'
    ]

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

settings = Settings()
