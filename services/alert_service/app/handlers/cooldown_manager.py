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
from datetime import datetime, timedelta
from redis import Redis
from app.config import ALERT_COOLDOWN_MINUTES

logger = logging.getLogger(__name__)


class CooldownManager:
    """Manage alert cooldown using Redis."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.cooldown_minutes = ALERT_COOLDOWN_MINUTES

    def _get_cooldown_key(self, user_id: str, event_type: str) -> str:
        """Generate Redis key for cooldown tracking."""
        return f"cooldown:{user_id}:{event_type}"

    def can_send_alert(self, user_id: str, event_type: str) -> bool:
        """
        Check if enough time has passed to send a new alert.
        
        Returns:
            True if we can send, False if still in cooldown period.
        """
        key = self._get_cooldown_key(user_id, event_type)
        
        try:
            # Get last alert timestamp
            last_timestamp_str = self.redis.get(key)
            
            if last_timestamp_str is None:
                # First alert for this (user, event_type) pair
                logger.debug(f"First alert for {user_id}:{event_type}, no cooldown")
                return True
            
            # Parse timestamp
            last_timestamp = datetime.fromisoformat(last_timestamp_str.decode('utf-8'))
            now = datetime.utcnow()
            elapsed_minutes = (now - last_timestamp).total_seconds() / 60
            
            if elapsed_minutes >= self.cooldown_minutes:
                logger.debug(f"Cooldown expired: {elapsed_minutes:.1f} min >= {self.cooldown_minutes} min")
                return True
            else:
                logger.debug(
                    f"Still in cooldown: {elapsed_minutes:.1f} min < {self.cooldown_minutes} min "
                    f"(skipping alert for {user_id}:{event_type})"
                )
                return False
                
        except Exception as e:
            logger.error(f"Cooldown check error: {e}", exc_info=True)
            # On error, allow alert (fail open)
            return True

    def record_alert_sent(self, user_id: str, event_type: str) -> None:
        """
        Record that an alert was sent for this (user_id, event_type) pair.
        Resets the cooldown timer.
        """
        key = self._get_cooldown_key(user_id, event_type)
        now = datetime.utcnow().isoformat()
        
        try:
            # Set timestamp with TTL = 2x cooldown (for cleanup)
            ttl_seconds = self.cooldown_minutes * 60 * 2
            self.redis.setex(key, ttl_seconds, now)
            logger.debug(f"Recorded alert for {user_id}:{event_type}, TTL={ttl_seconds}s")
        except Exception as e:
            logger.error(f"Failed to record alert: {e}", exc_info=True)

    def reset_cooldown(self, user_id: str, event_type: str) -> None:
        """Force reset cooldown (for testing or admin override)."""
        key = self._get_cooldown_key(user_id, event_type)
        try:
            self.redis.delete(key)
            logger.info(f"Cooldown reset for {user_id}:{event_type}")
        except Exception as e:
            logger.error(f"Failed to reset cooldown: {e}", exc_info=True)
