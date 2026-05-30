"""Redis event publishing for emotion and inactivity alerts."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import redis

from app.config import REDIS_HOST, REDIS_PORT, USER_ID

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class DistressEventPayload:
    """Payload wrapper for a distress event."""

    event_type: str
    user_id: str
    timestamp: str
    severity: str
    confidence: float
    metadata: dict


@dataclass(frozen=True)
class InactivityEventPayload:
    """Payload wrapper for an inactivity event."""

    event_type: str
    user_id: str
    timestamp: str
    severity: str
    confidence: float
    metadata: dict


class RedisEventPublisher:
    """Publish service events to Redis channels."""

    def __init__(self) -> None:
        self._client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    def _publish(self, channel: str, payload: dict) -> None:
        try:
            self._client.publish(channel, json.dumps(payload, ensure_ascii=False))
            logger.info("Published Redis event on %s", channel)
        except Exception:
            logger.exception("Failed to publish Redis event on channel %s", channel)

    def publish_distress_event(
        self,
        *,
        severity: str,
        confidence: float,
        emotion: str,
        score: float,
        redness_score: float,
        redness_level: str,
        redness_reliable: bool,
    ) -> None:
        """Publish a distress emotion event."""
        payload = DistressEventPayload(
            event_type="emotion_distress",
            user_id=USER_ID,
            timestamp=_utc_now_iso(),
            severity=severity,
            confidence=confidence,
            metadata={
                "emotion": emotion,
                "score": score,
                "redness_score": redness_score,
                "redness_level": redness_level,
                "redness_reliable": redness_reliable,
            },
        )
        self._publish("emotion_events", payload.__dict__)

    def publish_inactivity_event(self, *, duration_seconds: int) -> None:
        """Publish an inactivity alert event."""
        payload = InactivityEventPayload(
            event_type="inactivity_detected",
            user_id=USER_ID,
            timestamp=_utc_now_iso(),
            severity="medium",
            confidence=1.0,
            metadata={"duration_seconds": duration_seconds},
        )
        self._publish("inactivity_events", payload.__dict__)