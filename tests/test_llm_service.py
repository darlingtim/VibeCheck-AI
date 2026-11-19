import json
import os
from unittest.mock import patch

from services.llm_service import LLMReviewProcessor


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.body).encode("utf-8")


def test_gemini_request_and_response():
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "sentiment": "Positive",
                                    "primary_theme": "Sound",
                                    "urgency": 1,
                                }
                            )
                        }
                    ]
                }
            }
        ]
    }

    def fake_urlopen(request, timeout):
        body = json.loads(request.data.decode("utf-8"))
        assert request.get_header("X-goog-api-key") == "gemini-test-key"
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        assert timeout == 10
        return FakeResponse(response)

    with patch("services.llm_service.urlopen", fake_urlopen):
        result = LLMReviewProcessor(
            api_key="gemini-test-key", provider="gemini"
        ).analyze_review({"review_id": "REV-GEMINI", "text": "Great sound"})

    assert result["sentiment"] == "Positive"
    assert result["primary_theme"] == "Sound"


def test_openai_request_uses_bearer_authentication():
    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "sentiment": "Neutral",
                            "primary_theme": "General",
                            "urgency": 2,
                        }
                    )
                }
            }
        ]
    }

    def fake_urlopen(request, timeout):
        assert request.get_header("Authorization") == "Bearer openai-test-key"
        return FakeResponse(response)

    with patch("services.llm_service.urlopen", fake_urlopen):
        result = LLMReviewProcessor(
            api_key="openai-test-key", provider="openai"
        ).analyze_review({"review_id": "REV-OPENAI", "text": "An average event"})

    assert result["sentiment"] == "Neutral"
    assert result["primary_theme"] == "General"


def test_openai_failure_falls_back_to_gemini():
    gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "sentiment": "Negative",
                                    "primary_theme": "Bathrooms",
                                    "urgency": 4,
                                }
                            )
                        }
                    ]
                }
            }
        ]
    }

    def fake_urlopen(request, timeout):
        if "api.openai.com" in request.full_url:
            raise RuntimeError("OpenAI unavailable")
        assert "generativelanguage.googleapis.com" in request.full_url
        assert request.get_header("X-goog-api-key") == "gemini-fallback-key"
        return FakeResponse(gemini_response)

    with patch.dict(os.environ, {"GEMINI_API_KEY": "gemini-fallback-key"}):
        with patch("services.llm_service.urlopen", fake_urlopen):
            result = LLMReviewProcessor(
                api_key="openai-test-key", provider="openai"
            ).analyze_review(
                {"review_id": "REV-FAILOVER", "text": "Long bathroom queue"}
            )

    assert result["sentiment"] == "Negative"
    assert result["primary_theme"] == "Bathrooms"
