from contextlib import asynccontextmanager
import base64
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.external_services import get_detected_emotion, synthesize_speech
from app.llm_engine import generate_chat_response, stream_chat_response
from app.database import close_pool
from app.metrics import register_metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_pool()


app = FastAPI(title="FiAinina LLM Service", version="1.0.0", lifespan=lifespan)
register_metrics(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000",
                   "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE endpoint — yields tokens as Ollama generates them."""
    emotion = request.emotion
    if emotion is None or emotion.lower() == "auto":
        emotion = await get_detected_emotion()

    async def generate():
        try:
            async for token in stream_chat_response(request.user_id, request.message, emotion):
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield f"data: {json.dumps({'done': True, 'emotion': emotion})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

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
