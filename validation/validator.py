import logging
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class ReviewIngestionPipeline:
    def __init__(self, min_length: int = 10, max_length: int = 1000):
        self.min_length = min_length
        self.max_length = max_length

    def sanitize_text(self, raw_text: str) -> str:
        """Sanitizes raw review text by stripping whitespace and neutralizing control characters."""
        if not isinstance(raw_text, str):
            return ""
        return " ".join(raw_text.split())

    def validate_review(self, review: Dict[str, Any]) -> bool:
        """Validates review schema and length constraints."""
        if not review.get("review_id") or not review.get("text"):
            return False
        
        text_length = len(review["text"])
        if text_length < self.min_length or text_length > self.max_length:
            logging.warning(f"Review {review.get('review_id')} rejected due to length constraints.")
            return False
            
        return True

    def process_batch(self, raw_reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processes a batch of raw reviews through sanitization and validation."""
        valid_reviews = []
        for item in raw_reviews:
            sanitized_text = self.sanitize_text(item.get("text", ""))
            processed_item = {
                "review_id": item.get("review_id"),
                "text": sanitized_text,
                "timestamp": item.get("timestamp", "unknown")
            }
            if self.validate_review(processed_item):
                valid_reviews.append(processed_item)
                
        logging.info(f"Ingested {len(valid_reviews)} out of {len(raw_reviews)} reviews successfully.")
        return valid_reviews