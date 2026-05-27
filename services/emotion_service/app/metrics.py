from fastapi import FastAPI, Request, Response
import time
from prometheus_client import Counter, Histogram, CONTENT_TYPE_LATEST, REGISTRY, generate_latest

REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "http_status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_latency_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)


def register_metrics(app: FastAPI) -> None:
    @app.middleware("http")
    async def prometheus_http_middleware(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        elapsed = time.time() - start
        REQUEST_COUNTER.labels(
            method=request.method,
            endpoint=request.url.path,
            http_status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(elapsed)
        return response

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
