import whisper
import torch
from app.ffmpeg_path import ensure_ffmpeg_on_path

ensure_ffmpeg_on_path()

model = whisper.load_model("small")

def transcribe(audio_path: str) -> str:
    result = model.transcribe(audio_path, language="fr")
    return result["text"]
