"""
Centralized configuration management organized by domain.
Reads from .env file with sensible defaults.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env file
load_dotenv()


def get_env(key: str, default=None, cast=str):
    """Get environment variable with type casting."""
    value = os.getenv(key, default)
    if value is None:
        return None
    try:
        return cast(value)
    except Exception:
        raise ValueError(f"Invalid type for env variable {key}")


def get_bool(key: str, default=False):
    """Get boolean environment variable."""
    return os.getenv(key, str(default)).lower() in ("true", "1", "yes")


# =========================
# GENERAL
# =========================
@dataclass
class GeneralConfig:
    ENV: str = get_env("ENV", "development")
    DEBUG: bool = get_bool("DEBUG", True)
    APP_NAME: str = get_env("APP_NAME", "fi-ainina")
    API_HOST: str = get_env("API_HOST", "0.0.0.0")
    API_PORT: int = get_env("API_PORT", 8000, int)
    SECRET_KEY: str = get_env("SECRET_KEY", "change-me-in-production")


# =========================
# LLM CONFIG
# =========================
@dataclass
class LLMConfig:
    PROVIDER: str = get_env("LLM_PROVIDER", "ollama")

    # Ollama (local)
    OLLAMA_BASE_URL: str = get_env("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = get_env("OLLAMA_MODEL", "llama2")

    # OpenAI (optional alternative)
    OPENAI_API_KEY: str = get_env("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = get_env("OPENAI_MODEL", "gpt-4")

    # LLM parameters
    TEMPERATURE: float = get_env("LLM_TEMPERATURE", 0.7, float)
    MAX_TOKENS: int = get_env("LLM_MAX_TOKENS", 2048, int)


# =========================
# DATABASE
# =========================
@dataclass
class DatabaseConfig:
    URL: str = get_env("DATABASE_URL", "postgresql://postgres:password@localhost:5432/fi_ainina")


# =========================
# COMPUTER VISION
# =========================
@dataclass
class CVConfig:
    DEEPFACE_DISTANCE_METRIC: str = get_env("DEEPFACE_DISTANCE_METRIC", "cosine")
    MEDIAPIPE_CONFIDENCE: float = get_env("MEDIAPIPE_CONFIDENCE", 0.5, float)
    INACTIVITY_THRESHOLD: int = get_env("INACTIVITY_THRESHOLD", 60, int)
    FALL_TIME_THRESHOLD: int = get_env("FALL_TIME_THRESHOLD", 10, int)
    CAMERA_INDEX: int = get_env("CAMERA_INDEX", 0, int)


# =========================
# VOICE
# =========================
@dataclass
class VoiceConfig:
    # Speech-to-Text (Whisper)
    STT_PROVIDER: str = get_env("STT_PROVIDER", "whisper")
    WHISPER_MODEL: str = get_env("WHISPER_MODEL", "base")

    # Text-to-Speech (Coqui)
    TTS_PROVIDER: str = get_env("TTS_PROVIDER", "coqui")
    COQUI_DEVICE: str = get_env("COQUI_DEVICE", "cpu")  # or 'cuda'

    # ElevenLabs (optional alternative)
    ELEVENLABS_API_KEY: str = get_env("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = get_env("ELEVENLABS_VOICE_ID", "")


# =========================
# ALERT SYSTEM
# =========================
@dataclass
class AlertConfig:
    ALERT_EMAIL_FROM: str = get_env("ALERT_EMAIL_FROM", "alerts@aicompanion.local")
    ALERT_EMAIL_PASSWORD: str = get_env("ALERT_EMAIL_PASSWORD", "")

    SMTP_SERVER: str = get_env("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = get_env("SMTP_PORT", 587, int)

    ALERT_WEBHOOK_URL: str = get_env("ALERT_WEBHOOK_URL", "")
    ALERT_TIMEOUT: int = get_env("ALERT_TIMEOUT", 120, int)


# =========================
# LOGGING
# =========================
@dataclass
class LoggingConfig:
    LEVEL: str = get_env("LOG_LEVEL", "INFO")


# =========================
# FRONTEND
# =========================
@dataclass
class FrontendConfig:
    URL: str = get_env("VITE_API_URL", "http://localhost:5173")


# =========================
# GLOBAL CONFIG OBJECT
# =========================
class Config:
    """Global configuration object - access all settings here."""

    general = GeneralConfig()
    llm = LLMConfig()
    database = DatabaseConfig()
    cv = CVConfig()
    voice = VoiceConfig()
    alert = AlertConfig()
    logging = LoggingConfig()
    frontend = FrontendConfig()


# Singleton instance
config = Config()
