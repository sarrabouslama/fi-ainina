import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_llm():
    with patch("app.main.generate_chat_response", new_callable=AsyncMock) as mock:
        mock.return_value = "Hello! I am here for you."
        yield mock

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"service": "llm_service", "status": "ok"}

def test_chat_endpoint_success(mock_llm):
    payload = {
        "user_id": "user123",
        "message": "I feel a bit down today.",
        "emotion": "sad"
    }
    
    response = client.post("/chat", json=payload)
    
    assert response.status_code == 200
    assert response.json() == {
        "response": "Hello! I am here for you.",
        "emotion": "sad",
    }
    
    # Verify the mock was called with correct arguments
    mock_llm.assert_called_once_with(
        user_id="user123",
        message="I feel a bit down today.",
        emotion="sad"
    )

def test_chat_endpoint_validation_error():
    # Missing required 'message' field
    payload = {
        "user_id": "user123",
        "emotion": "happy"
    }
    
    response = client.post("/chat", json=payload)
    assert response.status_code == 422 # Unprocessable Entity


def test_chat_endpoint_uses_emotion_service_when_emotion_omitted(mock_llm):
    with patch("app.main.get_detected_emotion", new_callable=AsyncMock) as mock_emotion:
        mock_emotion.return_value = "happy"
        payload = {
            "user_id": "user123",
            "message": "Hello there.",
        }

        response = client.post("/chat", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "response": "Hello! I am here for you.",
        "emotion": "happy",
    }
    mock_llm.assert_called_once_with(
        user_id="user123",
        message="Hello there.",
        emotion="happy"
    )


def test_chat_endpoint_can_request_voice_synthesis(mock_llm):
    with patch("app.main.synthesize_speech", new_callable=AsyncMock) as mock_speech:
        mock_speech.return_value = (b"fake wav", "audio/wav")
        payload = {
            "user_id": "user123",
            "message": "Say this out loud.",
            "emotion": "neutral",
            "synthesize_voice": True,
        }

        response = client.post("/chat", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "response": "Hello! I am here for you.",
        "emotion": "neutral",
        "audio_base64": "ZmFrZSB3YXY=",
        "audio_content_type": "audio/wav",
    }
    mock_speech.assert_awaited_once_with("Hello! I am here for you.")
