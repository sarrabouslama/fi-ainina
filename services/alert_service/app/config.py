import os

# ─────────────────────────────────────────────────────────────
# Configuration : Alert Service
# Load from .env file or environment variables
# ─────────────────────────────────────────────────────────────

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# PostgreSQL (for alert_log and user lookups)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/fi_ainina")

# Email (SMTP)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "your@gmail.com")
SMTP_PASS = os.getenv("SMTP_PASS", "your_app_password")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "FiAinina Alerts")

# SMS (Twilio)
TWILIO_SID = os.getenv("TWILIO_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_FROM", "")  # Twilio phone number (e.g., +1234567890)

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
    if ENABLE_SMS and (not TWILIO_SID or not TWILIO_TOKEN or not TWILIO_FROM):
        raise ValueError("SMS enabled but Twilio credentials not set")