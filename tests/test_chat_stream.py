from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch
from openai import APITimeoutError

client = TestClient(app)

# def test_llm_timeout_triggers_error():
#     with patch("api.chat_router.llm_stream_chat") as mock_llm:
#         mock_llm.side_effect 
