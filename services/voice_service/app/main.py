from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
import shutil, os, httpx, threading
from app.stt import transcribe
from app.tts import speak
from app.redis_listener import start_redis_listener

app = FastAPI()

# Start Redis listener in background when server starts
@app.on_event("startup")
async def startup_event():
    thread = threading.Thread(target=start_redis_listener, daemon=True)
    thread.start()
    print("✅ Voice service started!")

class TextInput(BaseModel):
    text: str

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
    speak(input.text, output_path)
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
    print(f"📝 Transcribed: {text}")

    # Step 2: send to LLM service (P1)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "http://localhost:8001/chat",
                json={"message": text}
            )
            llm_response = response.json().get("response", "Je n'ai pas compris.")
    except Exception as e:
        print(f"⚠️ LLM service not available: {e}")
        llm_response = f"J'ai bien entendu: {text}"

    print(f"🤖 LLM response: {llm_response}")

    # Step 3: speak the response
    output_path = "pipeline_response.wav"
    speak(llm_response, output_path)
    return FileResponse(output_path, media_type="audio/wav")