import json
import redis.asyncio as redis
from typing import List, Dict
from app.config import settings

# Initialize Redis client
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

async def get_short_term_memory(user_id: str) -> List[Dict[str, str]]:
    """Retrieve the last N messages for a user from Redis."""
    key = f"memory:short_term:{user_id}"
    messages = await redis_client.lrange(key, 0, settings.conversation_history_length - 1)
    
    # Redis lrange returns newest first if we lpush, or oldest first if we rpush.
    # We will rpush, so they are in chronological order.
    return [json.loads(msg) for msg in messages]

async def add_message_to_memory(user_id: str, role: str, content: str):
    """Add a new message to the user's short-term memory."""
    key = f"memory:short_term:{user_id}"
    message = json.dumps({"role": role, "content": content})
    
    # Push to the right (end of list)
    await redis_client.rpush(key, message)
    
    # Trim to history length to keep only the latest N messages
    # LTRIM keeps indices from -length to -1
    await redis_client.ltrim(key, -settings.conversation_history_length, -1)
