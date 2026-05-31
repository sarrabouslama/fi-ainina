from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Companion Backend'
    env: str = 'dev'
    debug: bool = False

    database_url: str = 'postgresql+asyncpg://postgres:postgres@postgres:5432/companion'
    redis_url: str = 'redis://redis:6379/0'

    secret_key: str = 'change-me'
    jwt_algorithm: str = 'HS256'
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    dashboard_origin: AnyHttpUrl = 'http://localhost:5173'

    alerts_ws_url: str = 'ws://alerts:8000/ws'
    llm_base_url: str = 'http://llm:8000'
    voice_base_url: str = 'http://voice_assistant:8000'

    aes256_key_b64: str = Field(
        default='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=',
        description='Base64 urlsafe encoded 32-byte key',
    )


settings = Settings()
