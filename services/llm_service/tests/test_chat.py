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
    assert response.json() == {"response": "Hello! I am here for you."}
    
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
