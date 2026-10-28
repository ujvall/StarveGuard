import math
from typing import List, Optional
from scheduler.process import Process


class MetricsCalculator:
    """
    Computes system and process performance and fairness metrics.

    Metrics include:
        - Average Waiting Time: Mean time spent in ready queue.
        - Average Turnaround Time: Mean elapsed time from arrival to completion.
        - Average Response Time: Mean time from arrival to first CPU dispatch.
        - Maximum Waiting Time: Highest waiting time experienced by any process.
        - Waiting Time Disparity: Difference between maximum and minimum waiting times.
        - Jain's Fairness Index: Evaluates equity of execution efficiency ratios (burst / turnaround).
        - Starvation Threshold Crossing Count: Processes that crossed the starvation threshold.
        - Protected Process Count: Processes whose priority was improved by aging at least once.
        - Aging Intervention Count: Total number of discrete priority adjustments performed.
    """

    def __init__(self, processes: List[Process]):
        self.processes = processes

    def average_waiting_time(self) -> float:
        if not self.processes:
            return 0.0
        return sum(p.waiting_time for p in self.processes) / len(self.processes)

    def average_turnaround_time(self) -> float:
        if not self.processes:
            return 0.0
        return sum(p.turnaround_time for p in self.processes) / len(self.processes)

    def average_response_time(self) -> float:
        valid_responses = [p.response_time for p in self.processes if p.response_time >= 0]
        if not valid_responses:
            return 0.0
        return sum(valid_responses) / len(valid_responses)

    def maximum_waiting_time(self) -> int:
        if not self.processes:
            return 0
        return max(p.waiting_time for p in self.processes)

    def minimum_waiting_time(self) -> int:
        if not self.processes:
            return 0
        return min(p.waiting_time for p in self.processes)

    def waiting_time_disparity(self) -> int:
        """Spread between longest and shortest waiting times."""
        if not self.processes:
            return 0
        return self.maximum_waiting_time() - self.minimum_waiting_time()

    def waiting_time_std_dev(self) -> float:
        """Standard deviation of waiting time across processes."""
        if len(self.processes) <= 1:
            return 0.0
        avg = self.average_waiting_time()
        variance = sum((p.waiting_time - avg) ** 2 for p in self.processes) / len(self.processes)
        return math.sqrt(variance)

    def fairness_index(self) -> float:
        """
        Computes Jain's Fairness Index based on process execution efficiency ratio:
            x_i = burst_time / turnaround_time (0 < x_i <= 1.0)
            J(x) = (sum(x_i))^2 / (n * sum(x_i^2))

        1.0 denotes equal execution efficiency across all jobs.
        """
        if not self.processes:
            return 1.0

        values = [
            (p.burst_time / p.turnaround_time)
            for p in self.processes
            if p.turnaround_time > 0
        ]

        if not values:
            return 1.0

        total = sum(values)
        square_total = sum(v * v for v in values)

        if square_total == 0:
            return 1.0

        return (total * total) / (len(values) * square_total)

    def jains_fairness_index(self) -> float:
        """Explicit alias for fairness_index()."""
        return self.fairness_index()

    def starved_process_count(self, detector=None) -> int:
        """
        Counts processes that crossed the starvation threshold during simulation.
        Accepts optional detector instance for backward compatibility.
        """
        if detector is not None:
            return sum(detector.is_starving(p) for p in self.processes)
        return sum(p.starvation_detected for p in self.processes)

    def starvation_threshold_crossed_count(self) -> int:
        """Unambiguous alias for processes that crossed the starvation threshold."""
        return self.starved_process_count()

    def aging_intervention_count(self, scheduler) -> int:
        return len(scheduler.aging_events)

    def protected_process_count(self) -> int:
        """Processes whose priority was improved by aging at least once."""
        return sum(p.aging_adjustments > 0 for p in self.processes)

    def priority_changed_count(self) -> int:
        """Processes whose priority was altered by aging."""
        return self.protected_process_count()
