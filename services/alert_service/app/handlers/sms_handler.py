"""
Twilio Handler : send alert notifications via SMS or WhatsApp.
"""

import logging
from typing import List
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient

from app.models import AlertEvent
from app import config

logger = logging.getLogger(__name__)


class SMSHandler:
    """Send alert messages via Twilio SMS or WhatsApp."""

    def __init__(self):
        self.twilio_sid = config.TWILIO_SID
        self.twilio_token = config.TWILIO_TOKEN
        self.channel = config.TWILIO_CHANNEL
        self.twilio_from = (
            config.TWILIO_WHATSAPP_FROM
            if self.channel == "whatsapp"
            else config.TWILIO_FROM
        )
        self.enabled = config.ENABLE_SMS
        
        if self.enabled and self.twilio_sid and self.twilio_token:
            http_client = self._build_http_client()
            self.client = Client(self.twilio_sid, self.twilio_token, http_client=http_client)
        else:
            self.client = None

    @property
    def channel_name(self) -> str:
        return "whatsapp" if self.channel == "whatsapp" else "sms"

    def _mask_recipient(self, recipient: str) -> str:
        if len(recipient) <= 6:
            return "***"
        return f"{recipient[:4]}...{recipient[-2:]}"

    def _build_http_client(self):
        """Build a Twilio HTTP client only when TLS settings need customization."""
        if config.TWILIO_SSL_VERIFY and not config.TWILIO_CA_BUNDLE:
            return None

        http_client = TwilioHttpClient()
        if config.TWILIO_CA_BUNDLE:
            http_client.session.verify = config.TWILIO_CA_BUNDLE
        else:
            logger.warning("Twilio SSL verification is disabled. Use only for local testing.")
            http_client.session.verify = False

        return http_client

    async def send_alert(self, event: AlertEvent, recipients: List[str]) -> bool:
        """
        Send alert message to recipients.
        
        Args:
            event: The alert event
            recipients: List of phone numbers.
                SMS format: +33612345678
                WhatsApp format: +33612345678 or whatsapp:+33612345678
            
        Returns:
            True if all messages sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info("Twilio sending disabled, skipping")
            return True

        if not self.client:
            logger.error("Twilio client not initialized (missing credentials)")
            return False

        if not recipients:
            logger.warning(f"No {self.channel_name} recipients for alert {event.event_type}")
            return False

        # Format message
        message_text = self._compose_sms(event)
        success_count = 0

        for recipient in recipients:
            formatted_recipient = self._format_recipient(recipient)
            try:
                msg = self.client.messages.create(
                    body=message_text,
                    from_=self.twilio_from,
                    to=formatted_recipient
                )
                logger.info(
                    f"{self.channel_name.upper()} sent to {self._mask_recipient(formatted_recipient)} "
                    f"(SID: {msg.sid})"
                )
                success_count += 1
            except TwilioRestException as e:
                logger.error(
                    f"Failed to send {self.channel_name} to {self._mask_recipient(formatted_recipient)}: "
                    f"Twilio HTTP {e.status} - {e.msg}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to send {self.channel_name} to {self._mask_recipient(formatted_recipient)}: {e}"
                )
                logger.debug("Twilio send failure details", exc_info=True)

        if success_count == len(recipients):
            logger.info(f"All {success_count} {self.channel_name} messages sent successfully for {event.event_type}")
            return True
        else:
            logger.warning(
                f"Partial {self.channel_name} failure: {success_count}/{len(recipients)} sent for {event.event_type}"
            )
            return success_count > 0

    def _format_recipient(self, recipient: str) -> str:
        """Format recipient for the configured Twilio channel."""
        recipient = recipient.strip()
        if self.channel == "whatsapp" and not recipient.startswith("whatsapp:"):
            return f"whatsapp:{recipient}"
        return recipient

    def _compose_sms(self, event: AlertEvent) -> str:
        """Compose alert message. Kept short so it also works well as SMS."""
        emoji_map = {
            "fall_detected": "🚨",
            "fall_alert": "🚨",
            "emotion_distress": "😢",
            "extreme_redness_detected": "🚨",
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
