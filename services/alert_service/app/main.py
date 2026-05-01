"""
FiAinina Alert Service — Main Application

FastAPI service that:
1. Listens to Redis channels (fall_events, emotion_events, inactivity_events)
2. Deduplicates alerts using cooldown (5 min per user/event_type)
3. Dispatches notifications to 3 channels:
   - WebSocket (frontend, real-time)
   - Email (family members)
   - SMS (caregivers, via Twilio)
4. Logs all alerts to PostgreSQL for audit trail

Architecture:
- Background task: Redis subscriber (runs during startup)
- REST endpoints: /health, /alerts (GET/POST), /alerts/test
- WebSocket endpoint: /ws
"""

import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends
from fastapi.responses import JSONResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from app import config
from app.models import (
    AlertEvent, AlertHistoryResponse, AlertTestRequest, HealthCheckResponse, WebSocketMessage
)
from app.subscriber import redis_subscriber, create_redis_connection, close_redis_connection
from app.database import init_database, get_database_session, get_alert_recipients, log_alert_to_database
from app.handlers.cooldown_manager import CooldownManager
from app.handlers.websocket_handler import manager as ws_manager
from app.handlers.email_handler import email_handler
from app.handlers.sms_handler import sms_handler

# ─────────────────────────────────────────────────────────────
# Logging Configuration
# ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Global State
# ─────────────────────────────────────────────────────────────

# Database & Redis (initialized at startup)
database_engine = None
db_session_factory = None
redis_client: Optional[AsyncRedis] = None
cooldown_manager: Optional[CooldownManager] = None
subscriber_task: Optional[asyncio.Task] = None


# ─────────────────────────────────────────────────────────────
# Alert Processing Logic
# ─────────────────────────────────────────────────────────────

async def handle_alert(event: AlertEvent):
    """
    Central alert processing function.
    
    Flow:
    1. Check cooldown (skip if recent)
    2. Fetch recipients from PostgreSQL
    3. Dispatch to 3 channels in parallel
    4. Log to PostgreSQL
    5. Record cooldown reset
    """
    logger.info(f"Processing alert: {event.event_type} from {event.user_id} (severity: {event.severity})")
    
    # Step 1: Check cooldown
    if not cooldown_manager.can_send_alert(event.user_id, event.event_type):
        logger.debug(f"Alert skipped due to cooldown: {event.event_type}/{event.user_id}")
        return
    
    # Step 2: Fetch recipients from database
    async with db_session_factory() as session:
        recipients = await get_alert_recipients(session, event.user_id)
    
    if not recipients:
        logger.warning(f"No recipients found for {event.user_id}, sending only via WebSocket")
    
    # Step 3: Create WebSocket message
    ws_message = WebSocketMessage(
        event_type=event.event_type,
        user_id=event.user_id,
        timestamp=event.timestamp,
        severity=event.severity,
        confidence=event.confidence,
        metadata=event.metadata,
        message_type="alert"
    )
    
    # Step 4: Dispatch to all channels in parallel
    tasks = []
    
    # WebSocket (always, broadcast to all connected clients)
    tasks.append(ws_manager.broadcast(ws_message))
    
    # Email (to family members)
    email_recipients = [r["email"] for r in recipients if r.get("email") and r["role"] == "family"]
    if email_recipients:
        tasks.append(email_handler.send_alert(event, email_recipients))
    
    # SMS (to caregivers)
    sms_recipients = [r.get("phone") for r in recipients if r.get("phone") and r["role"] in ["caregiver", "admin"]]
    sms_recipients = [r for r in sms_recipients if r]  # Filter None values
    if sms_recipients:
        tasks.append(sms_handler.send_alert(event, sms_recipients))
    
    # Wait for all to complete
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error in dispatch task {i}: {result}")
    except Exception as e:
        logger.error(f"Error during parallel dispatch: {e}", exc_info=True)
    
    # Step 5: Log to PostgreSQL (audit trail)
    async with db_session_factory() as session:
        # Log WebSocket
        await log_alert_to_database(session, event.event_type, "websocket", "broadcast", "sent")
        
        # Log email
        for recipient in email_recipients:
            await log_alert_to_database(session, event.event_type, "email", recipient, "sent")
        
        # Log SMS
        for recipient in sms_recipients:
            await log_alert_to_database(session, event.event_type, "sms", recipient, "sent")
    
    # Step 6: Record cooldown
    cooldown_manager.record_alert_sent(event.user_id, event.event_type)
    
    logger.info(f"Alert processed successfully: {event.event_type}/{event.user_id}")


