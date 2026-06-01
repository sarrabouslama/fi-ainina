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
    speak(input.text, output_path)
    return FileResponse(output_path, media_type="audio/wav")

# ── Full pipeline: audio → LLM → audio ───────────────────
@app.post("/pipeline")
async def full_pipeline(file: UploadFile = File(...)):
    try:
        print(f"\n[PIPELINE] Starting pipeline for file: {file.filename}")
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"[PIPELINE] File saved to: {temp_path}")
        
        text = transcribe(temp_path)
        print(f"[PIPELINE] Transcribed text: '{text}'")
        os.remove(temp_path)

        if not text or text.strip() == "":
            print(f"[PIPELINE] ERROR: Transcription returned empty text")
            return {"error": "Could not transcribe audio"}, 400

        print(f"[PIPELINE] Sending to LLM service: '{text}'")
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    "http://localhost:8001/chat",
                    json={"user_id": "anonymous", "message": text, "emotion": "neutral"}
                )
                response.raise_for_status()
                llm_response = response.json().get("response", "Je n'ai pas compris.")
                print(f"[PIPELINE] LLM response: '{llm_response}'")
        except Exception as e:
            print(f"[PIPELINE] ERROR: LLM service not available: {e}")
            llm_response = f"J'ai bien entendu: {text}"

        print(f"[PIPELINE] Generating speech for: '{llm_response}'")
        output_path = "pipeline_response.wav"
        speak(llm_response, output_path)
        print(f"[PIPELINE] Speech generated: {output_path}")
        
        if not os.path.exists(output_path):
            print(f"[PIPELINE] ERROR: Speech file not created")
            return {"error": "Could not generate speech"}, 400
            
        print(f"[PIPELINE] Pipeline complete, returning audio")
        return FileResponse(output_path, media_type="audio/wav")
    except Exception as e:
        print(f"[PIPELINE] CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}, 500

@app.post("/wake-word/start")
def start_wake_word():
    from app.wake_word import start_wake_word_detector

    thread = threading.Thread(target=start_wake_word_detector, daemon=True)
    thread.start()
    return {"status": "Wake word detector started", "wake_word": "Bonjour Léa"}