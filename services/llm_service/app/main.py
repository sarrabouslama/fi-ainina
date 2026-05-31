from contextlib import asynccontextmanager
import base64

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.external_services import get_detected_emotion, synthesize_speech
from app.llm_engine import generate_chat_response
from app.database import close_pool
from app.metrics import register_metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_pool()


app = FastAPI(title="FiAinina LLM Service", version="1.0.0", lifespan=lifespan)
register_metrics(app)

class ChatRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user")
    message: str = Field(..., description="The user's message")
    emotion: str | None = Field(
        default=None,
        description="Current emotion. If omitted or set to 'auto', emotion_service is used.",
    )
    synthesize_voice: bool = Field(
        default=False,
        description="When true, ask voice_service to synthesize the assistant response.",
    )

class ChatResponse(BaseModel):
    response: str = Field(..., description="The generated response from the assistant")
    emotion: str = Field(..., description="The emotion used to generate the response")
    audio_base64: str | None = Field(default=None, description="Base64 encoded assistant audio, if requested")
    audio_content_type: str | None = Field(default=None, description="Audio MIME type, if audio was generated")

@app.get("/health")
def health():
    return {"service": "llm_service", "status": "ok"}

@app.post("/chat", response_model=ChatResponse, response_model_exclude_none=True)
async def chat(request: ChatRequest):
    try:
        emotion = request.emotion
        if emotion is None or emotion.lower() == "auto":
            emotion = await get_detected_emotion()

        reply = await generate_chat_response(
            user_id=request.user_id,
            message=request.message,
            emotion=emotion
        )

        audio_base64 = None
        audio_content_type = None
        if request.synthesize_voice:
            audio_bytes, audio_content_type = await synthesize_speech(reply)
            if audio_bytes:
                audio_base64 = base64.b64encode(audio_bytes).decode("ascii")

        return ChatResponse(
            response=reply,
            emotion=emotion,
            audio_base64=audio_base64,
            audio_content_type=audio_content_type,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
