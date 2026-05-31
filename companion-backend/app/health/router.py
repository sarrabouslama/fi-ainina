from fastapi import APIRouter

from app.main_state import health_state


router = APIRouter(tags=['health'])


@router.get('/health')
async def health():
    overall = 'healthy' if all(v == 'healthy' for v in health_state.status.values()) else 'degraded'
    return {'overall_status': overall, 'services': health_state.status, 'latency_ms': health_state.latency_ms}
