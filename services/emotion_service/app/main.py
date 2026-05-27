from fastapi import FastAPI
from app.metrics import register_metrics

app = FastAPI(title="FiAinina Emotion Service", version="1.0.0")
register_metrics(app)

@app.get("/health")
def health():
    return {"service": "emotion_service", "status": "ok"}

# TODO P4: implement emotion/inactivity endpoints
# GET  /status            (current emotion + motion level)
# WS   /stream            (real-time emotion events)
