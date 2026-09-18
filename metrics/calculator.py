class MetricsCalculator:

    def __init__(self, processes):
        self.processes = processes

    def average_waiting_time(self):
        return sum(
            p.waiting_time for p in self.processes
        ) / len(self.processes)

    def average_turnaround_time(self):
        return sum(
            p.turnaround_time for p in self.processes
        ) / len(self.processes)

    def average_response_time(self):
        return sum(
            p.response_time for p in self.processes
        ) / len(self.processes)

    def maximum_waiting_time(self):
        return max(
            p.waiting_time for p in self.processes
        )

    def fairness_index(self):
        values = [
            p.burst_time / p.turnaround_time
            for p in self.processes
            if p.turnaround_time > 0
        ]

        total = sum(values)
        square_total = sum(v * v for v in values)

        return (total * total) / (
            len(values) * square_total
        )

    def starved_process_count(self):
        return sum(
            p.starvation_detected
            for p in self.processes
        )

    def aging_intervention_count(self, scheduler):
        return len(scheduler.aging_events)

    def protected_process_count(self):
        return sum(
            p.aging_adjustments > 0
            for p in self.processes
        )