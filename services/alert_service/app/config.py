import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip().strip('"').strip("'")
    return default


def _env_list(name: str) -> list[str]:
    return [value.strip().strip('"').strip("'") for value in os.getenv(name, "").split(",") if value.strip()]

# ─────────────────────────────────────────────────────────────
# Configuration : Alert Service
# Load from .env file or environment variables
# ─────────────────────────────────────────────────────────────

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
ALERT_REDIS_CHANNELS = _env_list("ALERT_REDIS_CHANNELS") or [
    "emotion_events",
    "fall_alerts",
]

# PostgreSQL (for alert_log and user lookups)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/fi_ainina")

# Email (SMTP)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "your@gmail.com")
SMTP_PASS = os.getenv("SMTP_PASS", "your_app_password")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "FiAinina Alerts")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER)
SMTP_TLS = _env_bool("SMTP_TLS", "true")
SMTP_SSL = _env_bool("SMTP_SSL", "false")
SMTP_TIMEOUT = float(os.getenv("SMTP_TIMEOUT", "30"))
ALERT_TEST_EMAIL_RECIPIENTS = _env_list("ALERT_TEST_EMAIL_RECIPIENTS")

# SMS / WhatsApp (Twilio)
TWILIO_SID = _env_first("TWILIO_ACCOUNT_SID", "TWILIO_SID")
TWILIO_TOKEN = _env_first("TWILIO_AUTH_TOKEN", "TWILIO_TOKEN")
TWILIO_FROM = _env_first("TWILIO_FROM", "TWILIO_PHONE_NUMBER")  # Twilio phone number (e.g., +1234567890)
TWILIO_CHANNEL = os.getenv("TWILIO_CHANNEL", "sms").strip().lower()
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
TWILIO_SSL_VERIFY = _env_bool("TWILIO_SSL_VERIFY", "true")
TWILIO_CA_BUNDLE = _env_first("TWILIO_CA_BUNDLE", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE")
ALERT_TEST_SMS_RECIPIENTS = _env_list("ALERT_TEST_SMS_RECIPIENTS")
ALERT_TEST_WHATSAPP_RECIPIENTS = _env_list("ALERT_TEST_WHATSAPP_RECIPIENTS")

# Alert Configuration
ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "5"))
WS_PORT = int(os.getenv("WS_PORT", "8005"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Feature flags
ENABLE_EMAIL = os.getenv("ENABLE_EMAIL", "true").lower() == "true"
ENABLE_SMS = os.getenv("ENABLE_SMS", "true").lower() == "true"
ENABLE_WEBSOCKET = os.getenv("ENABLE_WEBSOCKET", "true").lower() == "true"

# ─────────────────────────────────────────────────────────────
# Validation : critical config must be set
# ─────────────────────────────────────────────────────────────

def validate_config():
    """Validate critical configuration at startup."""
    if ENABLE_EMAIL and (not SMTP_USER or not SMTP_PASS):
        raise ValueError("Email enabled but SMTP_USER or SMTP_PASS not set")
    if TWILIO_CHANNEL not in {"sms", "whatsapp"}:
        raise ValueError("TWILIO_CHANNEL must be 'sms' or 'whatsapp'")
    twilio_from = TWILIO_WHATSAPP_FROM if TWILIO_CHANNEL == "whatsapp" else TWILIO_FROM
    if ENABLE_SMS and (not TWILIO_SID or not TWILIO_TOKEN or not twilio_from):
        raise ValueError("Twilio channel enabled but SID, token, or sender is missing")
