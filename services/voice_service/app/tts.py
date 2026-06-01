import collections
import torch
import torch.serialization
from TTS.utils.radam import RAdam
from TTS.api import TTS

# PyTorch 2.6 changed torch.load default weights_only to True.
# TTS checkpoint files require regular deserialization.
_original_torch_load = torch.load

def _torch_load_weights_only_false(f, *args, **kwargs):
    if "weights_only" not in kwargs:
        kwargs["weights_only"] = False
    return _original_torch_load(f, *args, **kwargs)

torch.load = _torch_load_weights_only_false

torch.serialization.add_safe_globals([
    RAdam,
    dict,
    collections.defaultdict,
    collections.OrderedDict,
    collections.Counter,
])

tts = TTS(model_name="tts_models/fr/mai/tacotron2-DDC", progress_bar=False, gpu=False)

def speak(text: str, output_path: str = "output.wav", speed: float = 1.0):
    tts.tts_to_file(text=text, file_path=output_path, speed=speed)
    return output_path