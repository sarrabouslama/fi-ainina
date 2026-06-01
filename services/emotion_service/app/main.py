import asyncio
import logging

import cv2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.capture import get_current_frame, start_capture_thread, stop_capture_thread
from app.metrics import register_metrics
from app.routes.status import router as status_router
from app.routes.stream import router as stream_router

app = FastAPI(title="FiAinina Emotion Service", version="1.0.0")
register_metrics(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000",
                   "http://localhost:3001", "http://127.0.0.1:3001"],
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


@app.on_event("startup")
def startup() -> None:
    logger.info("Starting emotion service capture worker")
    start_capture_thread()
