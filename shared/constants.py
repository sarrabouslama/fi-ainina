"""
Shared constants and enums used across services.
"""

from enum import Enum

# Service names
SERVICE_LLM = "llm"
SERVICE_CV = "cv"
SERVICE_VOICE = "voice"
SERVICE_ALERTS = "alerts"

ALL_SERVICES = [SERVICE_LLM, SERVICE_CV, SERVICE_VOICE, SERVICE_ALERTS]

# HTTP response codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_INTERNAL_ERROR = 500


# Alert severity levels
class AlertSeverity(str, Enum):
    """Alert severity classification."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
