from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ollama_url: str = "http://ollama:11434/v1"
    llm_model: str = "llama3"
    conversation_history_length: int = 20
    redis_url: str = "redis://redis:6379/0"
    voice_service_url: str = "http://host.docker.internal:8002"

    class Config:
        env_file = ".env"

settings = Settings()
