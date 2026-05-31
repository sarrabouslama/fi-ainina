import base64
import json
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings


def _key_bytes() -> bytes:
    return base64.urlsafe_b64decode(settings.aes256_key_b64)


def encrypt_json(data: dict | list | None):
    if data is None:
        return None
    nonce = os.urandom(12)
    aes = AESGCM(_key_bytes())
    plaintext = json.dumps(data, separators=(',', ':')).encode('utf-8')
    ciphertext = aes.encrypt(nonce, plaintext, None)
    return {'_enc': base64.b64encode(nonce + ciphertext).decode('utf-8')}


def decrypt_json(data):
    if data is None or '_enc' not in data:
        return data
    raw = base64.b64decode(data['_enc'])
    nonce, ciphertext = raw[:12], raw[12:]
    aes = AESGCM(_key_bytes())
    plaintext = aes.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode('utf-8'))
