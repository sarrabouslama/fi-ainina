from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
import shutil, os
from app.stt import transcribe
from app.tts import speak

app = FastAPI()

class TextInput(BaseModel):
    text: str

@app.get("/health")
def health():
    return {"status": "ok", "service": "voice_service"}

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    text = transcribe(temp_path)
    os.remove(temp_path)
    return {"text": text}

@app.post("/speak")
def speak_text(input: TextInput):
    output_path = "response.wav"
    speak(input.text, output_path)
    return FileResponse(output_path, media_type="audio/wav")