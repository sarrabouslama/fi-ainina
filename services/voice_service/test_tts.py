import torch
import torch.serialization
from TTS.utils.radam import RAdam

# Fix for PyTorch 2.6+ compatibility
torch.serialization.add_safe_globals([RAdam])

from TTS.api import TTS

print("Loading TTS model...")
tts = TTS(model_name="tts_models/fr/mai/tacotron2-DDC", progress_bar=False, gpu=False)

tts.tts_to_file(
    text="Bonjour, je suis votre assistant. Comment puis-je vous aider aujourd'hui?",
    file_path="output.wav"
)

print("✅ Audio saved to output.wav")