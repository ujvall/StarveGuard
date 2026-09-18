class AgingManager:

    def __init__(self):
        pass

    def calculate_boost(self, starvation_score):
        if starvation_score >= 30:
            return 3
        elif starvation_score >= 20:
            return 2
        elif starvation_score >= 10:
            return 1
        else:
            return 0

    def apply_aging(self, process, starvation_score):
        boost = self.calculate_boost(starvation_score)

        new_priority = max(
            1,
            process.original_priority - boost
        )

        if new_priority != process.current_priority:
            process.current_priority = new_priority
            process.aging_adjustments += 1
