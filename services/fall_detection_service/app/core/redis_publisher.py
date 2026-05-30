import json
import redis
from typing import Dict, Optional
from datetime import datetime

from app.config import settings
from app.core.utils.debug_utils import debug_print


def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client (lazy init). Returns None on failure."""
    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        # Optional ping to validate connection
        try:
            client.ping()
        except Exception:
            # Ping failure is non-fatal here; we'll still return the client
            pass
        return client
    except Exception as e:
        debug_print(f"[REDIS] Connection failed: {e}", tag="REDIS")
        return None


def publish_fall_event(event_data: Dict) -> bool:
    """Publish fall event to configured Redis channel.

    Returns True if publish succeeded (or no subscribers), False on error.
    """
    try:
        client = get_redis_client()
        if not client:
            debug_print("[REDIS] No Redis connection, event not published", tag="REDIS")
            return False

        result = client.publish(settings.redis_channel_fall, json.dumps(event_data))

        if result > 0:
            debug_print(
                f"[REDIS] Published fall event to {result} subscriber(s): {event_data.get('event_type')}",
                tag="REDIS",
            )
            return True
        else:
            debug_print(
                f"[REDIS] Published fall event but no subscribers listening on {settings.redis_channel_fall}",
                tag="REDIS",
            )
            return True

    except Exception as e:
        debug_print(f"[REDIS] Error publishing event: {e}", tag="REDIS")
        return False
