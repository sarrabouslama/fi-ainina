import redis
import threading
import json
import os
import time
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import httpx
import whisper as whisper_module
from app.tts import speak

REDIS_URL = "redis://localhost:6379/0"
CHANNEL_FALL = "fall_events"
CHANNEL_ALERT = "fall_alerts"
SAMPLE_RATE = 16000

# Load STT model once
print(" Loading Whisper for fall response detection...")
stt_model = whisper_module.load_model("small")
print(" Whisper loaded for fall detection!")

def publish_alert(event: dict):
    """Always publish to alert service with full context."""
    try:
        r = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=30,
            socket_connect_timeout=10
        )
        r.publish(CHANNEL_ALERT, json.dumps(event))
        print(f" Alert published to '{CHANNEL_ALERT}': {event}")
    except Exception as e:
        print(f" Could not publish alert: {e}")

def record_response(duration: int = 7) -> str:
    """Record the elderly person's response after alert."""
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='int16'
    )
    sd.wait()
    path = "fall_response.wav"
    wav.write(path, SAMPLE_RATE, audio)
    return path

def transcribe_response(audio_path: str) -> str:
    """Transcribe with auto language detection."""
    result = stt_model.transcribe(audio_path, fp16=False)
    return result["text"]

def analyze_response(text: str):
    """
    Returns:
    - 'needs_help' if person needs help
    - 'okay' if person is fine
    - 'no_response' if nothing detected
    - 'unclear' if can't determine
    """
    text_lower = text.lower().strip()

    if not text_lower:
        return "no_response"

    needs_help = any(word in text_lower for word in [
        # French
        "aide", "aidez", "mal", "blessé", "blessée", "oui", "secours",
        "ambulance", "docteur", "douleur", "souffre", "tombé", "chute",
        "appelle", "appelez", "vite", "urgent",
        # English
        "help", "hurt", "pain", "yes", "doctor", "emergency", "fallen",
        "call", "please", "need"
    ])

    is_okay = any(word in text_lower for word in [
        # French
        "bien", "ça va", "non", "pas besoin", "okay", "pas mal",
        "parfait", "tranquille", "debout", "relevé",
        # English
        "fine", "ok", "good", "no", "alright", "okay"
    ])

    if needs_help:
        return "needs_help"
    elif is_okay:
        return "okay"
    else:
        return "unclear"

def handle_fall_event(data: dict):
    event_type = data.get("event_type", "unknown")
    person_id = data.get("person_id", "unknown")

    print(f" Fall event received! type={event_type} person={person_id}")

    # Step 1 — Speak the alert loudly
    speak(
        "Attention! Une chute a été détectée. Êtes-vous blessé? Répondez s'il vous plaît.",
        "alert.wav"
    )
    os.system("start alert.wav")
    time.sleep(8)  # wait for alert audio to finish

    # Step 2 — Tell them Léa is listening
    speak("Je vous écoute.", "listening.wav")
    os.system("start listening.wav")
    time.sleep(4)  # wait for "je vous écoute" to finish

    # Step 3 — Record their response
    print(" Recording your response now — say 'aide' or 'ça va'...")
    print("⏳ You have 7 seconds starting NOW...")
    response_path = record_response(duration=7)
    print(" Recording done, transcribing...")

    # Step 4 — Transcribe
    response_text = ""
    try:
        response_text = transcribe_response(response_path)
        print(f" Person said: '{response_text}'")
    except Exception as e:
        print(f" Could not transcribe: {e}")

    # Step 5 — Analyze and react
    status = analyze_response(response_text)
    print(f" Status detected: {status}")

    if status == "no_response":
        print(" No response detected!")
        speak(
            "Aucune réponse détectée. J'alerte vos proches immédiatement.",
            "no_response.wav"
        )
        os.system("start no_response.wav")
        publish_alert({
            "event_type": "fall_detected",
            "person_id": person_id,
            "responded": False,
            "response_text": None,
            "person_status": "no_response",
            "action_required": "emergency",
            "message_for_family": "La personne n'a pas répondu après la chute. Intervention urgente requise."
        })

    elif status == "needs_help":
        print(" Person needs help!")
        speak(
            "Je comprends. J'alerte vos proches et les secours immédiatement. Restez calme, de l'aide arrive.",
            "help_response.wav"
        )
        os.system("start help_response.wav")
        publish_alert({
            "event_type": "fall_detected",
            "person_id": person_id,
            "responded": True,
            "response_text": response_text,
            "person_status": "needs_help",
            "action_required": "emergency",
            "message_for_family": f"La personne a chuté et a besoin d'aide. Elle a dit: '{response_text}'"
        })

    elif status == "okay":
        print(" Person says they are okay!")
        speak(
            "Je suis soulagée que vous alliez bien. Vos proches seront quand même informés de votre chute.",
            "okay_response.wav"
        )
        os.system("start okay_response.wav")
        publish_alert({
            "event_type": "fall_detected",
            "person_id": person_id,
            "responded": True,
            "response_text": response_text,
            "person_status": "okay",
            "action_required": "notify_only",
            "message_for_family": f"La personne a chuté mais dit aller bien. Elle a dit: '{response_text}'. Vérification recommandée."
        })

    else:  # unclear
        print(f" Unclear response: '{response_text}'")
        speak(
            "Je n'ai pas bien compris. Vos proches vont être contactés pour vérifier que vous allez bien.",
            "unclear_response.wav"
        )
        os.system("start unclear_response.wav")
        publish_alert({
            "event_type": "fall_detected",
            "person_id": person_id,
            "responded": True,
            "response_text": response_text,
            "person_status": "unclear",
            "action_required": "verify",
            "message_for_family": f"La personne a chuté. Réponse unclear: '{response_text}'. Vérification recommandée."
        })

def start_redis_listener():
    while True:
        try:
            r = redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_timeout=30,
                socket_connect_timeout=10
            )
            r.ping()
            pubsub = r.pubsub()
            pubsub.subscribe(CHANNEL_FALL)
            print(f" Redis listener active on channel: {CHANNEL_FALL}")

            for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        handle_fall_event(data)
                    except json.JSONDecodeError:
                        print(f" Could not parse message: {message['data']}")

        except Exception as e:
            print(f" Redis connection lost: {e} — retrying in 5 seconds...")
            time.sleep(5)
            continue