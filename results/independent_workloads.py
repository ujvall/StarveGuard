"""
StarveGuard Independent Validation Workload Generator.

Generates rigorous out-of-sample and adversarial test workloads to evaluate
scheduling policies beyond the standard synthetic benchmark suite:
    - VAL_SHORT_STREAM: Continuous arrival of short interactive tasks
    - VAL_LONG_STREAM: Continuous arrival of long compute-bound batch jobs
    - VAL_P1_SATURATION: Heavy Priority 1 saturation (stressing Apex Isolation)
    - VAL_PRIORITY_GAPS: Extreme priority disparity (P1 vs P10)
    - VAL_QUEUE_BURST: Massive simultaneous arrival (t=0 congestion)
    - VAL_STAGGERED_WAVES: Multi-wave arrival clusters with distinct gaps
    - VAL_ADVERSARIAL: Pathological arrival pattern engineered to trigger starvation
"""

import random
from typing import Dict, List, Tuple

VALIDATION_SCENARIOS: Dict[str, str] = {
    "VAL_SHORT_STREAM": "Continuous Short Process Arrival Stream",
    "VAL_LONG_STREAM": "Continuous Long Process Arrival Stream",
    "VAL_P1_SATURATION": "Heavy Priority 1 Apex Saturation",
    "VAL_PRIORITY_GAPS": "Extreme Priority Disparity (P1 vs P10)",
    "VAL_QUEUE_BURST": "Massive Ready-Queue Congestion (All Arrival at t=0)",
    "VAL_STAGGERED_WAVES": "Clustered Wave Arrivals with Execution Gaps",
    "VAL_ADVERSARIAL": "Adversarial Starvation-Trapping Interleaved Arrivals",
}


def generate_independent_workload(
    scenario: str,
    n_processes: int = 100,
    seed: int = 7000
) -> List[Tuple[str, int, int, int]]:
    """
    Generates deterministic, out-of-sample validation workloads:
        Returns list of (pid, arrival_time, burst_time, original_priority)
    """
    rng = random.Random(seed)
    processes = []

    if scenario == "VAL_SHORT_STREAM":
        # First 5% are long batch jobs arriving at t=0 with lower priority (e.g. prio 4-6)
        # Remainder 95% are continuous stream of short interactive jobs (burst 1-3, prio 2)
        n_long = max(2, n_processes // 20)
        for i in range(n_long):
            processes.append((f"P_LONG_{i}", 0, rng.randint(25, 45), rng.randint(4, 6)))
        curr_t = 1
        for i in range(n_processes - n_long):
            curr_t += rng.randint(1, 3)
            processes.append((f"P_SHORT_{i}", curr_t, rng.randint(1, 3), 2))

    elif scenario == "VAL_LONG_STREAM":
        # Continuous arrivals of heavy CPU-bound jobs (burst 30-60)
        curr_t = 0
        for i in range(n_processes):
            processes.append((f"P_CPU_{i}", curr_t, rng.randint(30, 60), rng.randint(1, 8)))
            curr_t += rng.randint(5, 15)

    elif scenario == "VAL_P1_SATURATION":
        # 60% of all processes are assigned Priority 1 (Apex), testing system resilience
        curr_t = 0
        for i in range(n_processes):
            is_p1 = (rng.random() < 0.60)
            prio = 1 if is_p1 else rng.randint(2, 10)
            burst = rng.randint(2, 12) if is_p1 else rng.randint(10, 30)
            processes.append((f"P_P1SAT_{i}", curr_t, burst, prio))
            curr_t += rng.randint(1, 4)

    elif scenario == "VAL_PRIORITY_GAPS":
        # Bimodal priorities: only Priority 1 and Priority 10
        curr_t = 0
        for i in range(n_processes):
            prio = 1 if (rng.random() < 0.35) else 10
            burst = rng.randint(2, 8) if prio == 1 else rng.randint(15, 35)
            processes.append((f"P_GAP_{i}", curr_t, burst, prio))
            curr_t += rng.randint(1, 5)

    elif scenario == "VAL_QUEUE_BURST":
        # All processes arrive simultaneously at t=0
        for i in range(n_processes):
            processes.append((f"P_BURST_{i}", 0, rng.randint(2, 25), rng.randint(1, 10)))

    elif scenario == "VAL_STAGGERED_WAVES":
        # 4 distinct waves with long idle gaps between them
        wave_size = n_processes // 4
        base_t = 0
        p_idx = 0
        for w in range(4):
            for _ in range(wave_size):
                processes.append((f"P_WAVE_{p_idx}", base_t + rng.randint(0, 10), rng.randint(3, 15), rng.randint(1, 10)))
                p_idx += 1
            base_t += wave_size * 10 + 50  # large gap

    elif scenario == "VAL_ADVERSARIAL":
        # 10 low-priority batch jobs (prio 9, burst 40) at t=0
        # Continuous stream of high-priority tasks (prio 1-2, burst 4) precisely timed
        # to trigger repeated preemption and starve the batch jobs
        for i in range(10):
            processes.append((f"P_TRAPPED_{i}", 0, 40, 9))
        curr_t = 2
        for i in range(n_processes - 10):
            processes.append((f"P_ADV_{i}", curr_t, 4, rng.choice([1, 2])))
            curr_t += 3  # arrives right before previous would finish

    else:
        raise ValueError(f"Unknown validation scenario: {scenario}")

    processes.sort(key=lambda p: (p[1], p[0]))
    return processes
