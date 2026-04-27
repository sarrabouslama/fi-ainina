from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from app.api.routes_detection import router as detection_router
from app.api.routes_camera import router as camera_router
from app.api.routes_events import router as events_router
from app.api.routes_config import router as config_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: start video capture thread on startup
    print("Fall Detection Service starting...")
    yield
    print("Fall Detection Service shutting down...")

app = FastAPI(
    title="ElderCare Fall Detection Service",
    version="1.0.0",
    description="P3 — Real-time fall detection using MediaPipe + OpenCV",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(detection_router, prefix="/detection", tags=["detection"])
app.include_router(camera_router,    prefix="/camera",    tags=["camera"])
app.include_router(events_router,    prefix="/events",    tags=["events"])
app.include_router(config_router,    prefix="/config",    tags=["config"])

@app.get("/health")
def health():
    return {"service": "fall_detection_service", "status": "ok", "version": "1.0.0"}
