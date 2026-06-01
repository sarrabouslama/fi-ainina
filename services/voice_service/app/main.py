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

    # Step 2: send to LLM service (P1)
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                "http://localhost:8001/chat",
                json={
                    "user_id": "00000000-0000-0000-0000-000000000001",
                    "message": text,
                    "emotion": "auto",
                    "synthesize_voice": False
                }
            )
            llm_response = response.json().get("response", "Je n'ai pas compris.")
    except Exception as e:
        print(f" LLM service not available: {e}")
        llm_response = "Je suis désolée, je n'arrive pas à joindre mon service de réponse. Veuillez réessayer dans quelques instants."

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