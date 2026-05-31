import speech_recognition as sr
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import whisper
import httpx
import os
import time

SAMPLE_RATE = 16000
VOICE_SERVICE_URL = "http://localhost:8002"
WAKE_WORDS = [
    "bonjour léa", "bonjour lea", "bonjour la",
    "bonjour", "bonne journée", "bon jour"
]

print(" Loading Whisper for command processing...")
model = whisper.load_model("small")
print(" Ready!")

# Initialize recognizer
recognizer = sr.Recognizer()
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = True

def listen_for_wake_word():
    """Uses Google Speech Recognition for wake word — much more accurate."""
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print(" Listening for 'Bonjour Léa'... (beep when ready)")
        os.system('powershell -c "[console]::beep(800,200)"')
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=4)
            text = recognizer.recognize_google(audio, language="fr-FR").lower()
            print(f"   heard: '{text}'")
            return any(wake in text for wake in WAKE_WORDS)
        except sr.WaitTimeoutError:
            print("   (no speech detected)")
            return False
        except sr.UnknownValueError:
            print("   (could not understand)")
            return False
        except sr.RequestError:
            print("   (Google API error — check internet)")
            return False

def record_user_command(duration: int = 5) -> str:
    """Record user command using sounddevice."""
    print("🎙️ Listening for your command...")
    os.system('powershell -c "[console]::beep(1000,300)"')
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
    try:
        with open(audio_path, "rb") as f:
            response = httpx.post(
                f"{VOICE_SERVICE_URL}/pipeline",
                files={"file": ("command.wav", f, "audio/wav")},
                timeout=30
            )
        if response.status_code == 200:
            with open("lea_response.wav", "wb") as out:
                out.write(response.content)
            os.system("start lea_response.wav")
            print(" Léa responded!")
        else:
            print(f" Pipeline error: {response.status_code}")
    except Exception as e:
        print(f" Could not reach voice service: {e}")

def start_wake_word_detector():
    print(" Say 'Bonjour Léa' to activate!")
    print("   (Press Ctrl+C to stop)\n")

    while True:
        try:
            if listen_for_wake_word():
                print("\n Wake word detected! Léa is listening...")
                from app.tts import speak
                speak("Oui, je vous écoute. Posez votre question.", "ready.wav")
                os.system("start ready.wav")
                time.sleep(3)
                command_path = record_user_command(duration=5)
                send_to_pipeline(command_path)
                print("\n👂 Back to listening...\n")
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n Stopped.")
            break
        except Exception as e:
            print(f" Error: {e}")
            time.sleep(1)