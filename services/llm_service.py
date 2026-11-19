import os
import json
import logging
from typing import Dict, Any
from urllib.request import Request, urlopen

class LLMReviewProcessor:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.endpoint = "https://api.openai.com/v1/chat/completions"

    def analyze_review(self, review: Dict[str, Any]) -> Dict[str, Any]:
        """Sends a single review to the LLM for semantic classification."""
        prompt = f"""
        Analyze the following festival review and return a strict JSON object with:
        - sentiment: "Positive", "Neutral", or "Negative"
        - primary_theme: "Sound", "Bathrooms", "Food/Water", "Crowd Control", or "General"
        - urgency: integer from 1 to 5 (5 being critical safety/facility failure)
        
        Review Text: "{review['text']}"
        """
        
        # Local fallback mock response if no API key is set
        if not self.api_key:
            is_bathroom = "bathroom" in review["text"].lower()
            return {
                "review_id": review["review_id"],
                "sentiment": "Negative" if is_bathroom else "Positive",
                "primary_theme": "Bathrooms" if is_bathroom else "Sound",
                "urgency": 4 if is_bathroom else 1
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }

        try:
            request = Request(
                self.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urlopen(request, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
            content = json.loads(result["choices"]["message"]["content"])
            return {"review_id": review["review_id"], **content}
        except Exception as e:
            logging.error(f"API Error on review {review['review_id']}: {e}")
            return {"review_id": review["review_id"], "error": str(e)}