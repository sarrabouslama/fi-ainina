"""
SMS Handler : send alert notifications via Twilio.

Uses Twilio SDK for SMS sending.
"""

import logging
from typing import List
from twilio.rest import Client

from app.models import AlertEvent
from app import config

logger = logging.getLogger(__name__)


class SMSHandler:
    """Send alert SMS via Twilio."""

    def __init__(self):
        self.twilio_sid = config.TWILIO_SID
        self.twilio_token = config.TWILIO_TOKEN
        self.twilio_from = config.TWILIO_FROM
        self.enabled = config.ENABLE_SMS
        
        if self.enabled and self.twilio_sid and self.twilio_token:
            self.client = Client(self.twilio_sid, self.twilio_token)
        else:
            self.client = None

    async def send_alert(self, event: AlertEvent, recipients: List[str]) -> bool:
        """
        Send alert SMS to recipients.
        
        Args:
            event: The alert event
            recipients: List of phone numbers (E.164 format, e.g., +33612345678)
            
        Returns:
            True if all SMS sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info("SMS sending disabled, skipping")
            return True

        if not self.client:
            logger.error("Twilio client not initialized (missing credentials)")
            return False

        if not recipients:
            logger.warning(f"No SMS recipients for alert {event.event_type}")
            return False

        # Format message
        message_text = self._compose_sms(event)
        success_count = 0

        for recipient in recipients:
            try:
                msg = self.client.messages.create(
                    body=message_text,
                    from_=self.twilio_from,
                    to=recipient
                )
                logger.info(f"SMS sent to {recipient} (SID: {msg.sid})")
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send SMS to {recipient}: {e}", exc_info=True)

        if success_count == len(recipients):
            logger.info(f"All {success_count} SMS sent successfully for {event.event_type}")
            return True
        else:
            logger.warning(
                f"Partial SMS failure: {success_count}/{len(recipients)} sent for {event.event_type}"
            )
            return success_count > 0

    def _compose_sms(self, event: AlertEvent) -> str:
        """Compose SMS message (keep short for SMS constraints)."""
        emoji_map = {
            "fall_detected": "🚨",
            "emotion_distress": "😢",
            "inactivity_detected": "⏱️"
        }
        emoji = emoji_map.get(event.event_type, "⚠️")

        # Keep under 160 chars for single SMS (no split charges)
        message = (
            f"{emoji} Alerte {event.severity.upper()}: {event.event_type} "
            f"- {event.user_id} à {event.timestamp.strftime('%H:%M')}"
        )
        
        # Truncate if too long
        if len(message) > 160:
            message = message[:157] + "..."

        return message


# Global instance
sms_handler = SMSHandler()
