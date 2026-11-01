"""
StarveGuard Multi-Scale Deterministic Workload Generator.

Generates reproducible, statistically rigorous benchmark workloads across 5 scales:
    - Small: 10 processes
    - Medium: 50 processes
    - Large: 100 processes
    - Very Large: 250 processes
    - Stress: 500 processes

Across 7 OS Workload Categories:
    - A: Balanced (mixed priorities 1-10, mixed burst 2-20, distributed arrivals)
    - B: Priority Skew (75% lower-priority 7-10, 25% high-priority 1-4)
    - C: Burst Mixture (50% short interactive 1-4, 50% long CPU-bound 25-50)
    - D: Heavy Contention (near-simultaneous arrivals t in [0, 5], high CPU competition)
    - E: Staggered Arrivals (clustered waves with idle gaps between phases)
    - F: Starvation-Prone (continuous stream of high-priority tasks starving low-priority batch jobs)
    - G: Mixed Realistic (40% interactive, 35% normal, 25% batch with arrival bursts)
"""

import random
from typing import Dict, List, Optional, Tuple

SCALE_SIZES: Dict[str, int] = {
    "small": 10,
    "medium": 50,
    "large": 100,
    "very_large": 250,
    "stress": 500,
}

WORKLOAD_CATEGORIES: Dict[str, str] = {
    "A": "Workload A — Balanced",
    "B": "Workload B — Priority Skew",
    "C": "Workload C — Short and Long Burst Mixture",
    "D": "Workload D — Heavy Contention",
    "E": "Workload E — Staggered Arrivals",
    "F": "Workload F — Starvation-Prone",
    "G": "Workload G — Mixed Realistic Workload",
}


def get_workload_scales() -> Dict[str, int]:
    return dict(SCALE_SIZES)


def get_workload_categories() -> Dict[str, str]:
    return dict(WORKLOAD_CATEGORIES)


def generate_benchmark_workload(
    scale: str,
    category: str,
    seed: int,
    custom_n: Optional[int] = None
) -> List[Tuple[str, int, int, int]]:
    """
    Generates a deterministic synthetic workload of (pid, arrival, burst, priority) tuples.

    Parameters:
        scale: One of 'small', 'medium', 'large', 'very_large', 'stress'.
        category: One of 'A', 'B', 'C', 'D', 'E', 'F', 'G'.
        seed: Random seed for 100% deterministic reproducibility.
        custom_n: Optional override for process count.
    """
    scale_lower = scale.lower()
    if custom_n is not None:
        n = custom_n
    elif scale_lower in SCALE_SIZES:
        n = SCALE_SIZES[scale_lower]
    else:
        raise ValueError(f"Unknown scale '{scale}'. Valid scales: {list(SCALE_SIZES.keys())}")

    cat_upper = category.upper()
    if cat_upper not in WORKLOAD_CATEGORIES:
        raise ValueError(
            f"Unknown category '{category}'. Valid categories: {list(WORKLOAD_CATEGORIES.keys())}"
        )

    rng = random.Random(seed)
    processes: List[Tuple[str, int, int, int]] = []

    if cat_upper == "A":
        # Workload A — Balanced:
        # Uniformly distributed priorities 1-10, burst times 2-20, inter-arrivals 1-4.
        sim_time = 0
        for i in range(1, n + 1):
            if i > 1:
                sim_time += rng.randint(1, 4)
            burst = rng.randint(2, 20)
            priority = rng.randint(1, 10)
            processes.append((f"P{i}", sim_time, burst, priority))

    elif cat_upper == "B":
        # Workload B — Priority Skew:
        # Concentration in lower-priority tiers (75% prio 7-10, burst 15-30; 25% prio 1-4, burst 3-8).
        sim_time = 0
        for i in range(1, n + 1):
            if i > 1:
                sim_time += rng.randint(0, 3)
            is_low_priority = (rng.random() < 0.75)
            if is_low_priority:
                burst = rng.randint(15, 30)
                priority = rng.randint(7, 10)
            else:
                burst = rng.randint(3, 8)
                priority = rng.randint(1, 4)
            processes.append((f"P{i}", sim_time, burst, priority))

    elif cat_upper == "C":
        # Workload C — Short and Long Burst Mixture:
        # Bimodal: 50% short interactive (1-4 ticks, prio 1-5), 50% long CPU-bound (25-50 ticks, prio 5-10).
        sim_time = 0
        for i in range(1, n + 1):
            if i > 1:
                sim_time += rng.randint(0, 3)
            if i % 2 == 1:
                burst = rng.randint(1, 4)
                priority = rng.randint(1, 5)
            else:
                burst = rng.randint(25, 50)
                priority = rng.randint(5, 10)
            processes.append((f"P{i}", sim_time, burst, priority))

    elif cat_upper == "D":
        # Workload D — Heavy Contention:
        # High arrival density: all processes arrive close together (t in [0, 5]), competing heavily.
        for i in range(1, n + 1):
            arrival = rng.randint(0, 5)
            burst = rng.randint(5, 20)
            priority = rng.randint(1, 10)
            processes.append((f"P{i}", arrival, burst, priority))

    elif cat_upper == "E":
        # Workload E — Staggered Arrivals:
        # Processes arrive in distinct cluster waves separated by idle gaps.
        sim_time = 0
        cluster_size = max(2, n // 5)
        for i in range(1, n + 1):
            if (i - 1) % cluster_size == 0 and i > 1:
                # Add a substantial idle gap between clusters
                sim_time += rng.randint(20, 45)
            elif i > 1:
                sim_time += rng.randint(0, 2)
            burst = rng.randint(4, 16)
            priority = rng.randint(1, 8)
            processes.append((f"P{i}", sim_time, burst, priority))

    elif cat_upper == "F":
        # Workload F — Starvation-Prone:
        # Initial lower-priority batch jobs (20%, prio 8-10, burst 20-40) at t=0,
        # followed by continuous stream of high-priority processes (80%, prio 1-3, burst 2-5).
        num_victims = max(1, int(n * 0.20))
        for i in range(1, num_victims + 1):
            burst = rng.randint(20, 40)
            priority = rng.randint(8, 10)
            processes.append((f"P{i}", 0, burst, priority))

        sim_time = 0
        for i in range(num_victims + 1, n + 1):
            sim_time += rng.randint(1, 3)
            burst = rng.randint(2, 5)
            priority = rng.randint(1, 3)
            processes.append((f"P{i}", sim_time, burst, priority))

    elif cat_upper == "G":
        # Workload G — Mixed Realistic Workload:
        # 40% interactive (prio 1-3, burst 2-5), 35% normal (prio 4-7, burst 6-15), 25% batch (prio 8-10, burst 20-45).
        sim_time = 0
        for i in range(1, n + 1):
            # Arrival jitter with occasional load bursts
            if rng.random() < 0.15:
                sim_time += rng.randint(5, 12)  # Pause
            else:
                sim_time += rng.randint(0, 2)  # Burst

            tier = rng.choices(["interactive", "normal", "batch"], weights=[0.40, 0.35, 0.25])[0]
            if tier == "interactive":
                burst = rng.randint(2, 5)
                priority = rng.randint(1, 3)
            elif tier == "normal":
                burst = rng.randint(6, 15)
                priority = rng.randint(4, 7)
            else:
                burst = rng.randint(20, 45)
                priority = rng.randint(8, 10)
            processes.append((f"P{i}", sim_time, burst, priority))

    # Sort strictly by arrival time, then by PID for stable deterministic ordering
    processes.sort(key=lambda p: (p[1], int(p[0][1:])))
    return processes

