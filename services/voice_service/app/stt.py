import whisper
import torch

model = whisper.load_model("medium")

def transcribe(audio_path: str) -> str:
    result = model.transcribe(audio_path, language="fr")
    return result["text"]