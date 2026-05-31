from app.microservices.base import AsyncServiceClient


class LLMClient(AsyncServiceClient):
    async def chat(self, user_id: str, text: str, emotion_context: dict | None, history: list[dict]):
        resp = await self._request(
            'POST',
            '/chat',
            json={
                'user_id': user_id,
                'text': text,
                'emotion_context': emotion_context,
                'history': history,
            },
        )
        return resp.json()
