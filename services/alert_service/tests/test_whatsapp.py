from twilio.rest import Client

# =====================================================
# REMPLACEZ CES VALEURS PAR LES VÔTRES
# =====================================================
ACCOUNT_SID = "AC628693ae83e4bd5cdfa7187bc5f9778b"  # Votre Account SID
AUTH_TOKEN = "295f2362a3a0cd84b537531b21783f99"     # Votre Auth Token
#FROM_NUMBER = "+21696278425"    # Votre numéro Twilio (ex: +1234567890)
#TO_NUMBER = "+21699732724"   # Votre numéro personnel (au format E.164)
WHATSAPP_FROM = "whatsapp:+14155238886"  # Numéro Sandbox Twilio
WHATSAPP_TO = "whatsapp:+21696278425"   # Votre numéro WhatsApp
# =====================================================

def test_whatsapp():
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        message = client.messages.create(
            body="🚨 Test ElderLink - Votre service d'alertes fonctionne !",
            from_=WHATSAPP_FROM,
            to=WHATSAPP_TO
        )
        print(f"✅ Message WhatsApp envoyé ! SID: {message.sid}")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    test_whatsapp()