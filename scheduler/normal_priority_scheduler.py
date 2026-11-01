import time
from typing import List, Optional, Tuple
from scheduler.process import Process


class NormalPriorityScheduler:
    """
    Standard Preemptive Priority Scheduler.

    Scheduling policy:
        - Evaluated per discrete time unit (quantum = 1).
        - Lowest numerical priority value runs first.
        - Tie-breaking: earliest arrival time (FCFS), then lexicographical PID.
        - Priorities remain fixed (no aging or starvation intervention).
    """

    def __init__(self, processes: List[Process]):
        self.processes = processes
        self.time = 0
        self.gantt_chart: List[Tuple[str, int]] = []
        self._last_running_pid: Optional[str] = None
        self.scheduling_decisions: int = 0
        self.decision_time_sec: float = 0.0
        self.preemption_count: int = 0

    def get_ready_processes(self) -> List[Process]:
        return [
            p for p in self.processes
            if p.arrival_time <= self.time and p.remaining_time > 0
        ]

    def select_process(self) -> Optional[Process]:
        ready = self.get_ready_processes()
        if not ready:
            return None

        return min(
            ready,
            key=lambda p: (p.current_priority, p.arrival_time, p.pid)
        )

    def run(self) -> List[Tuple[str, int]]:
        if not self.processes:
            return self.gantt_chart

        while any(p.remaining_time > 0 for p in self.processes):
            _t0 = time.perf_counter()
            process = self.select_process()
            self.decision_time_sec += (time.perf_counter() - _t0)
            self.scheduling_decisions += 1

            if process is None:
                self.gantt_chart.append(("IDLE", self.time))
                self.time += 1
                self._last_running_pid = None
                continue

            # Track dispatch bypass and preemption when a new process is selected
            is_new_dispatch = (self._last_running_pid != process.pid)
            if is_new_dispatch and self._last_running_pid is not None:
                last_p = next((p for p in self.processes if p.pid == self._last_running_pid), None)
                if last_p and last_p.remaining_time > 0:
                    self.preemption_count += 1

            ready = self.get_ready_processes()

            for p in ready:
                if p.pid != process.pid:
                    p.waiting_time += 1
                    p.current_wait_streak += 1
                    if p.current_wait_streak > p.longest_continuous_wait:
                        p.longest_continuous_wait = p.current_wait_streak
                    if is_new_dispatch:
                        p.bypass_count += 1
                else:
                    p.current_wait_streak = 0

            if process.first_run_time == -1:
                process.first_run_time = self.time
                process.response_time = self.time - process.arrival_time

            self.gantt_chart.append((process.pid, self.time))
            self._last_running_pid = process.pid

            process.remaining_time -= 1
            self.time += 1

            if process.remaining_time == 0:
                process.completion_time = self.time
                process.turnaround_time = process.completion_time - process.arrival_time
                process.waiting_time = process.turnaround_time - process.burst_time

        return self.gantt_chart
