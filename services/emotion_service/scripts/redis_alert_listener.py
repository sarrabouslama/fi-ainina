"""Listen for emotion and inactivity alerts on Redis pub/sub channels."""

from __future__ import annotations

import json
import os

import redis
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))

    client = redis.Redis(host=host, port=port, decode_responses=True)
    try:
        client.ping()
    except redis.exceptions.ConnectionError as exc:
        raise SystemExit(f"Redis is not reachable at {host}:{port}: {exc}")

    pubsub = client.pubsub()
    pubsub.subscribe("emotion_events", "inactivity_events")

    print(f"Listening on Redis {host}:{port} for emotion_events and inactivity_events...")

    for message in pubsub.listen():
        if message.get("type") != "message":
            continue
        channel = message.get("channel")
        data = message.get("data")
        print(f"[{channel}] {json.loads(data)}")


if __name__ == "__main__":
    main()