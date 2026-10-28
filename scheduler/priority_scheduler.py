from typing import List, Optional, Tuple
from scheduler.process import Process
from starvation.detector import StarvationDetector
from aging.aging_manager import AgingManager


class PriorityScheduler:
    """
    StarveGuard Preemptive Priority Scheduler with Starvation Detection and Aging.

    Scheduling Policy:
        - Evaluated per discrete time unit (quantum = 1).
        - Dynamic aging evaluates ready processes at each scheduling decision.
        - Process with lowest numerical effective priority is dispatched.
        - Tie-breaking: earliest arrival time (FCFS), then lexicographical PID.
        - Idle CPU periods are explicitly tracked.
        - Supports:
            * 'capped': Historical 3-tier capped aging (max boost +3)
            * 'continuous': Continuous waiting-time aging (floor 1, parameter K)
            * 'conservative': Threshold-Triggered Conservative Aging (TTCA, floor 2 apex isolation)
    """

    def __init__(
        self,
        processes: List[Process],
        detector: Optional[StarvationDetector] = None,
        aging_manager: Optional[AgingManager] = None,
        aging_policy: str = "capped",
        k: int = 5,
        threshold: int = 20,
        k_starve: int = 10,
        max_boost: int = 3,
        floor: Optional[int] = None
    ):
        self.processes = processes
        self.time = 0
        self.gantt_chart: List[Tuple[str, int]] = []
        self.aging_events: List[Tuple[int, str, int, int, int]] = []
        self.detector = detector if detector is not None else StarvationDetector(threshold=threshold)
        if aging_manager is not None:
            self.aging_manager = aging_manager
        else:
            self.aging_manager = AgingManager(
                policy=aging_policy,
                k=k,
                threshold=threshold,
                k_starve=k_starve,
                max_boost=max_boost,
                floor=floor
            )
        self._last_running_pid: Optional[str] = None

    def get_ready_processes(self) -> List[Process]:
        return [
            p for p in self.processes
            if p.arrival_time <= self.time and p.remaining_time > 0
        ]

    def apply_starvation_prevention(self) -> None:
        """
        Evaluates waiting processes in the ready queue, detects starvation,
        and applies priority aging.
        """
        for p in self.get_ready_processes():
            score = self.detector.calculate_score(p)
            if self.detector.is_starving(p):
                p.starvation_detected = True

            old_priority = p.current_priority
            adjusted = self.aging_manager.apply_aging(p, score)

            if adjusted:
                self.aging_events.append(
                    (
                        self.time,
                        p.pid,
                        old_priority,
                        p.current_priority,
                        score
                    )
                )

    def select_process(self) -> Optional[Process]:
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

    def run(self) -> List[Tuple[str, int]]:
        if not self.processes:
            return self.gantt_chart

        while any(p.remaining_time > 0 for p in self.processes):
            # Apply aging intervention before dispatch arbitration
            self.apply_starvation_prevention()

            process = self.select_process()

            if process is None:
                self.gantt_chart.append(("IDLE", self.time))
                self.time += 1
                self._last_running_pid = None
                continue

            # Track dispatch bypass when a new process is selected
            is_new_dispatch = (self._last_running_pid != process.pid)
            ready = self.get_ready_processes()

            for p in ready:
                if p.pid != process.pid:
                    p.waiting_time += 1
                    if is_new_dispatch:
                        p.bypass_count += 1

            if process.first_run_time == -1:
                process.first_run_time = self.time
                process.response_time = self.time - process.arrival_time

            self.gantt_chart.append((process.pid, self.time))
            self._last_running_pid = process.pid

            process.remaining_time -= 1
            self.time += 1

            if process.remaining_time == 0:
                process.completion_time = self.time
                process.turnaround_time = (
                    process.completion_time - process.arrival_time
                )
                process.waiting_time = (
                    process.turnaround_time - process.burst_time
                )

        return self.gantt_chart
