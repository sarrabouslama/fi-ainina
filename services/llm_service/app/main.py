from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.llm_engine import generate_chat_response
from app.config import settings
from app.metrics import register_metrics

app = FastAPI(title="FiAinina LLM Service", version="1.0.0")
register_metrics(app)

class ChatRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user")
    message: str = Field(..., description="The user's message")
    emotion: str = Field(default="neutral", description="The current emotion of the user (e.g., happy, sad, neutral)")

class ChatResponse(BaseModel):
    response: str = Field(..., description="The generated response from the assistant")

@app.get("/health")
def health():
    return {"service": "llm_service", "status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        reply = await generate_chat_response(
            user_id=request.user_id,
            message=request.message,
            emotion=request.emotion
        )
        return ChatResponse(response=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
