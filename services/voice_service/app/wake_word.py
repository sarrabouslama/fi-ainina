import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import whisper
import torch
import httpx
import os
import time

# ── Settings ──────────────────────────────────────────────
SAMPLE_RATE = 16000
CHUNK_DURATION = 3        # seconds to record each chunk
WAKE_WORDS = [
    "bonjour léa", "bonjour lea", "bonjour lé", "bonjour la",
    "bonjour là", "bonjour les", "bonjour l", "bon jour léa",
    "bonsoir léa", "bonsoir lea", "bonjour léas", "bonjour léah"
]
VOICE_SERVICE_URL = "http://localhost:8002"

# ── Load Whisper once ──────────────────────────────────────
print(" Loading Whisper for wake word detection...")
model = whisper.load_model("tiny")  # tiny = fastest for wake word
print(" Wake word detector ready — say 'Bonjour Léa' to activate!")

def record_chunk(duration: int = CHUNK_DURATION) -> str:
    """Record audio chunk and save to temp file."""
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='int16'
    )
    sd.wait()
    path = "wake_chunk.wav"
    wav.write(path, SAMPLE_RATE, audio)
    return path

def is_wake_word(audio_path: str) -> bool:
    """Check if wake word was spoken in audio chunk."""
    result = model.transcribe(audio_path, language="fr", fp16=False)
    text = result["text"].lower().strip()
    print(f"   heard: '{text}'")
    return any(wake in text for wake in WAKE_WORDS)

def record_user_command(duration: int = 5) -> str:
    """Record user command after wake word detected."""
    print(" Listening for your command...")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='int16'
    )
    sd.wait()
    path = "user_command.wav"
    wav.write(path, SAMPLE_RATE, audio)
    return path

def send_to_pipeline(audio_path: str):
    """Send audio to voice service pipeline endpoint."""
    try:
        with open(audio_path, "rb") as f:
            response = httpx.post(
                f"{VOICE_SERVICE_URL}/pipeline",
                files={"file": ("command.wav", f, "audio/wav")},
                timeout=30
            )
        if response.status_code == 200:
            # Save and play the response audio
            with open("lea_response.wav", "wb") as out:
                out.write(response.content)
            os.system("start lea_response.wav")
            print(" Léa responded!")
        else:
            print(f" Pipeline error: {response.status_code}")
    except Exception as e:
        print(f" Could not reach voice service: {e}")

def start_wake_word_detector():
    """Main loop — continuously listen for wake word."""
    print(" Listening for 'Bonjour Léa'...")
    print("   (Press Ctrl+C to stop)\n")

    while True:
        try:
            # Record a short chunk
            audio_path = record_chunk(CHUNK_DURATION)

            
            
            if is_wake_word(audio_path):
                print("\n Wake word detected! Léa is listening...")

                # Léa speaks to confirm she's ready
        
                from app.tts import speak
                speak("Oui, je vous écoute. Posez votre question.", "ready.wav")
                os.system("start ready.wav")
                time.sleep(3)  # wait for audio to finish playing
                # Record the actual command
                command_path = record_user_command(duration=5)

                # Send to pipeline
                send_to_pipeline(command_path)

                print("\n Back to listening for 'Bonjour Léa'...\n")
                time.sleep(1)  # brief pause before listening again

        except KeyboardInterrupt:
            print("\n Wake word detector stopped.")
            break
        except Exception as e:
            print(f" Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    start_wake_word_detector()