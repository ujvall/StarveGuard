class StarvationDetector:
    """
    Evaluates process starvation severity.

    In Operating Systems scheduling, starvation is fundamentally characterized by
    excessive queue waiting time without CPU allocation.

    Starvation Score calculation:
        score = waiting_time + (bypass_count * bypass_weight)

    By default, bypass_weight is 0, simplifying the score directly to queue waiting time,
    which provides an unambiguous, physically interpretable starvation metric.
    If bypass_weight > 0 is configured, the score additionally factors in dispatch bypasses
    (the number of scheduling decisions where another process was selected ahead of this process).
    """

    def __init__(self, threshold: int = 20, bypass_weight: int = 0):
        self.threshold = threshold
        self.bypass_weight = bypass_weight

    def calculate_score(self, process) -> int:
        if self.bypass_weight == 0:
            return process.waiting_time
        return process.waiting_time + (process.bypass_count * self.bypass_weight)

    def is_starving(self, process) -> bool:
        return self.calculate_score(process) >= self.threshold
