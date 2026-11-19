from validation.validator import ReviewIngestionPipeline
from services.llm_service import LLMReviewProcessor
from core.calculator import MetricsCalculator

def run_pipeline():
    raw_data = [
        {"review_id": "REV-001", "text": "The sound system at the main stage was fantastic, but the bathroom queues took over 45 minutes!"},
        {"review_id": "REV-002", "text": "We loved the food trucks, though water stations ran out of cups by 6 PM. Needs improvement."}
    ]

    # 1. Ingest & Sanitize via Validator Package
    pipeline = ReviewIngestionPipeline(min_length=15)
    cleaned_reviews = pipeline.process_batch(raw_data)

    # 2. LLM Processing via Services Package
    processor = LLMReviewProcessor()
    analyzed_results = [processor.analyze_review(r) for r in cleaned_reviews]

    # 3. Python Math & Analytics via Core Package
    final_report = MetricsCalculator.calculate_summary_metrics(analyzed_results)
    
    print("--- VibeCheck AI Final Report ---")
    print(final_report)

if __name__ == "__main__":
    run_pipeline()