from fastapi import FastAPI

app = FastAPI(title="FiAinina Alert Service", version="1.0.0")

@app.get("/health")
def health():
    return {"service": "alert_service", "status": "ok"}

# TODO P5: implement alert endpoints
# GET  /alerts            (alert history)
# POST /alerts/test       (send test alert)
# Subscriber: Redis channel "fall_events", "inactivity_events", "emotion_events"
