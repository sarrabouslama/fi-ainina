import logging

import httpx

from app.config import settings
from app.database import get_pool

logger = logging.getLogger(__name__)

async def get_long_term_facts(user_id: str) -> str:
    """Read durable user context from PostgreSQL, including assigned caregiver."""
    try:
        pool = await get_pool()
        row = await pool.fetchrow(
            "SELECT full_name, role::text AS role, preferences FROM users WHERE id = $1",
            user_id,
        )
        # Find caregiver via person_watchers
        caregiver_row = await pool.fetchrow(
            """
            SELECT u.full_name, u.phone
            FROM person_watchers pw
            JOIN users u ON u.id = pw.user_id
            WHERE pw.person_id = $1
            LIMIT 1
            """,
            user_id,
        )
    except Exception as exc:
        logger.warning("Could not load user context for %s: %s", user_id, exc)
        return "Aucun contexte utilisateur disponible."

    if not row:
        return "Aucun contexte utilisateur disponible."

    context = [f"Prénom du résident : {row['full_name']}"]

    if caregiver_row:
        caregiver_name = caregiver_row['full_name']
        caregiver_phone = caregiver_row['phone'] or 'non renseigné'
        context.append(f"Soignant assigné : {caregiver_name}")
        context.append(f"Téléphone du soignant : {caregiver_phone}")
        context.append(
            f"INSTRUCTION ABSOLUE EN CAS D'URGENCE : dire exactement "
            f"\"Je contacte votre soignant {caregiver_name}"
            + (f" au {caregiver_phone}" if caregiver_row['phone'] else "")
            + " immédiatement.\""
        )
    else:
        context.append(
            "Aucun soignant assigné. En cas d'urgence, dire exactement : "
            "\"Je déclenche une alerte d'urgence pour vous.\""
        )

    preferences = row["preferences"]
    if isinstance(preferences, dict) and preferences:
        for key, value in preferences.items():
            if key != "assigned_user_ids":
                context.append(f"{key}: {value}")

    return "\n".join(context)


async def save_conversation_turn(user_id: str, user_message: str, assistant_reply: str) -> None:
    """Persist the chat turn via the companion backend API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{settings.companion_backend_url}/conversations/save",
                json={
                    "user_id": user_id,
                    "user_message": user_message,
                    "assistant_reply": assistant_reply,
                },
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

