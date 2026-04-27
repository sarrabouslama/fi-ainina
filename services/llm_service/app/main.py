from fastapi import FastAPI

app = FastAPI(title="FiAinina LLM Service", version="1.0.0")

@app.get("/health")
def health():
    return {"service": "llm_service", "status": "ok"}

# TODO P1: implement conversation endpoints
# POST /chat
# GET  /history/{person_id}
