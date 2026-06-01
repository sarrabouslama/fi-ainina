"""
main.py — FastAPI service for fall detection with state management.

Exposes:
  GET  /health                 - Service health check
  GET  /status                 - Current fall state + duration
  POST /reset                  - Manual reset of fall state (for false alarms)
  GET  /events                 - Recent fall events
  WS   /stream                 - Real-time fall events (websocket)
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import json
import asyncio
from collections import deque
from typing import Optional, Dict, List
from datetime import datetime

from app.config import settings
from app.core.analysis.fall_analysis_pipeline import fall_analyzer
from app.core.vision.video_capture import video_capture
from app.core.analysis.fall_detector import FallState, FallDetector
from app.core.utils.debug_utils import debug_print
from app.core.redis_publisher import publish_fall_event, get_redis_client


# ============================================================================# REDIS PUBLISHER — Publish fall events to alert_service
# ============================================================================

# Redis publishing is centralized in app.core.redis_publisher


# ============================================================================
# Detector wrapper: adapt core `FallDetector` to the service API
# ============================================================================


class DetectorWrapper:
    """Thin adapter around `FallDetector` to expose the same API used by routes.

    Keeps a small in-memory event history and provides `get_status()`,
    `reset()` and `get_events()` for compatibility with existing endpoints.
    """

    def __init__(self, detector: FallDetector, max_events: int = 100):
        self.detector = detector
        self.events: deque = deque(maxlen=max_events)

    # --- Compatibility properties -------------------------------------------------
    @property
    def current_state(self):
        return self.detector.state

    @property
    def fall_started_at(self):
        return getattr(self.detector, "fall_detected_at", None)

    @property
    def alert_sent_at(self):
        return getattr(self.detector, "alert_triggered_at", None)

    @property
    def state_changed_at(self):
        return getattr(self.detector, "state_entered_at", time.time())

    # --- Public API ---------------------------------------------------------------
    def reset(self) -> Dict:
        now = time.time()
        prev = self.detector.state
        self.detector.state = FallState.STABLE
        self.detector.state_entered_at = now
        self.detector.fall_detected_at = None
        self.detector.alert_triggered_at = None

        ev = {"event": "manual_reset", "timestamp": now, "previous_state": prev.value}
        self._log_event(ev)
        debug_print("[DETECTOR_WRAPPER] Manual reset", tag="STATE")
        return {"status": "reset", "timestamp": now}

    def get_status(self) -> Dict:
        now = time.time()
        fall_duration = None
        if self.fall_started_at:
            fall_duration = now - self.fall_started_at

        time_in_state = now - self.state_changed_at

        return {
            "state": self.current_state.value,
            "time_in_state_seconds": round(time_in_state, 2),
            "is_fallen": self.current_state in (FallState.FALLEN, FallState.ALERT),
            "fall_duration_seconds": round(fall_duration, 2) if fall_duration else None,
            "alert_sent": self.alert_sent_at is not None,
            "timestamp": now,
        }

    def get_events(self, limit: int = 50) -> List[Dict]:
        return list(self.events)[-limit:]

    def _log_event(self, event: Dict) -> None:
        event["logged_at"] = time.time()
        self.events.append(event)


# ============================================================================
# FASTAPI SETUP
# ============================================================================

# Global tracker (use core FallDetector as single source of truth)
state_tracker = DetectorWrapper(FallDetector())

# Background task: frame processing loop
processing_task = None
connected_clients: List[WebSocket] = []


async def process_frames_background():
    """
    Background task that processes video frames continuously.
    Sends fall events to connected WebSocket clients.
    """
    debug_print("[STARTUP] Frame processing loop started", tag="MAIN")
    
    try:
        while True:
            # Process one frame
            frame = video_capture.get_frame()
            if frame is None:
                await asyncio.sleep(0.01)
                continue
            
            # Analyze frame
            result = fall_analyzer.analyze(frame)

            # Run core detector (single source of truth)
            det_event = state_tracker.detector.process_frame(
                result.posture,
                result.body_angle_deg,
                getattr(result, "vsr", None),
            )

            if det_event:
                # Log event in wrapper history
                state_tracker._log_event({
                    "event": det_event.get("event"),
                    "timestamp": time.time(),
                    "details": det_event,
                })

                # Publish to Redis & broadcast to clients
                ev_type = det_event.get("event")
                if ev_type == "fall":
                    fall_event_for_redis = {
                        "event_type": "fall",
                        "user_id": settings.default_person_id,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "severity": det_event.get("severity", "high"),
                        "confidence": round(result.confidence.score, 3),
                        "metadata": {
                            "posture": result.posture,
                            "body_angle": round(result.body_angle_deg, 1),
                            "signals": result.confidence.signals,
                            "detector": det_event,
                        }
                    }
                    # Default behavior: do not publish transient 'fall'
                    # events to Redis (external systems). Keep broadcasting to
                    # local WebSocket clients so the UI still sees immediate
                    # detections, but only escalate via Redis on 'fall_detected'.
                    await broadcast_alert(fall_event_for_redis)

                elif ev_type == "fall_detected":
                    duration = det_event.get("duration_lying_seconds", 0)
                    alert_event_for_redis = {
                        "event_type": "fall_detected",
                        "user_id": settings.default_person_id,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "severity": "critical" if duration > 30 else ("high" if duration > 10 else "high"),
                        "confidence": round(result.confidence.score, 3),
                        "metadata": {
                            "duration_seconds": round(duration, 2),
                            "posture": result.posture,
                            "signals": result.confidence.signals,
                            "detector": det_event,
                        }
                    }
                    publish_fall_event(alert_event_for_redis)
                    await broadcast_alert(alert_event_for_redis)
            
            # Small delay to prevent CPU spinning
            await asyncio.sleep(0.01)
    
    except Exception as e:
        debug_print(f"[ERROR] Frame processing error: {e}", tag="MAIN")


async def broadcast_alert(event: Dict):
    """Send alert to all connected WebSocket clients."""
    disconnected = []
    
    for client in connected_clients:
        try:
            await client.send_json(event)
        except Exception:
            disconnected.append(client)
    
    # Remove disconnected clients
    for client in disconnected:
        connected_clients.remove(client)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    global processing_task
    
    # Startup
    debug_print("[STARTUP] Fall detection service starting...", tag="MAIN")
    video_capture.start()
    processing_task = asyncio.create_task(process_frames_background())
    
    yield
    
    # Shutdown
    debug_print("[SHUTDOWN] Fall detection service shutting down...", tag="MAIN")
    if processing_task:
        processing_task.cancel()
    video_capture.stop()


app = FastAPI(
    title="Fall Detection Service",
    description="Real-time fall detection with persistent state management",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health")
def health():
    """Service health check."""
    return {
        "service": settings.service_name,
        "status": "ok",
        "version": settings.service_version,
        "timestamp": time.time(),
    }


@app.get("/status")
def get_status():
    """
    Get current fall state and duration.
    
    Returns:
    - state: STABLE | FALLING | FALLEN | ALERT
    - is_fallen: bool (True if FALLEN or ALERT)
    - fall_duration_seconds: How long person has been on floor (or None)
    - alert_sent: Whether alert has been triggered
    """
    return state_tracker.get_status()


@app.post("/reset")
def reset_fall_state():
    """
    Manual reset of fall state. Use if false alarm detected.
    
    Returns:
    - status: "reset"
    - timestamp: When reset occurred
    """
    return state_tracker.reset()


@app.get("/events")
def get_events(limit: int = 50):
    """
    Get recent fall events.
    
    Query parameters:
    - limit: Max number of events to return (default: 50)
    
    Returns:
    - events: List of events with timestamps and details
    """
    return {
        "events": state_tracker.get_events(limit),
        "count": len(state_tracker.events),
    }


@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time fall events.
    
    Connects and sends:
    - fall events
    - alert events  
    - recovery events
    """
    await websocket.accept()
    connected_clients.append(websocket)
    
    debug_print(
        f"[WS] Client connected. Total clients: {len(connected_clients)}",
        tag="WEBSOCKET"
    )
    
    try:
        # Send current status on connect
        status = state_tracker.get_status()
        await websocket.send_json({
            "event": "status",
            "data": status,
        })
        
        # Keep connection alive
        while True:
            # Receive messages (to detect disconnects)
            await websocket.receive_text()
    
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        debug_print(
            f"[WS] Client disconnected. Total clients: {len(connected_clients)}",
            tag="WEBSOCKET"
        )
    except Exception as e:
        debug_print(f"[WS] Error: {e}", tag="WEBSOCKET")
        if websocket in connected_clients:
            connected_clients.remove(websocket)


