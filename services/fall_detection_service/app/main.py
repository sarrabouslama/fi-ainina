from fastapi import FastAPI

@app.get("/health")
def health():
    return {"service": "fall_detection_service", "status": "ok", "version": "1.0.0"}


# TODO P3: implement fall detection endpoints
# GET  /status            (current fall status + motion level)
# WS   /stream            (real-time fall events)
