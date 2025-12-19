"""
Constants for AI services including scorecard thresholds.
"""

# Scorecard pass/fail thresholds
# A score >= threshold is considered a "pass", < threshold is a "fail"
SCORECARD_THRESHOLDS = {
    'compliance': 40,     # Compliance scorecard must score 40 or above to pass
    'servicing': 40,      # Servicing scorecard must score 40 or above to pass
    'collections': 40,    # Collections scorecard must score 40 or above to pass
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
