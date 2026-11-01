"""
StarveGuard Scheduling Invariants Verification Module.

Enforces strict formal invariants for uniprocessor preemptive scheduling:
    1. Complete Execution: Every process completes exactly once (remaining_time == 0).
    2. Chronological Feasibility: Completion time >= arrival time.
    3. Turnaround Conservation: Turnaround Time = Completion Time - Arrival Time.
    4. Waiting Time Conservation: Waiting Time = Turnaround Time - Burst Time.
    5. Response Time Definition: Response Time = First Run Time - Arrival Time (>= 0).
    6. No Execution Prior to Arrival: No process runs before its arrival time.
    7. Mutual Exclusion & Uniprocessor Invariant: Exactly one process (or IDLE) runs per discrete clock tick.
    8. Workload Identity & Immutability: Base process attributes match the input workload.
"""

from typing import Any, Dict, List, Tuple
from scheduler.process import Process


class InvariantViolationError(AssertionError):
    """Raised when any fundamental scheduling invariant is violated."""
    pass


def validate_scheduling_invariants(
    processes: List[Process],
    scheduler: Any,
    original_workload: List[Tuple[str, int, int, int]]
) -> bool:
    """
    Validates all 8 formal scheduling invariants.
    Returns True if all invariants hold; raises InvariantViolationError otherwise.
    """
    if not processes and not original_workload:
        return True

    if len(processes) != len(original_workload):
        raise InvariantViolationError(
            f"Process count mismatch: {len(processes)} processed vs {len(original_workload)} input."
        )

    # 8. Workload Identity & Immutability
    input_map = {item[0]: item for item in original_workload}
    proc_map = {p.pid: p for p in processes}

    for pid, orig_arrival, orig_burst, orig_prio in original_workload:
        if pid not in proc_map:
            raise InvariantViolationError(f"Missing process {pid} in completed processes.")
        p = proc_map[pid]
        if p.arrival_time != orig_arrival:
            raise InvariantViolationError(
                f"Process {pid} arrival time altered: {p.arrival_time} != {orig_arrival}"
            )
        if p.burst_time != orig_burst:
            raise InvariantViolationError(
                f"Process {pid} burst time altered: {p.burst_time} != {orig_burst}"
            )
        if p.original_priority != orig_prio:
            raise InvariantViolationError(
                f"Process {pid} original priority altered: {p.original_priority} != {orig_prio}"
            )

    # 1. Complete Execution
    for p in processes:
        if p.remaining_time != 0:
            raise InvariantViolationError(
                f"Process {p.pid} did not complete: remaining_time={p.remaining_time}"
            )
        if p.completion_time < 0:
            raise InvariantViolationError(
                f"Process {p.pid} has invalid completion_time={p.completion_time}"
            )

        # 2. Chronological Feasibility
        if p.completion_time < p.arrival_time:
            raise InvariantViolationError(
                f"Process {p.pid} completed before arrival: CT={p.completion_time} < AT={p.arrival_time}"
            )

        # 3. Turnaround Conservation
        expected_tat = p.completion_time - p.arrival_time
        if p.turnaround_time != expected_tat:
            raise InvariantViolationError(
                f"Process {p.pid} TAT violation: {p.turnaround_time} != {expected_tat} (CT-AT)"
            )

        # 4. Waiting Time Conservation
        expected_wt = p.turnaround_time - p.burst_time
        if p.waiting_time != expected_wt:
            raise InvariantViolationError(
                f"Process {p.pid} WT violation: {p.waiting_time} != {expected_wt} (TAT-BT)"
            )

        # 5. Response Time Definition
        if p.first_run_time < 0:
            raise InvariantViolationError(
                f"Process {p.pid} was never dispatched: first_run_time={p.first_run_time}"
            )
        expected_rt = p.first_run_time - p.arrival_time
        if p.response_time != expected_rt:
            raise InvariantViolationError(
                f"Process {p.pid} RT violation: {p.response_time} != {expected_rt} (FirstRun-AT)"
            )
        if p.response_time < 0:
            raise InvariantViolationError(
                f"Process {p.pid} has negative response time: {p.response_time}"
            )

        # 6. No Execution Prior to Arrival
        if p.first_run_time < p.arrival_time:
            raise InvariantViolationError(
                f"Process {p.pid} executed before arrival: FirstRun={p.first_run_time} < AT={p.arrival_time}"
            )

    # 7. Mutual Exclusion & Uniprocessor Contiguity in Gantt Chart
    gantt = scheduler.gantt_chart
    total_time = scheduler.time
    if len(gantt) != total_time:
        raise InvariantViolationError(
            f"Gantt chart length mismatch: {len(gantt)} slices != total simulation time {total_time}"
        )

    for tick, (pid, scheduled_tick) in enumerate(gantt):
        if tick != scheduled_tick:
            raise InvariantViolationError(
                f"Gantt tick index non-contiguous at index {tick}: recorded tick is {scheduled_tick}"
            )
        if pid != "IDLE":
            p = proc_map.get(pid)
            if p is None:
                raise InvariantViolationError(f"Unknown PID '{pid}' in Gantt chart at tick {tick}")
            if tick < p.arrival_time:
                raise InvariantViolationError(
                    f"Process {pid} scheduled at tick {tick} before its arrival {p.arrival_time}"
                )

    return True

