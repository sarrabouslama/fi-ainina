import logging

from fastapi import FastAPI

from app.capture import start_capture_thread
from app.metrics import register_metrics
from app.routes.status import router as status_router
from app.routes.stream import router as stream_router

app = FastAPI(title="FiAinina Emotion Service", version="1.0.0")
register_metrics(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.include_router(status_router)
app.include_router(stream_router)

@app.get("/health")
def health():
    """Return a simple health indicator for the service."""
    return {"service": "emotion_service", "status": "ok"}


@app.on_event("startup")
def startup() -> None:
    """Start the webcam capture worker when the app boots."""
    logger.info("Starting emotion service capture worker")
    start_capture_thread()
