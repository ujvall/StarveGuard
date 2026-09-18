class StarvationDetector:

    def __init__(self, threshold=20, bypass_weight=2):
        self.threshold = threshold
        self.bypass_weight = bypass_weight

    def calculate_score(self, process):
        return process.waiting_time + (
            process.bypass_count * self.bypass_weight
        )

    def is_starving(self, process):
        score = self.calculate_score(process)
        return score >= self.threshold
