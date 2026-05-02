from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

# ─────────────────────────────────────────────────────────────
# Alert Event : Redis event structure (from P3, P4)
# ─────────────────────────────────────────────────────────────

class AlertEvent(BaseModel):
    """
    Base alert event structure from Redis.
    All events follow the same contract across fall_events, emotion_events, inactivity_events.
    """
    event_type: str  # "fall_detected" | "emotion_distress" | "inactivity_detected"
    user_id: str  # monitored person ID
    timestamp: datetime
    severity: str  # "high" | "medium" | "low"
    confidence: Optional[float] = None  # 0.0-1.0
    metadata: Dict[str, Any] = {}  # event-specific metadata

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "fall_detected",
                "user_id": "elder_001",
                "timestamp": "2025-01-15T14:30:00Z",
                "severity": "high",
                "confidence": 0.92,
                "metadata": {"pose_keypoints": [...]}
            }
        }


# ─────────────────────────────────────────────────────────────
# Alert Log Entry : PostgreSQL audit trail
# ─────────────────────────────────────────────────────────────

class AlertLogEntry(BaseModel):
    """
    Alert log entry for audit trail (saved to PostgreSQL alert_log table).
    """
    id: Optional[UUID] = None
    event_id: Optional[str] = None  # reference to original Redis event
    event_type: str  # "fall_detected" | "emotion_distress" | "inactivity_detected"
    channel: str  # "email" | "sms" | "websocket"
    recipient: str  # email address, phone number, or "broadcast" for WS
    status: str = "sent"  # "sent" | "failed" | "pending"
    created_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "fall_detected",
                "channel": "email",
                "recipient": "caregiver@example.com",
                "status": "sent",
                "created_at": "2025-01-15T14:30:00Z"
            }
        }


# ─────────────────────────────────────────────────────────────
# Alert Recipients : derived from PostgreSQL (person_watchers + users)
# ─────────────────────────────────────────────────────────────

class AlertRecipient(BaseModel):
    """
    Alert recipient for a monitored person (family or caregiver).
    Derived from users + person_watchers tables.
    """
    user_id: UUID
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None  # if SMS enabled
    role: str  # "family" | "caregiver" | "admin"

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Alice Dupont",
                "email": "alice@example.com",
                "phone": "+33612345678",
                "role": "family"
            }
        }


# ─────────────────────────────────────────────────────────────
# Endpoints Response Models
# ─────────────────────────────────────────────────────────────

class AlertHistoryResponse(BaseModel):
    """Response for GET /alerts (paginated alert history)."""
    total: int
    limit: int
    offset: int
    alerts: list[AlertLogEntry]


class AlertTestRequest(BaseModel):
    """Request for POST /alerts/test (manual alert creation)."""
    event_type: str
    user_id: str
    severity: str = "high"
    metadata: Optional[Dict[str, Any]] = None


class HealthCheckResponse(BaseModel):
    """Response for GET /health."""
    service: str
    status: str  # "ok" | "degraded" | "error"
    redis_connected: bool
    database_connected: bool
    timestamp: datetime


class WebSocketMessage(BaseModel):
    """Message sent over WebSocket to frontend."""
    event_type: str
    user_id: str
    timestamp: datetime
    severity: str
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = {}
    message_type: str = "alert"  # "alert" | "heartbeat"