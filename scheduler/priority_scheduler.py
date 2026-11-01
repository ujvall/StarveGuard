import time
from typing import Callable, List, Optional, Tuple, Union
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
        floor: Optional[int] = None,
        tie_breaker: Union[str, Callable] = "fcfs",
        emergency_threshold: int = 40,
        gamma: float = 0.05,
        preemption_hysteresis: bool = False,
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
        self.tie_breaker = tie_breaker
        self.emergency_threshold = emergency_threshold
        self.gamma = gamma
        self.preemption_hysteresis = preemption_hysteresis
        self._last_running_pid: Optional[str] = None
        self.scheduling_decisions: int = 0
        self.decision_time_sec: float = 0.0
        self.priority_evaluations: int = 0
        self.preemption_count: int = 0

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
        ready = self.get_ready_processes()
        if not ready:
            return

        # Precompute higher-priority counts in O(|ready|) via prefix sums:
        max_p = max((p.current_priority for p in ready), default=1)
        counts = [0] * (max_p + 2)
        for p in ready:
            counts[p.current_priority] += 1
        cum = [0] * (max_p + 2)
        acc = 0
        for pr in range(1, max_p + 2):
            cum[pr] = acc
            acc += counts[pr]

        for p in ready:
            self.priority_evaluations += 1
            score = self.detector.calculate_score(p)
            if self.detector.is_starving(p):
                p.starvation_detected = True

            old_priority = p.current_priority
            # Compute queue pressure (count of ready processes with higher effective priority) in O(1)
            higher_count = cum[p.current_priority] if p.current_priority < len(cum) else acc
            adjusted = self.aging_manager.apply_aging(p, score, higher_prio_count=higher_count)

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

        if callable(self.tie_breaker):
            candidate = min(ready, key=self.tie_breaker)
        elif self.tie_breaker in ("srtf", "remaining_time", "shortest_remaining"):
            candidate = min(
                ready,
                key=lambda p: (
                    p.current_priority,
                    p.remaining_time,
                    p.arrival_time,
                    p.pid
                )
            )
        elif self.tie_breaker in ("starvation_aware_srtf", "sa_srtf", "discounted_srtf"):
            th = getattr(self.aging_manager, "threshold", 20) or 20
            candidate = min(
                ready,
                key=lambda p: (
                    p.current_priority,
                    p.remaining_time - self.gamma * max(0, p.waiting_time - th),
                    p.arrival_time,
                    p.pid
                )
            )
        elif self.tie_breaker in ("dual_tier", "emergency_srtf", "hybrid"):
            candidate = min(
                ready,
                key=lambda p: (
                    p.current_priority,
                    0 if p.waiting_time >= self.emergency_threshold else 1,
                    p.remaining_time,
                    p.arrival_time,
                    p.pid
                )
            )
        else:  # "fcfs" (default)
            candidate = min(
                ready,
                key=lambda p: (
                    p.current_priority,
                    p.arrival_time,
                    p.pid
                )
            )

        if self.preemption_hysteresis and self._last_running_pid:
            curr = next((p for p in ready if p.pid == self._last_running_pid), None)
            if curr and curr.remaining_time <= 1:
                if candidate.current_priority < curr.current_priority:
                    return candidate
                else:
                    return curr

        return candidate

    def run(self) -> List[Tuple[str, int]]:
        if not self.processes:
            return self.gantt_chart

        while any(p.remaining_time > 0 for p in self.processes):
            _t0 = time.perf_counter()
            # Apply aging intervention before dispatch arbitration
            self.apply_starvation_prevention()
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
                process.turnaround_time = (
                    process.completion_time - process.arrival_time
                )
                process.waiting_time = (
                    process.turnaround_time - process.burst_time
                )

        return self.gantt_chart
