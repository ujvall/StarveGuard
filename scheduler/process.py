from dataclasses import dataclass


@dataclass
class Process:
    """
    Represents a process / task in the CPU scheduler.

    Priority convention:
        Lower numerical value represents higher scheduling priority (e.g., priority 1 is highest).
    """
    pid: str
    arrival_time: int
    burst_time: int
    original_priority: int

    remaining_time: int = 0
    current_priority: int = 0
    waiting_time: int = 0
    bypass_count: int = 0
    completion_time: int = 0
    turnaround_time: int = 0
    response_time: int = -1
    aging_adjustments: int = 0
    starvation_detected: bool = False
    first_run_time: int = -1

    def __post_init__(self):
        self.remaining_time = self.burst_time
        self.current_priority = self.original_priority

    def clone(self) -> "Process":
        """Produce an independent copy with initial state."""
        return Process(
            pid=self.pid,
            arrival_time=self.arrival_time,
            burst_time=self.burst_time,
            original_priority=self.original_priority
        )
