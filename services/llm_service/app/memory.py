import json
import logging

import redis.asyncio as redis
from typing import List, Dict
from app.config import settings

logger = logging.getLogger(__name__)

redis_client = redis.from_url(settings.redis_url, decode_responses=True)

async def get_short_term_memory(user_id: str) -> List[Dict[str, str]]:
    """Retrieve the last N messages for a user from Redis. Returns [] if Redis is unavailable."""
    try:
        key = f"memory:short_term:{user_id}"
        messages = await redis_client.lrange(key, 0, settings.conversation_history_length - 1)
        return [json.loads(msg) for msg in messages]
    except Exception as exc:
        logger.warning("Redis unavailable for short-term memory read (%s): %s", user_id, exc)
        return []

async def add_message_to_memory(user_id: str, role: str, content: str):
    """Add a new message to the user's short-term memory. Silently skips if Redis is unavailable."""
    try:
        key = f"memory:short_term:{user_id}"
        message = json.dumps({"role": role, "content": content})
        await redis_client.rpush(key, message)
        await redis_client.ltrim(key, -settings.conversation_history_length, -1)
    except Exception as exc:
        logger.warning("Redis unavailable for short-term memory write (%s): %s", user_id, exc)
