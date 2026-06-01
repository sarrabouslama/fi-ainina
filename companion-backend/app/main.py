import asyncio
import contextlib
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.alerts.router import router as alerts_router
from app.auth.router import router as auth_router
from app.config import settings
from app.conversations.router import router as conversations_router
from app.dashboard.router import router as dashboard_router
from app.database import Base, SessionLocal, engine
from app.events.manager import manager
from app.events.router import router as events_router
from app.health.router import router as health_router
from app.main_state import health_state
from app.microservices.alerts_ws import run_alerts_ws_bridge
from app.microservices.base import AsyncServiceClient
from app.reviews.router import router as reviews_router
from app.users.router import router as users_router


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title='Companion Backend', version='1.0.0')
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:3000',
        'http://localhost:3001',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:3001',
        'http://localhost:5173',
        'http://127.0.0.1:5173',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.middleware('http')
async def user_rate_limit_key(request: Request, call_next):
    return await call_next(request)


@app.on_event('startup')
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.alerts_bridge_task = asyncio.create_task(
        run_alerts_ws_bridge(settings.alerts_ws_url, SessionLocal)
    )
    app.state.health_poll_task = asyncio.create_task(health_poller())


@app.on_event('shutdown')
async def shutdown():
    for task_name in ('alerts_bridge_task', 'health_poll_task'):
        task = getattr(app.state, task_name, None)
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


async def health_poller():
    clients = {
        'llm':            AsyncServiceClient(settings.llm_base_url),
        'voice_assistant': AsyncServiceClient(settings.voice_base_url),
        'fall_detection': AsyncServiceClient('http://127.0.0.1:8003'),
        'emotion':        AsyncServiceClient('http://127.0.0.1:8004'),
        'alerts':         AsyncServiceClient('http://127.0.0.1:8005'),
    }
    previous = dict(health_state.status)
    try:
        while True:
            for name, client in clients.items():
                start = time.perf_counter()
                status = 'healthy'
                try:
                    await client._request('GET', '/health')
                except Exception:
                    status = 'unhealthy'
                latency = int((time.perf_counter() - start) * 1000)
                health_state.status[name] = status
                health_state.latency_ms[name] = latency
                if previous.get(name) != status:
                    await manager.broadcast({'type': 'service_health_change', 'payload': {'service': name, 'status': status}})
                previous[name] = status
            await asyncio.sleep(30)
    finally:
        for c in clients.values():
            await c.close()


@limiter.limit('100/minute')
@app.get('/')
async def root(request: Request):
    return {'service': 'companion-backend'}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(dashboard_router)
app.include_router(events_router)
app.include_router(reviews_router)
app.include_router(alerts_router)
app.include_router(conversations_router)
app.include_router(health_router)
