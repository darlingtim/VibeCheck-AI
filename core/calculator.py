from typing import List, Dict, Any
from collections import Counter

class MetricsCalculator:
    @staticmethod
    def calculate_summary_metrics(analyzed_reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Computes accurate percentages and complaint frequencies via Python."""
        total_reviews = len(analyzed_reviews)
        if total_reviews == 0:
            return {"total_reviews": 0}

        sentiments = [r.get("sentiment") for r in analyzed_reviews if "sentiment" in r]
        themes = [r.get("primary_theme") for r in analyzed_reviews if "primary_theme" in r]
        
        sentiment_counts = Counter(sentiments)
        theme_counts = Counter(themes)

        sentiment_percentages = {
            sent: round((count / total_reviews) * 100, 2)
            for sent, count in sentiment_counts.items()
        }

        return {
            "total_reviews": total_reviews,
            "sentiment_breakdown": sentiment_percentages,
            "top_complaint_themes": theme_counts.most_common(3)
        }