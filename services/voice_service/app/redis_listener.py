import redis
import threading
import json
import os
import time
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import httpx
from app.tts import speak
from app.stt import transcribe

REDIS_URL = "redis://localhost:6379/0"
CHANNEL_FALL = "fall_events"
SAMPLE_RATE = 16000

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
    time.sleep(4)  # wait for alert audio to finish

    # Step 2 — Listen for their response
    print(" Listening for response from person...")
    speak("Je vous écoute.", "listening.wav")
    os.system("start listening.wav")
    time.sleep(2)

    response_path = record_response(duration=7)

    # Step 3 — Transcribe what they said
    try:
        response_text = transcribe(response_path)
        print(f" Person said: {response_text}")
    except Exception as e:
        print(f" Could not transcribe response: {e}")
        response_text = ""

    # Step 4 — React based on their response
    if not response_text.strip():
        # No response — escalate immediately
        handle_no_response()
    else:
        handle_person_response(response_text, person_id)

def handle_no_response():
    """No response received — escalate to emergency."""
    print(" No response — escalating to emergency!")
    speak(
        "Aucune réponse détectée. J'alerte les secours immédiatement.",
        "escalate.wav"
    )
    os.system("start escalate.wav")
    # Here you would publish to Redis to notify caregiver/emergency service
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.publish("emergency_alerts", json.dumps({
            "event_type": "no_response_after_fall",
            "action": "call_emergency"
        }))
    except Exception as e:
        print(f" Could not publish emergency alert: {e}")

def handle_person_response(response_text: str, person_id: str):
    """Handle what the person said after the fall alert."""
    text_lower = response_text.lower()

    # Check if they need help
    needs_help = any(word in text_lower for word in [
        "aide", "help", "mal", "blessé", "oui", "yes",
        "aidez", "secours", "ambulance", "docteur"
    ])

    # Check if they are okay
    is_okay = any(word in text_lower for word in [
        "bien", "ça va", "non", "pas besoin", "okay", "ok", "no"
    ])

    if needs_help:
        print(" Person needs help — alerting caregiver!")
        speak(
            "Je comprends. J'alerte votre famille et les secours immédiatement. Restez calme.",
            "help_response.wav"
        )
        os.system("start help_response.wav")
        # Publish to notify caregiver
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True)
            r.publish("emergency_alerts", json.dumps({
                "event_type": "fall_help_needed",
                "person_id": person_id,
                "person_said": response_text
            }))
        except Exception as e:
            print(f" Could not publish help alert: {e}")

    elif is_okay:
        print(" Person says they are okay")
        speak(
            "Je suis soulagée que vous alliez bien. Je reste à votre écoute si vous avez besoin de moi.",
            "okay_response.wav"
        )
        os.system("start okay_response.wav")

    else:
        # Unclear response — ask again via LLM
        print(f"Unclear response: {response_text} — sending to LLM")
        try:
            response = httpx.post(
                "http://localhost:8001/chat",
                json={"message": f"Après une chute détectée, la personne a dit: {response_text}. Comment répondre?"},
                timeout=10
            )
            llm_reply = response.json().get("response", "Pouvez-vous répéter s'il vous plaît?")
        except Exception:
            llm_reply = "Je n'ai pas bien compris. Avez-vous besoin d'aide?"

        speak(llm_reply, "unclear_response.wav")
        os.system("start unclear_response.wav")

def start_redis_listener():
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
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
        print(f" Redis not available: {e} — voice service running without Redis")