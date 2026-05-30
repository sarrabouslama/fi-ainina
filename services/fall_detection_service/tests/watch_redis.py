#!/usr/bin/env python3
"""
watch_redis.py — Monitor fall_events Redis channel.

Run this in a separate terminal to see all fall detection events.
"""
import redis
import json
import sys
import os

# Make local package imports work when running this script from tests/
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(ROOT))

from app.config import settings

def main():
    print("[REDIS] Connecting to Redis...")
    print(f"[REDIS] URL: {settings.redis_url}")
    print(f"[REDIS] Channel: {settings.redis_channel_fall}\n")
    
    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        print("✅ Connected to Redis\n")
    except Exception as e:
        print(f"❌ Failed to connect: {e}\n")
        sys.exit(1)
    
    pubsub = client.pubsub()
    pubsub.subscribe(settings.redis_channel_fall)
    
    print(f"🔍 Listening on '{settings.redis_channel_fall}'...")
    print("=" * 70)
    
    try:
        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    event = json.loads(message["data"])
                    
                    print(f"\n📬 Event: {event['event_type'].upper()}")
                    print(f"   User ID:    {event['user_id']}")
                    print(f"   Severity:   {event['severity']}")
                    print(f"   Confidence: {event['confidence']}")
                    print(f"   Timestamp:  {event['timestamp']}")
                    
                    metadata = event.get("metadata", {})
                    if metadata:
                        print(f"   Metadata:")
                        for key, value in metadata.items():
                            if isinstance(value, dict):
                                print(f"     {key}:")
                                for k, v in value.items():
                                    print(f"       {k}: {v}")
                            else:
                                print(f"     {key}: {value}")
                    
                    print("=" * 70)
                    
                except json.JSONDecodeError:
                    print(f"\n⚠️  Invalid JSON: {message['data']}")
    
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped listening.")
        sys.exit(0)

if __name__ == "__main__":
    main()
