"""
Database : PostgreSQL connection and ORM setup.

Uses SQLAlchemy with asyncpg for async database operations.
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from uuid import UUID

from app import config

logger = logging.getLogger(__name__)

Base = declarative_base()


async def init_database():
    """Initialize database engine and test connection."""
    try:
        # Convert postgresql:// to postgresql+asyncpg:// for async
        db_url = config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        
        engine = create_async_engine(
            db_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
        )
        
        # Test connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        logger.info("Database connection established")
        return engine
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise


async def get_database_session(engine):
    """Get async session factory."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_alert_recipients(session: AsyncSession, person_id: str) -> list[dict]:
    """
    Get all recipients (family + caregivers) for a monitored person.
    
    Returns list of dicts with: {user_id, name, email, phone, role}
    """
    try:
        UUID(str(person_id))
    except (TypeError, ValueError):
        logger.warning(
            "Skipping database recipient lookup for non-UUID person_id %r; using configured fallbacks",
            person_id,
        )
        return []

    try:
        query = text("""
            SELECT 
                u.id as user_id,
                u.name,
                u.email,
                u.role
            FROM users u
            INNER JOIN person_watchers pw ON u.id = pw.user_id
            WHERE pw.person_id = :person_id
              AND u.deleted_at IS NULL
              AND pw.deleted_at IS NULL
        """)
        
        result = await session.execute(query, {"person_id": person_id})
        rows = result.fetchall()
        
        recipients = [
            {
                "user_id": str(row[0]),
                "name": row[1],
                "email": row[2],
                "phone": None,  # Not stored in users table, could extend
                "role": row[3]
            }
            for row in rows
        ]
        
        return recipients
    except Exception as e:
        logger.error(f"Failed to fetch alert recipients for {person_id}: {e}", exc_info=True)
        return []


async def log_alert_to_database(
    session: AsyncSession,
    event_type: str,
    channel: str,
    recipient: str,
    status: str = "sent"
) -> bool:
    """
    Log alert to PostgreSQL alert_log table.
    
    Args:
        session: AsyncSession
        event_type: "fall_detected" | "emotion_distress" | "inactivity_detected"
        channel: "email" | "sms" | "websocket"
        recipient: email, phone number, or "broadcast"
        status: "sent" | "failed" | "pending"
    
    Returns:
        True if successful
    """
    try:
        insert_query = text("""
            INSERT INTO alert_log (event_type, channel, recipient, status, created_at)
            VALUES (:event_type, :channel, :recipient, :status, NOW())
        """)
        
        await session.execute(
            insert_query,
            {
                "event_type": event_type,
                "channel": channel,
                "recipient": recipient,
                "status": status
            }
        )
        await session.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to log alert: {e}", exc_info=True)
        return False
