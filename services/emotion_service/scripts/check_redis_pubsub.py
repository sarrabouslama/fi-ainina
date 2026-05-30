"""Verify Redis pub/sub with a publish/subscribe round trip."""

from __future__ import annotations

import argparse
import json
import os
import threading
import time

import redis
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", default="emotion_events", help="Redis channel to test")
    parser.add_argument("--timeout", type=float, default=5.0, help="Seconds to wait for the message")
    args = parser.parse_args()

    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    client = redis.Redis(host=host, port=port, decode_responses=True)

    try:
        client.ping()
    except redis.exceptions.ConnectionError as exc:
        print(f"Redis is not reachable at {host}:{port}: {exc}")
        return 1

    received = threading.Event()
    payload_holder: dict[str, str] = {}

    def listen() -> None:
        pubsub = client.pubsub()
        pubsub.subscribe(args.channel)
        for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            payload_holder["data"] = message.get("data", "")
            received.set()
            break

    thread = threading.Thread(target=listen, daemon=True)
    thread.start()
    time.sleep(0.5)

    message = json.dumps({"test": True, "timestamp": time.time()}, ensure_ascii=False)
    try:
        client.publish(args.channel, message)
    except redis.exceptions.ConnectionError as exc:
        print(f"Redis publish failed at {host}:{port}: {exc}")
        return 1

    if not received.wait(args.timeout):
        print(f"Redis pub/sub test failed on {host}:{port} channel={args.channel}")
        return 1

    print(f"Redis pub/sub test passed on {host}:{port} channel={args.channel}")
    print(payload_holder["data"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())