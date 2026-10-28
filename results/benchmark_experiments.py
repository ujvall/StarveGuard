import csv
import os
import random
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Dict, List, Tuple
from comparison.comparator import SchedulerComparator
from scheduler.process import Process


def generate_controlled_workloads() -> Dict[str, List[Tuple[str, int, int, int]]]:
    """
    Generates deterministic, reproducible workloads across Small (10), Medium (50),
    and Large (100) scales with diverse arrival patterns and priority imbalances.
    """
    workloads = {}
    rng = random.Random(42)

    # 1. Standard Benchmark Suites (for backwards compatibility and direct inspection)
    workloads["Workload 1 (Classic Starvation)"] = [
        ("P1", 0, 20, 6),
        ("P2", 0, 5, 8),
        ("P3", 0, 5, 9)
    ]

    workloads["Workload 2 (Staggered Arrivals)"] = [
        ("P1", 0, 8, 3),
        ("P2", 1, 4, 1),
        ("P3", 2, 3, 4),
        ("P4", 4, 5, 8)
    ]

    workloads["Workload 3 (Long-Burst Starvation)"] = [
        ("P1", 0, 30, 6),
        ("P2", 0, 10, 8),
        ("P3", 0, 10, 9)
    ]

    workloads["Workload 4 (Sequential Non-Contested)"] = [
        ("P1", 3, 4, 2),
        ("P2", 7, 3, 1),
        ("P3", 10, 2, 3)
    ]

    # 2. Small Scale (~10 processes)
    # Scenario: Small High-Priority Bias (starvation stress test)
    small_procs = []
    # 2 low priority victim processes arriving early
    small_procs.append(("P1", 0, 25, 9))
    small_procs.append(("P2", 2, 20, 8))
    # 8 higher priority short jobs arriving sequentially
    for i in range(3, 11):
        arrival = (i - 3) * 3
        burst = rng.randint(2, 6)
        prio = rng.randint(1, 4)
        small_procs.append((f"P{i}", arrival, burst, prio))
    workloads["Small Scale (10 procs - Contention)"] = small_procs

    # 3. Medium Scale (~50 processes)
    # Scenario: 50 processes with 75% high-priority short tasks and 25% low-priority background tasks
    medium_procs = []
    current_time = 0
    for i in range(1, 51):
        current_time += rng.randint(0, 3)
        if i % 4 == 0:
            # Low priority long task (vulnerable to starvation)
            burst = rng.randint(15, 30)
            prio = rng.randint(7, 10)
        else:
            # High/medium priority interactive job
            burst = rng.randint(2, 8)
            prio = rng.randint(1, 5)
        medium_procs.append((f"P{i}", current_time, burst, prio))
    workloads["Medium Scale (50 procs - Skewed)"] = medium_procs

    # 4. Large Scale (~100 processes)
    # Scenario: 100 processes across multi-tier priority classes with realistic arrival bursts
    large_procs = []
    sim_time = 0
    for i in range(1, 101):
        # Clustered arrivals
        if i % 10 == 0:
            sim_time += rng.randint(5, 12)
        else:
            sim_time += rng.randint(0, 2)

        # Diverse priority distribution
        tier = rng.choices(["interactive", "normal", "batch"], weights=[0.4, 0.4, 0.2])[0]
        if tier == "interactive":
            burst = rng.randint(2, 6)
            prio = rng.randint(1, 3)
        elif tier == "normal":
            burst = rng.randint(5, 15)
            prio = rng.randint(4, 7)
        else:
            burst = rng.randint(18, 40)
            prio = rng.randint(8, 10)

        large_procs.append((f"P{i}", sim_time, burst, prio))
    workloads["Large Scale (100 procs - Multi-tier)"] = large_procs

    return workloads


def run_all_benchmarks(output_csv: str = "results/workload_results.csv"):
    workloads = generate_controlled_workloads()
    rows = []

    print(f"\nExecuting StarveGuard Controlled Benchmark Suite ({len(workloads)} Workloads)...")
    print("=" * 110)

    for name, data in workloads.items():
        comparator = SchedulerComparator(data)
        normal = comparator.run_normal()
        starveguard = comparator.run_starveguard()

        row = {
            "Workload": name,
            "Processes": len(data),
            "Normal Avg Waiting": f"{normal['average_waiting']:.2f}",
            "StarveGuard Avg Waiting": f"{starveguard['average_waiting']:.2f}",
            "Normal Avg Turnaround": f"{normal['average_turnaround']:.2f}",
            "StarveGuard Avg Turnaround": f"{starveguard['average_turnaround']:.2f}",
            "Normal Avg Response": f"{normal['average_response']:.2f}",
            "StarveGuard Avg Response": f"{starveguard['average_response']:.2f}",
            "Normal Max Waiting": normal["maximum_waiting"],
            "StarveGuard Max Waiting": starveguard["maximum_waiting"],
            "Normal Fairness": f"{normal['fairness']:.4f}",
            "StarveGuard Fairness": f"{starveguard['fairness']:.4f}",
            "Normal Waiting Disparity": normal["waiting_disparity"],
            "StarveGuard Waiting Disparity": starveguard["waiting_disparity"],
            "Starved Processes": starveguard["starved_processes"],
            "Protected Processes": starveguard["protected_processes"],
            "Aging Interventions": starveguard["aging_interventions"],
        }
        rows.append(row)

        print(f"\n{name} (N={len(data)})")
        print(f"  Avg Waiting:    Normal={normal['average_waiting']:.2f} | SG={starveguard['average_waiting']:.2f} (Delta: {starveguard['average_waiting'] - normal['average_waiting']:+.2f})")
        print(f"  Max Waiting:    Normal={normal['maximum_waiting']} | SG={starveguard['maximum_waiting']} (Delta: {starveguard['maximum_waiting'] - normal['maximum_waiting']:+d})")
        print(f"  Avg Response:   Normal={normal['average_response']:.2f} | SG={starveguard['average_response']:.2f} (Delta: {starveguard['average_response'] - normal['average_response']:+.2f})")
        print(f"  Fairness Index: Normal={normal['fairness']:.4f} | SG={starveguard['fairness']:.4f}")
        print(f"  Starvation Threshold Crossings: {starveguard['starved_processes']} | Protected: {starveguard['protected_processes']} | Interventions: {starveguard['aging_interventions']}")

    # Write CSV
    fieldnames = [
        "Workload",
        "Processes",
        "Normal Avg Waiting",
        "StarveGuard Avg Waiting",
        "Normal Avg Turnaround",
        "StarveGuard Avg Turnaround",
        "Normal Avg Response",
        "StarveGuard Avg Response",
        "Normal Max Waiting",
        "StarveGuard Max Waiting",
        "Normal Fairness",
        "StarveGuard Fairness",
        "Normal Waiting Disparity",
        "StarveGuard Waiting Disparity",
        "Starved Processes",
        "Protected Processes",
        "Aging Interventions"
    ]

    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nBenchmark suite complete. Output saved to {output_csv}\n")


if __name__ == "__main__":
    run_all_benchmarks()
