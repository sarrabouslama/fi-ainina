import asyncio
import logging

import cv2
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.capture import get_current_frame, start_capture_thread, stop_capture_thread
from app import config as app_config
from app.metrics import register_metrics
from app.routes.status import router as status_router
from app.routes.stream import router as stream_router

app = FastAPI(title="FiAinina Emotion Service", version="1.0.0")
register_metrics(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
        "http://localhost:5173", "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.include_router(status_router)
app.include_router(stream_router)


@app.get("/health")
def health():
    return {"service": "emotion_service", "status": "ok"}


@app.get("/video_feed")
async def video_feed():
    """MJPEG stream of the current camera frame."""
    async def generate():
        while True:
            frame = get_current_frame()
            if frame is None:
                await asyncio.sleep(0.05)
                continue
            ret, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if not ret:
                await asyncio.sleep(0.05)
                continue
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
            await asyncio.sleep(0.033)

    return StreamingResponse(generate(), media_type='multipart/x-mixed-replace; boundary=frame')


@app.post("/camera/start")
def camera_start():
    """Start (or restart) the emotion detection camera."""
    start_capture_thread()
    return {"status": "started", "service": "emotion"}


@app.post("/camera/stop")
def camera_stop():
    """Stop the emotion detection camera."""
    stop_capture_thread()
    return {"status": "stopped", "service": "emotion"}


async def _resolve_elderly_user() -> None:
    """Query the companion backend for active elderly users and set USER_ID from the DB."""
    url = f"{app_config.COMPANION_BACKEND_URL}/users/elderly/active"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            elderly = resp.json()
        if elderly:
            app_config.USER_ID = elderly[0]["id"]
            logger.info(
                "Resolved monitored user from DB: %s (%s)",
                elderly[0].get("full_name"), app_config.USER_ID,
            )
            if len(elderly) > 1:
                logger.info(
                    "Multiple elderly users found (%d). Monitoring the first one. "
                    "Set USER_ID in .env to override.",
                    len(elderly),
                )
        else:
            logger.warning("No active elderly users found in the database. Alerts will use WebSocket only.")
    except Exception as exc:
        logger.warning("Could not reach companion backend at %s: %s. USER_ID stays as '%s'.",
                       url, exc, app_config.USER_ID)


@app.on_event("startup")
async def startup() -> None:
    await _resolve_elderly_user()
    logger.info("Starting emotion service capture worker (USER_ID=%s)", app_config.USER_ID)
    start_capture_thread()
