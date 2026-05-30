from app.microservices.base import AsyncServiceClient


class VoiceAssistantClient(AsyncServiceClient):
    async def transcribe(self, audio_bytes: bytes):
        resp = await self._request('POST', '/transcribe', content=audio_bytes)
        return resp.json()

    async def synthesize(self, text: str, voice_params: dict | None = None):
        resp = await self._request('POST', '/synthesize', json={'text': text, 'voice_params': voice_params or {}})
        return resp.content
