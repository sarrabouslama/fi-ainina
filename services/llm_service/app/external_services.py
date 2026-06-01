import logging

import httpx

from app.config import settings
from app.database import get_pool

logger = logging.getLogger(__name__)

async def get_long_term_facts(user_id: str) -> str:
    """
    Read durable user context from the shared PostgreSQL schema.

    The current shared schema does not define a separate facts table, so the LLM
    uses the user's profile fields and preferences as long-term context.
    """
    try:
        pool = await get_pool()
        row = await pool.fetchrow(
            """
            SELECT full_name, role::text AS role, consent_given, preferences
            FROM users
            WHERE id = $1
            """,
            user_id,
        )
    except Exception as exc:
        logger.warning("Could not load user context for %s: %s", user_id, exc)
        return "No long-term user context available."

    if not row:
        return "No long-term user context available."

    context = [
        f"Name: {row['full_name']}",
        f"Role: {row['role']}",
        f"Consent given: {row['consent_given']}",
    ]

    preferences = row["preferences"]
    if isinstance(preferences, dict) and preferences:
        preference_text = ", ".join(f"{key}: {value}" for key, value in preferences.items())
        context.append(f"Preferences: {preference_text}")

    return "\n".join(context)


async def save_conversation_turn(user_id: str, user_message: str, assistant_reply: str) -> None:
    """Persist the chat turn in the shared conversation tables."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                session_id = await conn.fetchval(
                    """
                    SELECT id
                    FROM conversation_sessions
                    WHERE user_id = $1 AND ended_at IS NULL
                    ORDER BY started_at DESC
                    LIMIT 1
                    """,
                    user_id,
                )

                if session_id is None:
                    session_id = await conn.fetchval(
                        """
                        INSERT INTO conversation_sessions (user_id, started_at, message_count)
                        VALUES ($1, NOW(), 0)
                        RETURNING id
                        """,
                        user_id,
                    )

                await conn.execute(
                    """
                    INSERT INTO conversation_messages (session_id, role, content, timestamp)
                    VALUES ($1, 'user', $2, NOW()), ($1, 'assistant', $3, NOW())
                    """,
                    session_id,
                    user_message,
                    assistant_reply,
                )
                await conn.execute(
                    """
                    UPDATE conversation_sessions
                    SET message_count = message_count + 2
                    WHERE id = $1
                    """,
                    session_id,
                )
    except Exception as exc:
        logger.warning("Could not persist conversation for %s: %s", user_id, exc)


async def get_detected_emotion() -> str:
    """Read the latest emotion snapshot from emotion_service."""
    try:
        async with httpx.AsyncClient(timeout=settings.service_request_timeout_seconds) as client:
            response = await client.get(f"{settings.emotion_service_url.rstrip('/')}/status")
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.warning("Could not read emotion_service status: %s", exc)
        return "neutral"

    emotion = str(payload.get("emotion") or "neutral").strip()
    return emotion or "neutral"


async def synthesize_speech(text: str) -> tuple[bytes | None, str | None]:
    """Ask voice_service to synthesize the assistant reply as audio."""
    try:
        async with httpx.AsyncClient(timeout=settings.service_request_timeout_seconds) as client:
            response = await client.post(
                f"{settings.voice_service_url.rstrip('/')}/speak",
                json={"text": text, "speed": 1.0},
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "audio/wav")
            return response.content, content_type
    except Exception as exc:
        logger.warning("Could not synthesize speech through voice_service: %s", exc)
        return None, None

