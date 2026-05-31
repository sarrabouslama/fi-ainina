"""
Redis Subscriber : listen to event channels from emotion service and voice service.

Architecture:
- Subscribe to 2 channels: emotion_events, fall_alerts
- Parse JSON AlertEvent
- Call handle_alert() for each event (deduplication, dispatch, logging)
- Run as background task during FastAPI startup
"""

import logging
import json
import asyncio
from redis.asyncio import Redis as AsyncRedis
from contextlib import asynccontextmanager

from app.models import AlertEvent
from app import config

logger = logging.getLogger(__name__)

# Channels to listen to
ALERT_CHANNELS = config.ALERT_REDIS_CHANNELS


def parse_alert_event(data: str) -> AlertEvent:
    """Parse one Redis pub/sub message into the alert-service event model."""
    event_dict = json.loads(data)
    if not isinstance(event_dict, dict):
        raise ValueError("Redis alert payload must be a JSON object")

    metadata = event_dict.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {"value": metadata}

    return AlertEvent(
        event_type=event_dict.get("event_type"),
        user_id=event_dict.get("user_id"),
        timestamp=event_dict.get("timestamp"),
        severity=event_dict.get("severity"),
        confidence=event_dict.get("confidence"),
        metadata=metadata,
    )


async def redis_subscriber(redis: AsyncRedis, handle_alert_callback):
    """
    Subscribe to Redis channels and process events.
    
    Args:
        redis: AsyncRedis client
        handle_alert_callback: async function to call for each event
    """
    pubsub = redis.pubsub()
    
    try:
        # Subscribe to all channels
        await pubsub.subscribe(*ALERT_CHANNELS)
        logger.info(f"Subscribed to Redis channels: {ALERT_CHANNELS}")
        
        # Listen for messages
        async for message in pubsub.listen():
            # Skip subscription confirmation messages
            if message["type"] != "message":
                continue
            
            channel = message["channel"].decode('utf-8') if isinstance(message["channel"], bytes) else message["channel"]
            data = message["data"].decode('utf-8') if isinstance(message["data"], bytes) else message["data"]
            
            logger.debug(f"Received message on channel {channel}")
            
            try:
                # Validate and create AlertEvent
                event = parse_alert_event(data)
                
                logger.info(
                    f"Parsed alert: {event.event_type} from {event.user_id} "
                    f"with severity {event.severity}"
                )
                
                # Process alert (handle deduplication, dispatch to channels, logging)
                await handle_alert_callback(event)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from channel {channel}: {e}", exc_info=True)
            except ValueError as e:
                logger.error(f"Invalid alert event data: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error processing alert: {e}", exc_info=True)
    
    except asyncio.CancelledError:
        logger.info("Redis subscriber task cancelled")
    except Exception as e:
        logger.error(f"Redis subscriber error: {e}", exc_info=True)
    finally:
        await pubsub.unsubscribe(*ALERT_CHANNELS)
        await pubsub.close()
        logger.info("Redis subscriber closed")


async def create_redis_connection() -> AsyncRedis:
    """Create async Redis connection pool."""
    try:
        redis = await AsyncRedis.from_url(config.REDIS_URL, decode_responses=False)
        # Test connection
        await redis.ping()
        logger.info("Redis connection established")
        return redis
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
        raise


async def close_redis_connection(redis: AsyncRedis):
    """Close Redis connection pool."""
    try:
        await redis.close()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis connection: {e}", exc_info=True)
