from fastapi import FastAPI
from app.metrics import register_metrics

app = FastAPI(title="FiAinina Voice Service", version="1.0.0")
register_metrics(app)

@app.get("/health")
def health():
    return {"service": "voice_service", "status": "ok"}

# TODO P2: implement voice endpoints
# POST /transcribe        (audio → text via Whisper)
# POST /synthesize        (text → audio via TTS)
# GET  /memory/{person_id}
# POST /memory/{person_id}
