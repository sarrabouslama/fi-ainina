"""Send one test WhatsApp alert through the configured Twilio channel."""

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import config
from app.handlers.sms_handler import SMSHandler
from app.models import AlertEvent


async def main():
    recipients = config.ALERT_TEST_WHATSAPP_RECIPIENTS
    override_recipient = os.getenv("TEST_WHATSAPP_TO")
    if override_recipient:
        recipients = [override_recipient]

    if not recipients:
        raise SystemExit("Set ALERT_TEST_WHATSAPP_RECIPIENTS or TEST_WHATSAPP_TO first.")

    if not config.TWILIO_WHATSAPP_FROM.startswith("whatsapp:"):
        raise SystemExit("Set TWILIO_WHATSAPP_FROM to a value like whatsapp:+14155238886.")

    handler = SMSHandler()
    handler.channel = "whatsapp"
    handler.twilio_from = config.TWILIO_WHATSAPP_FROM

    event = AlertEvent(
        event_type="fall_detected",
        user_id="whatsapp_test_person",
        timestamp=datetime.now(UTC),
        severity="high",
        confidence=0.95,
        metadata={"source": "app/scripts/test_whatsapp.py"},
    )

    sent = await handler.send_alert(event, recipients)
    if sent:
        print("WhatsApp alert sent. Check your phone.")
    else:
        raise SystemExit(
            "WhatsApp send failed. Check Twilio credentials, sandbox join status, recipient, and logs."
        )


if __name__ == "__main__":
    asyncio.run(main())
