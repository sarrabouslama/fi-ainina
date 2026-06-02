"""
Cooldown Manager : prevent alert spam using Redis.

Strategy: maintain a Redis hash key per (user_id, event_type) pair
with the timestamp of the last alert sent.
If (now - last_timestamp) < COOLDOWN_MINUTES, skip sending.

Redis Key: cooldown:{user_id}:{event_type}
Redis Value: ISO timestamp (datetime string)
Redis TTL: 2x COOLDOWN_MINUTES (auto cleanup)
"""

import logging
from datetime import datetime
from inspect import isawaitable
from typing import Union
from redis.asyncio import Redis
from app import config
from app.config import ALERT_COOLDOWN_MINUTES

logger = logging.getLogger(__name__)


class CooldownManager:
    """Manage alert cooldown using Redis with per-event-type overrides."""

    def __init__(self, redis: Union[str, Redis]):
        if isinstance(redis, str):
            self.redis = Redis.from_url(redis, decode_responses=True)
        else:
            self.redis = redis
        self.cooldown_minutes = ALERT_COOLDOWN_MINUTES

    def _get_cooldown_key(self, user_id: str, event_type: str) -> str:
        return f"cooldown:{user_id}:{event_type}"

    def _cooldown_for(self, event_type: str) -> int:
        """Return the cooldown in minutes for this event type."""
        return config.COOLDOWN_PER_EVENT_TYPE.get(event_type, self.cooldown_minutes)

    async def _resolve(self, value):
        if isawaitable(value):
            return await value
        return value

    async def can_send_alert(self, user_id: str, event_type: str) -> bool:
        """
        Check if enough time has passed to send a new alert.

        Returns True if we can send, False if still in cooldown period.
        """
        cooldown = self._cooldown_for(event_type)
        key = self._get_cooldown_key(user_id, event_type)

        try:
            if cooldown <= 0:
                logger.debug("Cooldown disabled for %s; allowing alert", event_type)
                return True

            last_timestamp_str = await self._resolve(self.redis.get(key))

            if last_timestamp_str is None:
                logger.debug("First alert for %s:%s, no cooldown", user_id, event_type)
                return True

            if isinstance(last_timestamp_str, bytes):
                last_timestamp_str = last_timestamp_str.decode("utf-8")

            last_timestamp = datetime.fromisoformat(last_timestamp_str)
            elapsed_minutes = (datetime.utcnow() - last_timestamp).total_seconds() / 60

            if elapsed_minutes >= cooldown:
                logger.debug("Cooldown expired for %s: %.1f min >= %d min", event_type, elapsed_minutes, cooldown)
                return True

            remaining = cooldown - elapsed_minutes
            logger.info(
                "Alert suppressed (cooldown): %s/%s — %.1f min remaining of %d min cooldown",
                event_type, user_id, remaining, cooldown,
            )
            return False

        except Exception as e:
            logger.error("Cooldown check error: %s", e, exc_info=True)
            return True  # fail open

    async def record_alert_sent(self, user_id: str, event_type: str) -> None:
        """Record that an alert was sent, starting the cooldown timer."""
        cooldown = self._cooldown_for(event_type)
        key = self._get_cooldown_key(user_id, event_type)
        now = datetime.utcnow().isoformat()

        try:
            if cooldown <= 0:
                logger.debug("Cooldown disabled for %s; not recording", event_type)
                return

            ttl_seconds = cooldown * 60 * 2  # keep key for 2x cooldown for cleanup
            await self._resolve(self.redis.setex(key, ttl_seconds, now))
            logger.info("Cooldown started for %s/%s: %d min", event_type, user_id, cooldown)
        except Exception as e:
            logger.error("Failed to record alert: %s", e, exc_info=True)

    async def reset_cooldown(self, user_id: str, event_type: str) -> None:
        """Force reset cooldown (for testing or admin override)."""
        key = self._get_cooldown_key(user_id, event_type)
        try:
            await self._resolve(self.redis.delete(key))
            logger.info(f"Cooldown reset for {user_id}:{event_type}")
        except Exception as e:
            logger.error(f"Failed to reset cooldown: {e}", exc_info=True)
