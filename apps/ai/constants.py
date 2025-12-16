"""
Constants for AI services including scorecard thresholds.
"""

# Scorecard pass/fail thresholds
# A score >= threshold is considered a "pass", < threshold is a "fail"
SCORECARD_THRESHOLDS = {
    'compliance': 80,     # Compliance scorecard must score 80 or above to pass
    'servicing': 70,      # Servicing scorecard must score 70 or above to pass
    'collections': 75,    # Collections scorecard must score 75 or above to pass
}


def get_pass_threshold(category: str) -> int:
    """
    Get the pass threshold for a specific scorecard category.

    Args:
        category: The scorecard category ('compliance', 'servicing', 'collections')

    Returns:
        int: The threshold score for passing
    """
    return SCORECARD_THRESHOLDS.get(category, 70)  # Default to 70 if unknown category
