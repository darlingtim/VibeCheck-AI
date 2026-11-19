import pytest
from validation.validator import ReviewIngestionPipeline
from core.calculator import MetricsCalculator

def test_sanitization_removes_extra_whitespace():
    pipeline = ReviewIngestionPipeline()
    raw = "   Too   much   space   "
    assert pipeline.sanitize_text(raw) == "Too much space"

def test_validation_rejects_short_reviews():
    pipeline = ReviewIngestionPipeline(min_length=20)
    review = {"review_id": "REV-999", "text": "Too short"}
    assert pipeline.validate_review(review) is False

def test_calculator_percentages():
    mock_analyzed = [
        {"sentiment": "Positive", "primary_theme": "Sound"},
        {"sentiment": "Negative", "primary_theme": "Bathrooms"},
        {"sentiment": "Positive", "primary_theme": "Sound"}
    ]
    report = MetricsCalculator.calculate_summary_metrics(mock_analyzed)
    assert report["total_reviews"] == 3
    assert report["sentiment_breakdown"]["Positive"] == 66.67