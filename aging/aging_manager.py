class AgingManager:
    """
    Manages multi-tier adaptive priority aging for processes experiencing starvation.

    Priority Convention:
        Lower numerical value represents higher priority (e.g., 1 is highest priority).

    Aging Policy:
        - Score < 10:  boost = 0 (effective priority = original_priority)
        - Score 10-19: boost = 1 (effective priority = max(1, original_priority - 1))
        - Score 20-29: boost = 2 (effective priority = max(1, original_priority - 2))
        - Score >= 30: boost = 3 (effective priority = max(1, original_priority - 3))

    Anchoring boosts to original_priority prevents runaway unbounded priority escalation,
    while a floor of 1 preserves valid priority boundaries.
    """

    def __init__(self):
        pass

    def calculate_boost(self, starvation_score: int) -> int:
        if starvation_score >= 30:
            return 3
        elif starvation_score >= 20:
            return 2
        elif starvation_score >= 10:
            return 1
        else:
            return 0

    def apply_aging(self, process, starvation_score: int) -> bool:
        """
        Applies priority boost anchored to original priority.
        Returns True if priority was adjusted, False otherwise.
        """
        boost = self.calculate_boost(starvation_score)

        new_priority = max(
            1,
            process.original_priority - boost
        )

        if new_priority != process.current_priority:
            process.current_priority = new_priority
            process.aging_adjustments += 1
            return True
        return False
