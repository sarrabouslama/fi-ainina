import redis
import threading
import json
import os
import time
import httpx
import speech_recognition as sr
from app.tts import speak

REDIS_URL = "redis://localhost:6379/0"
CHANNEL_FALL = "fall_events"
CHANNEL_ALERT = "fall_alerts"
COMPANION_URL = "http://127.0.0.1:8000"

_recognizer = sr.Recognizer()
_recognizer.energy_threshold = 300
_recognizer.dynamic_energy_threshold = True


def publish_alert(event: dict):
    """Send alert directly to companion backend via HTTP."""
    try:
        response = httpx.post(
            f"{COMPANION_URL}/alerts/fall",
            json=event,
            timeout=15.0,
        )
        print(f" Alert sent to companion backend: {response.status_code}")
    except Exception as e:
        print(f" Could not send alert to companion backend: {e}")
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=5)
            r.publish(CHANNEL_ALERT, json.dumps(event))
            print(f" Alert published to Redis fallback")
        except Exception as e2:
            print(f" Redis fallback also failed: {e2}")


def listen_for_response(timeout: int = 7) -> str:
    """Listen for the person's response using Google Speech — same engine as wake word, no mic conflict."""
    print(f" Recording your response now — say 'aide' or 'ça va'...")
    print(f"⏳ You have {timeout} seconds starting NOW...")
    try:
        with sr.Microphone() as source:
            _recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = _recognizer.listen(source, timeout=timeout, phrase_time_limit=timeout)
        text = _recognizer.recognize_google(audio, language="fr-FR")
        print(f" Person said: '{text}'")
        return text
    except sr.WaitTimeoutError:
        print(" (no response — timeout)")
        return ""
    except sr.UnknownValueError:
        print(" (incompris)")
        return ""
    except sr.RequestError as e:
        print(f" Google Speech API error: {e}")
        return ""
    except Exception as e:
        print(f" Response listen error: {e}")
        return ""


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
        "aide", "aidez", "mal", "blessé", "blessée", "oui", "secours",
        "ambulance", "docteur", "douleur", "souffre", "tombé", "chute",
        "appelle", "appelez", "vite", "urgent",
        "help", "hurt", "pain", "yes", "doctor", "emergency", "fallen",
        "call", "please", "need"
    ])

    is_okay = any(word in text_lower for word in [
        "bien", "ça va", "non", "pas besoin", "okay", "pas mal",
        "parfait", "tranquille", "debout", "relevé",
        "fine", "ok", "good", "no", "alright"
    ])

    if needs_help:
        return "needs_help"
    elif is_okay:
        return "okay"
    else:
        return "unclear"


def handle_fall_event(data: dict):
    event_type = data.get("event_type", "unknown")
    person_id = data.get("user_id") or data.get("person_id") or "unknown"

    print(f" Fall event received! type={event_type} person={person_id}")

    speak("Attention! Une chute a été détectée. Êtes-vous blessé? Répondez s'il vous plaît.", "alert.wav")
    os.system("start alert.wav")
    time.sleep(8)

    speak("Je vous écoute.", "listening.wav")
    os.system("start listening.wav")
    time.sleep(4)

    response_text = listen_for_response(timeout=7)

    status = analyze_response(response_text)
    print(f" Status detected: {status}")

    if status == "no_response":
        speak("Aucune réponse détectée. J'alerte vos proches immédiatement.", "no_response.wav")
        os.system("start no_response.wav")
        publish_alert({
            "event_type": "fall_detected", "person_id": person_id,
            "responded": False, "response_text": None,
            "person_status": "no_response", "action_required": "emergency",
            "message_for_family": "La personne n'a pas répondu après la chute. Intervention urgente requise."
        })

    elif status == "needs_help":
        speak("Je comprends. J'alerte vos proches immédiatement. Restez calme, de l'aide arrive.", "help_response.wav")
        os.system("start help_response.wav")
        publish_alert({
            "event_type": "fall_detected", "person_id": person_id,
            "responded": True, "response_text": response_text,
            "person_status": "needs_help", "action_required": "emergency",
            "message_for_family": f"La personne a chuté et a besoin d'aide. Elle a dit: '{response_text}'"
        })

    elif status == "okay":
        speak("Je suis soulagée que vous alliez bien. Vos proches seront quand même informés.", "okay_response.wav")
        os.system("start okay_response.wav")
        publish_alert({
            "event_type": "fall_detected", "person_id": person_id,
            "responded": True, "response_text": response_text,
            "person_status": "okay", "action_required": "notify_only",
            "message_for_family": f"La personne a chuté mais dit aller bien. Elle a dit: '{response_text}'."
        })

    else:
        speak("Je n'ai pas bien compris. Vos proches vont être contactés pour vérifier.", "unclear_response.wav")
        os.system("start unclear_response.wav")
        publish_alert({
            "event_type": "fall_detected", "person_id": person_id,
            "responded": True, "response_text": response_text,
            "person_status": "unclear", "action_required": "verify",
            "message_for_family": f"La personne a chuté. Réponse: '{response_text}'. Vérification recommandée."
        })


def start_redis_listener():
    while True:
        try:
            r = redis.from_url(
                REDIS_URL, decode_responses=True,
                socket_timeout=30, socket_connect_timeout=10
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
