from scheduler.process import Process
from starvation.detector import StarvationDetector
from aging.aging_manager import AgingManager


class PriorityScheduler:

    def __init__(self, processes):
        self.processes = processes
        self.time = 0
        self.gantt_chart = []
        self.aging_events = []
        self.detector = StarvationDetector()
        self.aging_manager = AgingManager()

    def get_ready_processes(self):
        return [
            p for p in self.processes
            if p.arrival_time <= self.time and p.remaining_time > 0
        ]

    def apply_starvation_prevention(self):
        for p in self.get_ready_processes():
            score = self.detector.calculate_score(p)
            old_priority = p.current_priority

            if score >= 10:
                if score >= self.detector.threshold:
                    p.starvation_detected = True

                self.aging_manager.apply_aging(p, score)

                if p.current_priority != old_priority:
                    self.aging_events.append(
                        (
                            self.time,
                            p.pid,
                            old_priority,
                            p.current_priority,
                            score
                        )
                    )

    def select_process(self):
        ready = self.get_ready_processes()

        if not ready:
            return None

        return min(
            ready,
            key=lambda p: (
                p.current_priority,
                p.arrival_time,
                p.pid
            )
        )

    def run(self):
        while any(p.remaining_time > 0 for p in self.processes):

            process = self.select_process()

            if process is None:
                self.time += 1
                continue

            self.apply_starvation_prevention()

            process = self.select_process()

            if process is None:
                self.time += 1
                continue

            ready = self.get_ready_processes()

            for p in ready:
                if p.pid != process.pid:
                    p.waiting_time += 1
                    p.bypass_count += 1

            if process.first_run_time == -1:
                process.first_run_time = self.time
                process.response_time = (
                    self.time - process.arrival_time
                )

            self.gantt_chart.append(
                (process.pid, self.time)
            )

            process.remaining_time -= 1
            self.time += 1

            if process.remaining_time == 0:
                process.completion_time = self.time
                process.turnaround_time = (
                    process.completion_time -
                    process.arrival_time
                )

        return self.gantt_chart