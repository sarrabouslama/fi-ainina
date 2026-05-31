import torch
import torch.serialization
from TTS.utils.radam import RAdam
from TTS.api import TTS

torch.serialization.add_safe_globals([RAdam])

tts = TTS(model_name="tts_models/fr/mai/tacotron2-DDC", progress_bar=False, gpu=False)

def speak(text: str, output_path: str = "output.wav", speed: float = 1.0):
    tts.tts_to_file(text=text, file_path=output_path, speed=speed)
    return output_path