# ─────────────────────────────────────────────────────────────
# FastAPI Startup & Shutdown
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI startup and shutdown logic."""
    
    # Startup
    logger.info("Initializing Alert Service...")
    
    try:
        # Validate configuration
        config.validate_config()
        logger.info("Configuration validated")
        
        # Initialize database
        global database_engine, db_session_factory
        database_engine = await init_database()
        db_session_factory = await get_database_session(database_engine)
        
        # Initialize Redis
        global redis_client, cooldown_manager
        redis_client = await create_redis_connection()
        cooldown_manager = CooldownManager(redis_client)
        
        # Start Redis subscriber as background task
        global subscriber_task
        subscriber_task = asyncio.create_task(
            redis_subscriber(redis_client, handle_alert)
        )
        logger.info("Redis subscriber started")
        
        logger.info("✓ Alert Service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Alert Service: {e}", exc_info=True)
        raise
    
    yield  # Application is running
    
    # Shutdown
    logger.info("Shutting down Alert Service...")
    
    try:
        # Cancel subscriber task
        if subscriber_task:
            subscriber_task.cancel()
            try:
                await subscriber_task
            except asyncio.CancelledError:
                pass
        
        # Close Redis
        if redis_client:
            await close_redis_connection(redis_client)
        
        # Close database
        if database_engine:
            await database_engine.dispose()
        
        logger.info("✓ Alert Service shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


# ─────────────────────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="FiAinina Alert Service",
    version="1.0.0",
    description="Real-time alert dispatching: WebSocket, Email, SMS",
    lifespan=lifespan
)


# ─────────────────────────────────────────────────────────────
# REST Endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        - status: "ok" if all systems healthy
        - redis_connected: Redis ping result
        - database_connected: Database ping result
    """
    redis_ok = False
    db_ok = False
    
    try:
        if redis_client:
            await redis_client.ping()
            redis_ok = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
    
    try:
        if db_session_factory:
            async with db_session_factory() as session:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
    
    status = "ok" if (redis_ok and db_ok) else "degraded"
    
    return HealthCheckResponse(
        service="alert_service",
        status=status,
        redis_connected=redis_ok,
        database_connected=db_ok,
        timestamp=datetime.utcnow()
    )


@app.get("/alerts", response_model=AlertHistoryResponse)
async def get_alert_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Get alert history (paginated).
    
    Query params:
        - limit: max records to return (default 50, max 500)
        - offset: pagination offset (default 0)
    
    Returns:
        - total: total number of alerts in database
        - alerts: list of AlertLogEntry objects
    """
    from sqlalchemy import text
    
    if not db_session_factory:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        async with db_session_factory() as session:
            # Get total count
            count_result = await session.execute(text("SELECT COUNT(*) FROM alert_log WHERE deleted_at IS NULL"))
            total = count_result.scalar()
            
            # Get paginated results
            query = text("""
                SELECT id, event_type, channel, recipient, status, created_at
                FROM alert_log
                WHERE deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            result = await session.execute(
                query,
                {"limit": limit, "offset": offset}
            )
            rows = result.fetchall()
            
            alerts = []
            for row in rows:
                from app.models import AlertLogEntry
                alert = AlertLogEntry(
                    id=row[0],
                    event_type=row[1],
                    channel=row[2],
                    recipient=row[3],
                    status=row[4],
                    created_at=row[5]
                )
                alerts.append(alert)
            
            return AlertHistoryResponse(
                total=total,
                limit=limit,
                offset=offset,
                alerts=alerts
            )
    except Exception as e:
        logger.error(f"Failed to fetch alert history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch alert history")


@app.post("/alerts/test")
async def create_test_alert(request: AlertTestRequest):
    """
    Create a test alert manually (for testing without P3/P4).
    
    Body:
        - event_type: "fall_detected" | "emotion_distress" | "inactivity_detected"
        - user_id: monitored person ID
        - severity: "high" | "medium" | "low"
        - metadata: optional dict
    
    Returns:
        - alert_id: UUID of created alert
        - status: "queued" (will be processed)
    """
    try:
        event = AlertEvent(
            event_type=request.event_type,
            user_id=request.user_id,
            timestamp=datetime.utcnow(),
            severity=request.severity,
            confidence=1.0,  # Test alert
            metadata=request.metadata or {}
        )
        
        alert_id = str(uuid4())
        
        # Queue for processing
        asyncio.create_task(handle_alert(event))
        
        logger.info(f"Test alert created: {alert_id}")
        return {
            "alert_id": alert_id,
            "status": "queued",
            "event_type": event.event_type,
            "user_id": event.user_id
        }
    except Exception as e:
        logger.error(f"Failed to create test alert: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


# ─────────────────────────────────────────────────────────────
# WebSocket Endpoint
# ─────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time alert streaming.
    
    Connected clients receive all alerts in JSON format:
    {
        "event_type": "fall_detected",
        "user_id": "elder_001",
        "timestamp": "2025-01-15T14:30:00Z",
        "severity": "high",
        "confidence": 0.92,
        "metadata": {...},
        "message_type": "alert"
    }
    
    Frontend can filter by user_id or severity as needed.
    """
    await ws_manager.connect(websocket)
    logger.info(f"WebSocket client connected")
    
    try:
        # Keep connection open, receive heartbeats or disconnection
        while True:
            data = await websocket.receive_text()
            logger.debug(f"WebSocket received: {data}")
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        ws_manager.disconnect(websocket)


# ─────────────────────────────────────────────────────────────
# Startup Message
# ─────────────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    logger.info("""
    
    ╔═══════════════════════════════════════════════════════════╗
    ║         FiAinina Alert Service — Starting Up             ║
    ║                                                           ║
    ║  Listening on:                                          ║
    ║    • Redis channels: fall_events, emotion_events,        ║
    ║                     inactivity_events                    ║
    ║    • REST endpoints: /health, /alerts, /alerts/test     ║
    ║    • WebSocket: /ws                                      ║
    ║                                                           ║
    ║  Notification channels:                                 ║
    ║    ✓ WebSocket (frontend, real-time)                    ║
    ║    ✓ Email (family members)                             ║
    ║    ✓ SMS (caregivers, via Twilio)                       ║
    ║                                                           ║
    ║  Cooldown: {} min per event/user                        ║
    ╚═══════════════════════════════════════════════════════════╝
    
    """.format(config.ALERT_COOLDOWN_MINUTES)
    )
