"""
Unit tests for Alert Service components.

Run with: pytest tests/test_alert_service.py -v
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from redis.asyncio import Redis

from app.models import AlertEvent, AlertRecipient
from app.handlers.cooldown_manager import CooldownManager
from app.handlers.websocket_handler import ConnectionManager
from app.handlers.email_handler import EmailHandler
from app.handlers.sms_handler import SMSHandler


# ─────────────────────────────────────────────────────────────
# Cooldown Manager Tests
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    return AsyncMock(spec=Redis)


@pytest.fixture
def cooldown_manager(mock_redis):
    """Create a CooldownManager with mock Redis."""
    manager = CooldownManager(mock_redis)
    manager.cooldown_minutes = 5  # For fast testing
    return manager


class TestCooldownManager:
    """Test alert deduplication logic."""

    @pytest.mark.asyncio
    async def test_first_alert_always_allowed(self, cooldown_manager, mock_redis):
        """First alert for a (user, event_type) pair should always be allowed."""
        mock_redis.get.return_value = None  # No previous alert
        
        result = cooldown_manager.can_send_alert("user_001", "fall_detected")
        
        assert result is True
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_second_alert_too_soon_blocked(self, cooldown_manager, mock_redis):
        """Second alert within cooldown window should be blocked."""
        # Simulate that an alert was sent 1 minute ago
        one_minute_ago = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
        mock_redis.get.return_value = one_minute_ago.encode('utf-8')
        
        result = cooldown_manager.can_send_alert("user_001", "fall_detected")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_second_alert_after_cooldown_allowed(self, cooldown_manager, mock_redis):
        """Alert after cooldown window should be allowed."""
        # Simulate that an alert was sent 6 minutes ago
        six_minutes_ago = (datetime.utcnow() - timedelta(minutes=6)).isoformat()
        mock_redis.get.return_value = six_minutes_ago.encode('utf-8')
        
        result = cooldown_manager.can_send_alert("user_001", "fall_detected")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_record_alert_sent(self, cooldown_manager, mock_redis):
        """Recording alert should set Redis key with TTL."""
        cooldown_manager.record_alert_sent("user_001", "fall_detected")
        
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert "cooldown:user_001:fall_detected" in str(call_args)


# ─────────────────────────────────────────────────────────────
# WebSocket Handler Tests
# ─────────────────────────────────────────────────────────────

class TestConnectionManager:
    """Test WebSocket connection management."""

    @pytest.mark.asyncio
    async def test_connect_adds_connection(self):
        """Connecting should add WebSocket to active connections."""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        
        await manager.connect(mock_ws)
        
        assert mock_ws in manager.active_connections
        mock_ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self):
        """Disconnecting should remove WebSocket from active connections."""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        
        await manager.connect(mock_ws)
        manager.disconnect(mock_ws)
        
        assert mock_ws not in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self):
        """Broadcast should send message to all connected clients."""
        manager = ConnectionManager()
        
        # Create 3 mock WebSocket connections
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws3 = AsyncMock()
        
        await manager.connect(mock_ws1)
        await manager.connect(mock_ws2)
        await manager.connect(mock_ws3)
        
        # Create test message
        from app.models import WebSocketMessage
        message = WebSocketMessage(
            event_type="fall_detected",
            user_id="user_001",
            timestamp=datetime.utcnow(),
            severity="high"
        )
        
        # Broadcast
        await manager.broadcast(message)
        
        # All connections should have received the message
        assert mock_ws1.send_text.called
        assert mock_ws2.send_text.called
        assert mock_ws3.send_text.called

    @pytest.mark.asyncio
    async def test_broadcast_handles_disconnection(self):
        """Broadcast should handle client disconnections gracefully."""
        manager = ConnectionManager()
        
        # Create 2 mock connections, one will fail
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.send_text.side_effect = Exception("Connection closed")
        
        await manager.connect(mock_ws1)
        await manager.connect(mock_ws2)
        
        from app.models import WebSocketMessage
        message = WebSocketMessage(
            event_type="fall_detected",
            user_id="user_001",
            timestamp=datetime.utcnow(),
            severity="high"
        )
        
        # Broadcast should not raise exception
        await manager.broadcast(message)
        
        # mock_ws2 should be disconnected due to error
        assert mock_ws2 not in manager.active_connections
        assert mock_ws1 in manager.active_connections


# ─────────────────────────────────────────────────────────────
# Alert Event Models Tests
# ─────────────────────────────────────────────────────────────

class TestAlertEventModels:
    """Test Pydantic model validation."""

    def test_alert_event_valid(self):
        """Valid AlertEvent should be created."""
        event = AlertEvent(
            event_type="fall_detected",
            user_id="elder_001",
            timestamp=datetime.utcnow(),
            severity="high",
            confidence=0.92,
            metadata={"pose_keypoints": []}
        )
        
        assert event.event_type == "fall_detected"
        assert event.user_id == "elder_001"
        assert event.severity == "high"
        assert event.confidence == 0.92

    def test_alert_event_missing_fields(self):
        """AlertEvent with missing required fields should fail."""
        with pytest.raises(ValueError):
            AlertEvent(
                event_type="fall_detected",
                # Missing user_id, timestamp, severity
            )

    def test_alert_recipient_valid(self):
        """Valid AlertRecipient should be created."""
        recipient = AlertRecipient(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            name="Alice Dupont",
            email="alice@example.com",
            phone="+33612345678",
            role="family"
        )
        
        assert recipient.name == "Alice Dupont"
        assert recipient.email == "alice@example.com"
        assert recipient.role == "family"


# ─────────────────────────────────────────────────────────────
# Email Handler Tests
# ─────────────────────────────────────────────────────────────

class TestEmailHandler:
    """Test email sending logic."""

    def test_email_handler_init(self):
        """EmailHandler should initialize with config."""
        handler = EmailHandler()
        
        assert handler.enabled is not None
        assert handler.smtp_host is not None
        assert handler.smtp_port == 587 or handler.smtp_port == 25

    @pytest.mark.asyncio
    async def test_compose_email_structure(self):
        """Email composition should include subject and HTML body."""
        handler = EmailHandler()
        
        event = AlertEvent(
            event_type="fall_detected",
            user_id="elder_001",
            timestamp=datetime.utcnow(),
            severity="high",
            confidence=0.95,
            metadata={}
        )
        
        subject, body = handler._compose_email(event)
        
        assert "ALERTE" in subject.upper()
        assert "fall_detected" in subject.lower()
        assert "<html>" in body.lower()
        assert "elder_001" in body


# ─────────────────────────────────────────────────────────────
# SMS Handler Tests
# ─────────────────────────────────────────────────────────────

class TestSMSHandler:
    """Test SMS sending logic."""

    def test_sms_handler_init(self):
        """SMSHandler should initialize with config."""
        handler = SMSHandler()
        
        assert handler.enabled is not None
        assert handler.twilio_from is not None

    def test_sms_compose_message_length(self):
        """SMS message should be under 160 chars (single SMS)."""
        handler = SMSHandler()
        
        event = AlertEvent(
            event_type="fall_detected",
            user_id="elder_001",
            timestamp=datetime.utcnow(),
            severity="high",
            confidence=0.95,
            metadata={}
        )
        
        message = handler._compose_sms(event)
        
        assert len(message) <= 160
        assert "Alerte" in message
        assert "elder_001" in message

    def test_sms_compose_message_emoji(self):
        """SMS message should include appropriate emoji."""
        handler = SMSHandler()
        
        event = AlertEvent(
            event_type="fall_detected",
            user_id="elder_001",
            timestamp=datetime.utcnow(),
            severity="high"
        )
        
        message = handler._compose_sms(event)
        
        assert "🚨" in message  # Fall emoji
        
        # Test emotion event
        event.event_type = "emotion_distress"
        message = handler._compose_sms(event)
        assert "😢" in message  # Emotion emoji


# ─────────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────────

class TestIntegration:
    """Integration tests (require services to be running)."""

    @pytest.mark.asyncio
    async def test_alert_event_parsing(self):
        """Test that JSON alert can be parsed correctly."""
        import json
        
        json_data = {
            "event_type": "fall_detected",
            "user_id": "elder_001",
            "timestamp": "2025-05-01T12:00:00Z",
            "severity": "high",
            "confidence": 0.92,
            "metadata": {"pose_keypoints": []}
        }
        
        # Parse as AlertEvent
        event = AlertEvent(**json_data)
        
        assert event.event_type == "fall_detected"
        assert event.severity == "high"


# ─────────────────────────────────────────────────────────────
# Fixtures for conftest
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def alert_event():
    """Create a sample AlertEvent for testing."""
    return AlertEvent(
        event_type="fall_detected",
        user_id="elder_001",
        timestamp=datetime.utcnow(),
        severity="high",
        confidence=0.95,
        metadata={"pose_keypoints": []}
    )


@pytest.fixture
def emotion_event():
    """Create a sample emotion AlertEvent for testing."""
    return AlertEvent(
        event_type="emotion_distress",
        user_id="elder_001",
        timestamp=datetime.utcnow(),
        severity="medium",
        confidence=0.87,
        metadata={"emotion": "sad", "score": 0.87}
    )


@pytest.fixture
def inactivity_event():
    """Create a sample inactivity AlertEvent for testing."""
    return AlertEvent(
        event_type="inactivity_detected",
        user_id="elder_001",
        timestamp=datetime.utcnow(),
        severity="low",
        confidence=None,
        metadata={"duration_seconds": 1800}
    )
