"""Test script to process an image and verify Redis alert publication."""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

import cv2
import redis
from dotenv import load_dotenv

# Import emotion service logic
from app.capture import _largest_face_bbox, _crop_face
from app.emotion import analyze_emotion
from app.redness import analyze_redness
from app.publisher import RedisEventPublisher

def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="Path to the image file")
    parser.add_argument("--channel", default="emotion_events", help="Redis channel to listen on")
    parser.add_argument("--timeout", type=float, default=10.0, help="Seconds to wait for Redis message")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: Image not found at {image_path}")
        return 1

    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    
    try:
        client = redis.Redis(host=host, port=port, decode_responses=True, protocol=2)
        client.ping()
    except Exception as e:
        print(f"Error: Redis connection failed at {host}:{port} - {e}")
        return 1

    received_event = threading.Event()
    received_payloads = []

    def listen():
        pubsub = client.pubsub()
        pubsub.subscribe(args.channel)
        print(f"Listening on channel: {args.channel}...")
        for message in pubsub.listen():
            if message.get("type") == "message":
                data = json.loads(message.get("data"))
                received_payloads.append(data)
                print(f"\n[REDIS] Received event: {data.get('event_type')}")
                # We don't break immediately so we can capture multiple events if they happen quickly
                received_event.set()

    listener_thread = threading.Thread(target=listen, daemon=True)
    listener_thread.start()
    time.sleep(1) # Give it a second to subscribe

    print(f"Processing image: {image_path}")
    frame = cv2.imread(str(image_path))
    if frame is None:
        print(f"Error: Could not read image at {image_path}")
        return 1

    bbox = _largest_face_bbox(frame)
    face_region = _crop_face(frame, bbox) if bbox is not None else None
    
    emotion_result = analyze_emotion(face_region)
    redness_result = analyze_redness(face_region)

    print(f"Analysis Results:")
    print(f" - Emotion: {emotion_result.emotion} (Conf: {emotion_result.confidence:.2f}, Severity: {emotion_result.severity})")
    print(f" - Redness: {redness_result.redness_level} (Score: {redness_result.redness_score:.3f}, Reliable: {redness_result.redness_reliable})")

    publisher = RedisEventPublisher()
    
    # Check for distress emotion
    distress_met = emotion_result.severity is not None and emotion_result.emotion not in {"happy", "neutral"}
    # Check for extreme redness
    redness_met = redness_result.redness_score > 0.8

    if distress_met:
        print("Publishing distress event to Redis...")
        publisher.publish_distress_event(
            severity=emotion_result.severity,
            confidence=emotion_result.confidence,
            emotion=emotion_result.emotion,
            score=emotion_result.confidence,
            redness_score=redness_result.redness_score,
            redness_level=redness_result.redness_level,
            redness_reliable=redness_result.redness_reliable,
        )

    if redness_met:
        print(f"!!! EXTREME REDNESS ({redness_result.redness_score:.3f}) DETECTED !!!")
        print("Publishing extreme redness alert to Redis...")
        publisher.publish_redness_alert(
            redness_score=redness_result.redness_score,
            level=redness_result.redness_level
        )
    
    # FOR TESTING: Force publish if neither condition met
    if not distress_met and not redness_met:
        print("Conditions NOT met by analysis. FORCING distress alert for testing...")
        publisher.publish_distress_event(
            severity="high",
            confidence=0.99,
            emotion="distress_test",
            score=0.99,
            redness_score=redness_result.redness_score,
            redness_level=redness_result.redness_level,
            redness_reliable=redness_result.redness_reliable,
        )
    
    if received_event.wait(args.timeout):
        print("\n" + "="*50)
        print(f"SUCCESS: {len(received_payloads)} alert(s) received from Redis!")
        for i, payload in enumerate(received_payloads, 1):
            etype = payload.get("event_type")
            print(f"\nAlert #{i}: {etype}")
            print(f"Details: {json.dumps(payload, indent=2)}")
        print("="*50)
        return 0
    else:
        print("\nFAILURE: No alerts received in Redis within timeout.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
