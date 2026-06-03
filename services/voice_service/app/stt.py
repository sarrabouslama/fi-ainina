import whisper
import os

_MODEL_NAME = os.getenv("WHISPER_MODEL", "small")
model = whisper.load_model(_MODEL_NAME)

def transcribe(audio_path: str) -> str:
    result = model.transcribe(audio_path, language="fr")
    return result["text"]
