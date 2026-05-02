"""
Email Handler : send alert notifications via SMTP.

Uses aiosmtplib for async email sending.
"""

import logging
from typing import List
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.models import AlertEvent
from app import config

logger = logging.getLogger(__name__)


class EmailHandler:
    """Send alert emails via SMTP."""

    def __init__(self):
        self.smtp_host = config.SMTP_HOST
        self.smtp_port = config.SMTP_PORT
        self.smtp_user = config.SMTP_USER
        self.smtp_pass = config.SMTP_PASS
        self.from_name = config.SMTP_FROM_NAME
        self.from_email = config.SMTP_FROM_EMAIL
        self.smtp_tls = config.SMTP_TLS
        self.smtp_ssl = config.SMTP_SSL
        self.timeout = config.SMTP_TIMEOUT
        self.enabled = config.ENABLE_EMAIL

    async def send_alert(self, event: AlertEvent, recipients: List[str]) -> bool:
        """
        Send alert email to recipients.
        
        Args:
            event: The alert event
            recipients: List of email addresses
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.info("Email sending disabled, skipping")
            return True

        if not recipients:
            logger.warning(f"No email recipients for alert {event.event_type}")
            return False

        try:
            # Compose email
            subject, body = self._compose_email(event)
            message = self._create_mime_message(subject, body, recipients)

            async with aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=self.smtp_ssl,
                start_tls=self.smtp_tls,
                timeout=self.timeout,
            ) as smtp:
                await smtp.login(self.smtp_user, self.smtp_pass)
                await smtp.send_message(message)

            logger.info(f"Email sent to {len(recipients)} recipients for {event.event_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False

    def _compose_email(self, event: AlertEvent) -> tuple[str, str]:
        """Compose email subject and body."""
        subject = f"[ALERTE FIAININA] {event.event_type.upper()} - Personne: {event.user_id}"

        # Create HTML body
        severity_color = {
            "high": "#dc3545",  # red
            "medium": "#ffc107",  # yellow
            "low": "#28a745"  # green
        }.get(event.severity, "#6c757d")

        event_type_label = {
            "fall_detected": "🚨 Chute détectée",
            "emotion_distress": "😢 Détresse émotionnelle",
            "inactivity_detected": "⏱️ Inactivité prolongée"
        }.get(event.event_type, event.event_type)

        confidence = f"{event.confidence * 100:.1f}%" if event.confidence is not None else "N/A"

        body = f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: {severity_color}; color: white; padding: 20px; border-radius: 5px; }}
                    .content {{ padding: 20px; background-color: #f8f9fa; margin-top: 10px; border-radius: 5px; }}
                    .detail {{ margin: 10px 0; padding: 10px; background-color: white; border-left: 4px solid {severity_color}; }}
                    .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>{event_type_label}</h1>
                        <p>Alerte de gravité : <strong>{event.severity.upper()}</strong></p>
                    </div>
                    <div class="content">
                        <div class="detail">
                            <strong>Personne monitorée :</strong> {event.user_id}
                        </div>
                        <div class="detail">
                            <strong>Date/Heure :</strong> {event.timestamp.strftime('%d/%m/%Y à %H:%M:%S')}
                        </div>
                        <div class="detail">
                            <strong>Confiance :</strong> {confidence}
                        </div>
                        <div class="detail">
                            <strong>Détails :</strong>
                            <pre>{self._format_metadata(event.metadata)}</pre>
                        </div>
                    </div>
                    <div class="footer">
                        <p>FiAinina - Système de Surveillance Intelligente</p>
                        <p>Message automatique, ne pas répondre.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        return subject, body

    def _format_metadata(self, metadata: dict) -> str:
        """Format metadata for display."""
        import json
        return json.dumps(metadata, indent=2, ensure_ascii=False)

    def _create_mime_message(self, subject: str, body: str, recipients: List[str]) -> MIMEMultipart:
        """Create MIME message."""
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = ", ".join(recipients)

        # Add HTML body
        part = MIMEText(body, "html", "utf-8")
        message.attach(part)

        return message


# Global instance
email_handler = EmailHandler()
