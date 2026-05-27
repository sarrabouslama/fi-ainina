import logging
from app.config import settings

logger = logging.getLogger(__name__)

async def get_long_term_facts(user_id: str) -> str:
    """
    Mock integration for P2 (Voice Service).
    Returns a mocked long-term facts string for the user.
    """
    logger.info(f"Mocking P2 call for user_id: {user_id}")
    
    # Mocked facts
    return "User loves gardening, has a dog named Max, and prefers to be spoken to in a cheerful tone."

