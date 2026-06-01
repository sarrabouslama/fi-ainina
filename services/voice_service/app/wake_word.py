import speech_recognition as sr
import sounddevice as sd
import soundfile as sf
import numpy as np
import scipy.io.wavfile as wav
import whisper
import httpx
import time

SAMPLE_RATE = 16000
VOICE_SERVICE_URL = "http://localhost:8002"
WAKE_WORDS = [
    "bonjour léa", "bonjour lea", "bonjour la",
    "bonjour", "bonne journée", "bon jour"
]

print(" Loading Whisper for command processing...")
model = whisper.load_model("medium")
print(" Ready!")

recognizer = sr.Recognizer()
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = True


def play_audio_sync(audio_path: str):
    """Play a WAV file and BLOCK until it finishes (no echo overlap)."""
    try:
        data, samplerate = sf.read(audio_path, dtype='float32')
        sd.play(data, samplerate)
        sd.wait()  # blocks until playback is done
    except Exception as e:
        print(f"   Audio playback error: {e}")


def listen_for_wake_word():
    """Uses Google Speech Recognition for wake word detection."""
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print(" Listening for 'Bonjour Léa'...")
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=4)
            text = recognizer.recognize_google(audio, language="fr-FR").lower()
            print(f"   heard: '{text}'")
            return any(wake in text for wake in WAKE_WORDS)
        except sr.WaitTimeoutError:
            print("   (silence)")
            return False
        except sr.UnknownValueError:
            print("   (incompris)")
            return False
        except sr.RequestError:
            print("   (Google API indisponible)")
            return False


def record_user_command(duration: int = 7) -> str:
    """Record user command after Léa has finished speaking."""
    print("🎙️ Posez votre question...")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='int16'
    )
    sd.wait()
    path = "user_command.wav"
    wav.write(path, SAMPLE_RATE, audio)
    print("   (enregistrement terminé)")
    return path


def send_to_pipeline(audio_path: str):
    try:
        with open(audio_path, "rb") as f:
            response = httpx.post(
                f"{VOICE_SERVICE_URL}/pipeline",
                files={"file": ("command.wav", f, "audio/wav")},
                timeout=120
            )
        if response.status_code == 200:
            with open("lea_response.wav", "wb") as out:
                out.write(response.content)
            print(" Léa répond...")
            play_audio_sync("lea_response.wav")  # also synchronous
            print(" Léa a répondu!")
        else:
            print(f" Pipeline error: {response.status_code}")
    except Exception as e:
        print(f" Impossible de joindre le service: {e}")


def start_wake_word_detector():
    print(" Dites 'Bonjour Léa' pour activer!")
    print("   (Ctrl+C pour arrêter)\n")

    while True:
        try:
            if listen_for_wake_word():
                print("\n Mot-clé détecté! Génération de la réponse vocale...")

                from app.tts import speak
                # Generate the "ready" audio
                speak("Oui, je vous écoute.", "ready.wav")

                # Play it synchronously — microphone is NOT recording yet
                play_audio_sync("ready.wav")

                # Brief pause so user knows it's their turn
                time.sleep(0.4)

                # NOW record the user's command (TTS is already silent)
                command_path = record_user_command(duration=7)

                # Send to LLM pipeline and play response
                send_to_pipeline(command_path)

                print("\n👂 Retour à l'écoute...\n")
                time.sleep(0.5)

        except KeyboardInterrupt:
            print("\n Arrêté.")
            break
        except Exception as e:
            print(f" Erreur: {e}")
            time.sleep(1)
