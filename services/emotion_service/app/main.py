from fastapi import FastAPI

app = FastAPI(title="ElderCare Emotion Service", version="1.0.0")

@app.get("/health")
def health():
    return {"service": "emotion_service", "status": "ok"}

# TODO P4: implement emotion/inactivity endpoints
# GET  /status            (current emotion + motion level)
# WS   /stream            (real-time emotion events)