# ============================================================================
# DEBUGGING ENDPOINTS (development only)
# ============================================================================

@app.get("/debug/state")
def debug_state():
    """Debug endpoint: Get internal state machine details."""
    if not settings.debug:
        return {"error": "Debug mode disabled"}, 403
    
    return {
        "current_state": state_tracker.current_state.value,
        "fall_started_at": state_tracker.fall_started_at,
        "alert_sent_at": state_tracker.alert_sent_at,
        "state_changed_at": state_tracker.state_changed_at,
        "now": time.time(),
    }


@app.post("/debug/inject-fall")
def debug_inject_fall():
    """Debug endpoint: Simulate a fall for testing."""
    if not settings.debug:
        return {"error": "Debug mode disabled"}, 403
    
    state_tracker.current_state = FallState.FALLEN
    state_tracker.fall_started_at = time.time()
    state_tracker.state_changed_at = time.time()
    
    return {"status": "Fall simulated", "timestamp": time.time()}


# ============================================================================
# CONFIGURATION SUMMARY
# ============================================================================

print(f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                    FALL DETECTION SERVICE INITIALIZED                      ║
╠════════════════════════════════════════════════════════════════════════════╣
║                           KEY SETTINGS                                     ║
├────────────────────────────────────────────────────────────────────────────┤
║  Confidence Threshold:     {settings.fall_confidence_threshold} (score must exceed this)
║  Persistence Window:       {settings.fall_persistence_seconds}s (score must stay above threshold)
║  Alert Timeout:            {settings.fall_alert_timeout}s (lying this long triggers ALERT)
║  Confirmation Time:        {settings.fall_confirmation_time}s (must be LYING to confirm)
║  Angular Velocity:         {settings.fall_angular_velocity_threshold}°/sec (fast collapse threshold)
║  VSR Velocity:             {settings.fall_vsr_velocity_threshold}/sec (body flattening threshold)
║  Intentional Lie-Down:     {settings.fall_intentional_lie_down_time}s (slower transitions ignored)
├────────────────────────────────────────────────────────────────────────────┤
║                        FALL STATE MACHINE                                   ║
├────────────────────────────────────────────────────────────────────────────┤
║  STABLE        → FALLING  : Fast motion detected (angular/VSR velocity)    ║
║  FALLING       → FALLEN   : Lying detected after fast motion               ║
║  FALLEN        → ALERT    : Lying for > {settings.fall_alert_timeout}s                       ║
║  ANY           → STABLE   : Person stands/sits again (RECOVERY)            ║
├────────────────────────────────────────────────────────────────────────────┤
║                          API ENDPOINTS                                     ║
├────────────────────────────────────────────────────────────────────────────┤
║  GET  /health           - Service status
║  GET  /status           - Current fall state + duration
║  POST /reset            - Manual reset (false alarm)
║  GET  /events           - Recent fall events
║  WS   /stream           - Real-time fall alerts (WebSocket)
╚════════════════════════════════════════════════════════════════════════════╝
""")
