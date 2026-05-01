# Créer un script de test email

import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "eyazayeni53@gmail.com"
SMTP_PASS = "1742Eyazayeni"  # 16 caractères
TEST_EMAIL = "eyazayeni53@exemple.com"

msg = EmailMessage()
msg.set_content("Test ElderLink - Votre pipeline fonctionne !")
msg["Subject"] = "Test Pipeline P5"
msg["From"] = SMTP_USER
msg["To"] = TEST_EMAIL

with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
    server.starttls()
    server.login(SMTP_USER, SMTP_PASS)
    server.send_message(msg)
    print("✅ Email envoyé !")
