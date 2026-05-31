import redis
import threading
import json
import os
from app.tts import speak

REDIS_URL = "redis://localhost:6379/0"
CHANNEL_FALL = "fall_events"

def handle_fall_event(data: dict):
    event_type = data.get("event_type", "unknown")
    person_id = data.get("person_id", "unknown")
    
    print(f" Fall event received! type={event_type} person={person_id}")
    
    # Speak urgent alert to the elderly person
    speak(
        "Attention! Une chute a été détectée. Avez-vous besoin d'aide? Répondez s'il vous plaît.",
        "alert.wav"
    )
    os.system("start alert.wav")

def start_redis_listener():
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
        pubsub = r.pubsub()
        pubsub.subscribe(CHANNEL_FALL)
        print(f"Redis listener active on channel: {CHANNEL_FALL}")

        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    handle_fall_event(data)
                except json.JSONDecodeError:
                    print(f" Could not parse message: {message['data']}")

    except Exception as e:
        print(f" Redis not available: {e} — voice service running without Redis")