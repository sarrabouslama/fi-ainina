from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import shutil, os, httpx, threading
from app.stt import transcribe
from app.tts import speak
from app.redis_listener import start_redis_listener
from app.wake_word import start_wake_word_detector

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000",
                   "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start Redis listener in background when server starts
@app.on_event("startup")
async def startup_event():
    thread = threading.Thread(target=start_redis_listener, daemon=True)
    thread.start()
    print(" Voice service started!")

class TextInput(BaseModel):
    text: str
    speed: float = 1.0

# ── Health check ──────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "voice_service", "port": 8002}

# ── STT: audio → text ─────────────────────────────────────
@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    text = transcribe(temp_path)
    os.remove(temp_path)
    return {"text": text}

# ── TTS: text → audio ─────────────────────────────────────
@app.post("/speak")
def speak_text(input: TextInput):
    output_path = "response.wav"
    speak(input.text, output_path, speed=input.speed)
    return FileResponse(output_path, media_type="audio/wav")

COMPANION_URL = "http://127.0.0.1:8000"
_cached_elderly_user_id: str | None = None

async def get_elderly_user_id() -> str:
    """Fetch the active elderly user's ID from the companion backend."""
    global _cached_elderly_user_id
    if _cached_elderly_user_id:
        return _cached_elderly_user_id
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{COMPANION_URL}/internal/elderly-user-id")
            if r.status_code == 200:
                _cached_elderly_user_id = r.json().get("user_id")
                return _cached_elderly_user_id
    except Exception as e:
        print(f" Could not fetch elderly user id: {e}")
    return "00000000-0000-0000-0000-000000000001"


# ── Full pipeline: audio → LLM → audio ───────────────────
@app.post("/pipeline")
async def full_pipeline(file: UploadFile = File(...)):
    # Step 1: transcribe user voice
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    text = transcribe(temp_path)
    os.remove(temp_path)
    print(f" Transcribed: {text}")

    user_id = await get_elderly_user_id()

    # Step 2: send to LLM service via streaming endpoint (more resilient)
    llm_response = None
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            async with client.stream(
                "POST",
                "http://localhost:8001/chat/stream",
                json={"user_id": user_id, "message": text, "emotion": "auto"},
            ) as resp:
                full = ""
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        import json as _json
                        try:
                            chunk = _json.loads(line[6:])
                            if chunk.get("token"):
                                full += chunk["token"]
                        except Exception:
                            pass
                if full.strip():
                    llm_response = full.strip()
    except Exception as e:
        print(f" LLM streaming failed: {e}")

    if not llm_response:
        print(" LLM gave no response — service may be down or Redis is dropping")
        llm_response = "Je suis désolée, je n'arrive pas à répondre pour le moment. Veuillez réessayer."

    print(f" LLM response: {llm_response}")

    # Step 3: speak the response
    output_path = "pipeline_response.wav"
    speak(llm_response, output_path)
    return FileResponse(output_path, media_type="audio/wav")

@app.post("/wake-word/start")
def start_wake_word():
    thread = threading.Thread(target=start_wake_word_detector, daemon=True)
    thread.start()
    return {"status": "Wake word detector started", "wake_word": "Bonjour Léa"}