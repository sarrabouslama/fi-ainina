import torch
import torch.serialization
from TTS.utils.radam import RAdam
from TTS.api import TTS

torch.serialization.add_safe_globals([RAdam])

# VITS is end-to-end (no separate vocoder) → 5-10x faster than Tacotron2 on CPU
tts = TTS(model_name="tts_models/fr/css10/vits", progress_bar=False, gpu=False)

def speak(text: str, output_path: str = "output.wav", speed: float = 1.0):
    tts.tts_to_file(text=text, file_path=output_path, speed=speed)
    return output_path
