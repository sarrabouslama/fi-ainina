"""Send one test email through the configured SMTP provider."""

import asyncio
import os
import sys
from datetime import datetime, UTC
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.handlers.email_handler import EmailHandler
from app.models import AlertEvent


async def main():
    recipient = os.getenv("TEST_EMAIL_TO", "eyaazayeni@gmail.com")
    handler = EmailHandler()

    event = AlertEvent(
        event_type="fall_detected",
        user_id="mailtrap_test_person",
        timestamp=datetime.now(UTC),
        severity="high",
        confidence=0.95,
        metadata={"source": "app/scripts/test_email.py"},
    )

    sent = await handler.send_alert(event, [recipient])
    if sent:
        print(f"Email sent to {recipient}. Check your Gmail inbox.")
    else:
        raise SystemExit("Email send failed. Check alert_service logs and SMTP settings.")


if __name__ == "__main__":
    asyncio.run(main())
