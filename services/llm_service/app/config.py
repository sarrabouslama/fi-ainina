from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ollama_url: str = "http://ollama:11434/v1"
    llm_model: str = "llama3"
    conversation_history_length: int = 20
    redis_url: str = "redis://redis:6379/0"
    database_url: str = "postgresql://postgres_user:changeme_strong_password@postgres:5432/fi-ainina"
    voice_service_url: str = "http://voice_service:8002"
    emotion_service_url: str = "http://emotion_service:8004"
    service_request_timeout_seconds: float = 3.0

settings = Settings()
