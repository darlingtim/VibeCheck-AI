import os
import json
import logging
import re
import traceback
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Any
from urllib.request import Request, urlopen

def _load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE entries without requiring an external package."""
    if not path.is_file():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_env_file(Path(__file__).resolve().parents[1] / ".env")

LOG_FILE = Path(__file__).resolve().parents[1] / "logs" / "llm_service.log"
ERROR_LOG_DIR = LOG_FILE.parent / "errors"


def _get_logger() -> logging.Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not any(
        isinstance(handler, RotatingFileHandler)
        and Path(handler.baseFilename).resolve() == LOG_FILE.resolve()
        for handler in logger.handlers
    ):
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(handler)

    return logger


logger = _get_logger()


def _write_error_log(review_id: Any, error: Exception) -> None:
    """Write one diagnostic file for an individual failed API attempt."""
    timestamp = datetime.now(timezone.utc)
    safe_review_id = re.sub(r"[^A-Za-z0-9_.-]", "_", str(review_id))
    error_file = ERROR_LOG_DIR / (
        f"llm_error_{timestamp.strftime('%Y%m%dT%H%M%S_%fZ')}_{safe_review_id}.log"
    )
    ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)
    error_file.write_text(
        "\n".join(
            [
                f"timestamp_utc={timestamp.isoformat()}",
                f"review_id={review_id}",
                f"error_type={type(error).__name__}",
                f"error={error}",
                "",
                "traceback:",
                traceback.format_exc(),
            ]
        ),
        encoding="utf-8",
    )


class LLMReviewProcessor:
    def __init__(self, api_key: str = None, provider: str = None):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "openai")).lower()
        if self.provider not in {"openai", "gemini"}:
            raise ValueError("LLM_PROVIDER must be either 'openai' or 'gemini'")

        key_name = "GEMINI_API_KEY" if self.provider == "gemini" else "OPENAI_API_KEY"
        self.api_key = api_key or os.getenv(key_name)
        self.model = os.getenv(
            "GEMINI_MODEL" if self.provider == "gemini" else "OPENAI_MODEL",
            "gemini-2.0-flash" if self.provider == "gemini" else "gpt-4o-mini",
        )
        self.endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
            if self.provider == "gemini"
            else "https://api.openai.com/v1/chat/completions"
        )

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
            result = {
                "review_id": review["review_id"],
                "sentiment": "Negative" if is_bathroom else "Positive",
                "primary_theme": "Bathrooms" if is_bathroom else "Sound",
                "urgency": 4 if is_bathroom else 1
            }
            logger.info(
                "review_id=%s outcome=success mode=local_fallback",
                review["review_id"],
            )
            return result

        providers = [(self.provider, self.api_key, self.model, self.endpoint)]
        if self.provider == "openai":
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key:
                gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
                providers.append(
                    (
                        "gemini",
                        gemini_key,
                        gemini_model,
                        f"https://generativelanguage.googleapis.com/v1beta/models/"
                        f"{gemini_model}:generateContent",
                    )
                )

        errors = []
        for provider, api_key, model, endpoint in providers:
            if not api_key:
                errors.append(f"{provider}: API key is not configured")
                continue

            try:
                headers = {"Content-Type": "application/json"}
                if provider == "gemini":
                    headers["x-goog-api-key"] = api_key
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "responseMimeType": "application/json"
                        },
                    }
                else:
                    headers["Authorization"] = f"Bearer {api_key}"
                    payload = {
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"},
                    }

                request = Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST",
                )
                with urlopen(request, timeout=10) as response:
                    result = json.loads(response.read().decode("utf-8"))
                if provider == "gemini":
                    raw_content = result["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    raw_content = result["choices"][0]["message"]["content"]
                content = json.loads(raw_content)
                logger.info(
                    "review_id=%s outcome=success provider=%s model=%s",
                    review["review_id"],
                    provider,
                    model,
                )
                return {"review_id": review["review_id"], **content}
            except Exception as e:
                errors.append(f"{provider}: {e}")
                logger.error(
                    "review_id=%s outcome=failure provider=%s error_type=%s error=%s",
                    review["review_id"],
                    provider,
                    type(e).__name__,
                    e,
                )
                try:
                    _write_error_log(review["review_id"], e)
                except OSError:
                    logger.exception(
                        "review_id=%s outcome=failure error_log_write_failed provider=%s",
                        review["review_id"],
                        provider,
                    )

        return {
            "review_id": review["review_id"],
            "error": "All configured LLM providers failed: " + "; ".join(errors),
        }
