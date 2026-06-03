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
        severity_color = {
            "critical": "#b91c1c",
            "high":     "#dc2626",
            "medium":   "#d97706",
            "low":      "#16a34a",
        }.get(event.severity, "#6b7280")

        severity_bg = {
            "critical": "#fef2f2",
            "high":     "#fff5f5",
            "medium":   "#fffbeb",
            "low":      "#f0fdf4",
        }.get(event.severity, "#f9fafb")

        event_label, icon, action_text = {
            "fall_detected": (
                "Chute détectée",
                "🚨",
                "Rendez-vous auprès du résident immédiatement ou contactez les secours.",
            ),
            "emotion_distress": (
                "Détresse émotionnelle détectée",
                "⚠️",
                "Le résident présente des signes de détresse. Veuillez le contacter ou lui rendre visite.",
            ),
            "extreme_redness_detected": (
                "Rougeur faciale intense détectée",
                "🔴",
                "Une rougeur anormale a été détectée. Vérifiez l'état de santé du résident.",
            ),
            "inactivity_detected": (
                "Inactivité prolongée détectée",
                "⏱️",
                "Le résident n'a pas bougé depuis un moment. Vérifiez qu'il va bien.",
            ),
        }.get(event.event_type, (event.event_type, "📋", "Veuillez vérifier l'état du résident."))

        subject = f"{icon} ALERTE FiAinina — {event_label}"

        meta = event.metadata or {}
        resident_name = meta.get("full_name") or str(event.user_id)
        person_status = meta.get("person_status", "")
        response_text = meta.get("response_text", "")
        message_for_family = meta.get("message_for_family", "")
        confidence_str = f"{event.confidence * 100:.0f}%" if event.confidence is not None else "—"
        timestamp_str = event.timestamp.strftime("%d/%m/%Y à %H:%M:%S")

        status_block = ""
        if person_status:
            status_labels = {
                "needs_help":  ("🆘 Besoin d'aide", "#b91c1c"),
                "no_response": ("📵 Aucune réponse", "#7c3aed"),
                "okay":        ("✅ Dit aller bien", "#15803d"),
                "unclear":     ("❓ Réponse floue", "#b45309"),
            }
            label, color = status_labels.get(person_status, (person_status, "#6b7280"))
            status_block = f"""
            <tr>
              <td style="padding:10px 0;border-bottom:1px solid #e5e7eb;">
                <span style="font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em;">
                  Réponse du résident
                </span><br>
                <span style="font-size:15px;font-weight:700;color:{color};">{label}</span>
                {"<br><span style='font-size:13px;color:#374151;font-style:italic;'>«&nbsp;" + response_text + "&nbsp;»</span>" if response_text else ""}
              </td>
            </tr>"""

        family_block = ""
        if message_for_family:
            family_block = f"""
            <tr>
              <td style="padding:10px 0;border-bottom:1px solid #e5e7eb;">
                <span style="font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em;">
                  Message
                </span><br>
                <span style="font-size:14px;color:#1f2937;">{message_for_family}</span>
              </td>
            </tr>"""

        body = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:{severity_color};border-radius:12px 12px 0 0;padding:28px 32px;">
            <p style="margin:0 0 4px;font-size:13px;color:rgba(255,255,255,0.8);font-weight:600;letter-spacing:.08em;text-transform:uppercase;">
              Alerte FiAinina · Gravité {event.severity.upper()}
            </p>
            <h1 style="margin:0;font-size:26px;font-weight:800;color:#ffffff;line-height:1.2;">
              {icon}&nbsp; {event_label}
            </h1>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="background:#ffffff;padding:28px 32px;">

            <!-- Action banner -->
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
              <tr>
                <td style="background:{severity_bg};border-left:4px solid {severity_color};border-radius:4px;padding:14px 18px;">
                  <p style="margin:0;font-size:15px;font-weight:700;color:{severity_color};">
                    ACTION REQUISE
                  </p>
                  <p style="margin:6px 0 0;font-size:14px;color:#374151;line-height:1.5;">
                    {action_text}
                  </p>
                </td>
              </tr>
            </table>

            <!-- Details table -->
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding:10px 0;border-bottom:1px solid #e5e7eb;">
                  <span style="font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em;">
                    Résident
                  </span><br>
                  <span style="font-size:16px;font-weight:700;color:#111827;">{resident_name}</span>
                </td>
              </tr>
              <tr>
                <td style="padding:10px 0;border-bottom:1px solid #e5e7eb;">
                  <span style="font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em;">
                    Date et heure
                  </span><br>
                  <span style="font-size:14px;color:#1f2937;font-weight:600;">{timestamp_str}</span>
                </td>
              </tr>
              {status_block}
              {family_block}
              <tr>
                <td style="padding:10px 0;">
                  <span style="font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em;">
                    Confiance du système
                  </span><br>
                  <span style="font-size:14px;color:#1f2937;">{confidence_str}</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f9fafb;border-radius:0 0 12px 12px;padding:18px 32px;border-top:1px solid #e5e7eb;">
            <p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.6;">
              Ce message a été généré automatiquement par <strong style="color:#6b7280;">FiAinina</strong> —
              Système de surveillance intelligente pour personnes âgées.<br>
              Ne pas répondre à cet email.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
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
