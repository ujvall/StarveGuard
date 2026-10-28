import csv
import math
import os
import random
import sys
import time
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from comparison.comparator import SchedulerComparator
from results.benchmark_experiments import generate_controlled_workloads


def generate_independent_workload(
    scale: str,
    seed: int
) -> List[Tuple[str, int, int, int]]:
    """
    Generates an independent, deterministic synthetic workload with realistic OS characteristics:
      - Skewed and balanced priorities
      - Staggered and burst arrivals
      - Mixed short interactive tasks and long CPU-bound jobs
    """
    rng = random.Random(seed)
    processes = []

    if scale == "small":
        n = 10
        # 20% long low-priority victim jobs, 80% higher-priority short jobs
        sim_time = 0
        for i in range(1, n + 1):
            if i <= 2:
                arrival = (i - 1) * 2
                burst = rng.randint(18, 25)
                prio = rng.randint(8, 10)
            else:
                sim_time += rng.randint(1, 4)
                arrival = sim_time
                burst = rng.randint(2, 6)
                prio = rng.randint(1, 4)
            processes.append((f"P{i}", arrival, burst, prio))

    elif scale == "medium":
        n = 50
        # 25% background/batch long jobs (prio 7-10), 75% interactive/normal jobs (prio 1-6)
        sim_time = 0
        for i in range(1, n + 1):
            sim_time += rng.randint(0, 3)
            if i % 4 == 0:
                burst = rng.randint(15, 32)
                prio = rng.randint(7, 10)
            else:
                burst = rng.randint(2, 8)
                prio = rng.randint(1, 5)
            processes.append((f"P{i}", sim_time, burst, prio))

    elif scale == "large":
        n = 100
        # 3-tier distribution with arrival bursts
        sim_time = 0
        for i in range(1, n + 1):
            if i % 10 == 0:
                sim_time += rng.randint(4, 10)
            else:
                sim_time += rng.randint(0, 2)

            tier = rng.choices(["interactive", "normal", "batch"], weights=[0.45, 0.35, 0.20])[0]
            if tier == "interactive":
                burst = rng.randint(2, 6)
                prio = rng.randint(1, 3)
            elif tier == "normal":
                burst = rng.randint(5, 14)
                prio = rng.randint(4, 7)
            else:
                burst = rng.randint(18, 40)
                prio = rng.randint(8, 10)
            processes.append((f"P{i}", sim_time, burst, prio))
    else:
        raise ValueError(f"Unknown scale: {scale}")

    return processes


def evaluate_workload(
    workload: List[Tuple[str, int, int, int]]
) -> Dict[str, Dict[str, Any]]:
    """Runs all 6 scheduling policies on the identical input workload."""
    comparator = SchedulerComparator(workload)

    # 1. Normal Priority
    t0 = time.perf_counter()
    res_normal = comparator.run_normal()
    dur_normal = (time.perf_counter() - t0) * 1000.0

    # 2. Capped Aging (+3)
    t0 = time.perf_counter()
    res_capped = comparator.run_starveguard(aging_policy="capped")
    dur_capped = (time.perf_counter() - t0) * 1000.0

    # 3. Continuous Aging K=3
    t0 = time.perf_counter()
    res_cont_k3 = comparator.run_starveguard(aging_policy="continuous", k=3)
    dur_cont_k3 = (time.perf_counter() - t0) * 1000.0

    # 4. Continuous Aging K=5
    t0 = time.perf_counter()
    res_cont_k5 = comparator.run_starveguard(aging_policy="continuous", k=5)
    dur_cont_k5 = (time.perf_counter() - t0) * 1000.0

    # 5. Continuous Aging K=10
    t0 = time.perf_counter()
    res_cont_k10 = comparator.run_starveguard(aging_policy="continuous", k=10)
    dur_cont_k10 = (time.perf_counter() - t0) * 1000.0

    # 6. Threshold-Triggered Conservative Aging (TTCA)
    t0 = time.perf_counter()
    res_ttca = comparator.run_starveguard_conservative(
        threshold=20,
        k_starve=10,
        max_boost=3,
        floor=2
    )
    dur_ttca = (time.perf_counter() - t0) * 1000.0

    return {
        "normal": {**res_normal, "runtime_ms": dur_normal},
        "capped": {**res_capped, "runtime_ms": dur_capped},
        "continuous_k3": {**res_cont_k3, "runtime_ms": dur_cont_k3},
        "continuous_k5": {**res_cont_k5, "runtime_ms": dur_cont_k5},
        "continuous_k10": {**res_cont_k10, "runtime_ms": dur_cont_k10},
        "ttca": {**res_ttca, "runtime_ms": dur_ttca},
    }


def compute_mean_and_std(values: List[float]) -> Tuple[float, float]:
    if not values:
        return 0.0, 0.0
    mean = sum(values) / len(values)
    if len(values) == 1:
        return mean, 0.0
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return mean, math.sqrt(variance)


def run_comprehensive_evaluation():
    results_dir = os.path.dirname(__file__)

    # ---------------------------------------------------------
    # PART 1: Historical Fixed Workloads (seed 42 baseline)
    # ---------------------------------------------------------
    print("\n" + "=" * 100)
    print("PART 1: Historical Fixed Workloads Evaluation (Normal vs Capped vs Continuous K=5 vs TTCA)")
    print("=" * 100)

    fixed_workloads = generate_controlled_workloads()
    fixed_rows = []

    for name, data in fixed_workloads.items():
        eval_res = evaluate_workload(data)
        norm = eval_res["normal"]
        cap = eval_res["capped"]
        cont = eval_res["continuous_k5"]
        ttca = eval_res["ttca"]

        fixed_rows.append({
            "Workload": name,
            "Processes": len(data),
            "Normal Avg Waiting": f"{norm['average_waiting']:.2f}",
            "Capped Avg Waiting": f"{cap['average_waiting']:.2f}",
            "Cont_K5 Avg Waiting": f"{cont['average_waiting']:.2f}",
            "TTCA Avg Waiting": f"{ttca['average_waiting']:.2f}",
            "Normal Max Waiting": norm["maximum_waiting"],
            "Capped Max Waiting": cap["maximum_waiting"],
            "Cont_K5 Max Waiting": cont["maximum_waiting"],
            "TTCA Max Waiting": ttca["maximum_waiting"],
            "Normal Starved": norm["starved_processes"],
            "Capped Starved": cap["starved_processes"],
            "Cont_K5 Starved": cont["starved_processes"],
            "TTCA Starved": ttca["starved_processes"],
            "Capped Interventions": cap["aging_interventions"],
            "Cont_K5 Interventions": cont["aging_interventions"],
            "TTCA Interventions": ttca["aging_interventions"],
            "Normal Fairness": f"{norm['fairness']:.4f}",
            "Capped Fairness": f"{cap['fairness']:.4f}",
            "Cont_K5 Fairness": f"{cont['fairness']:.4f}",
            "TTCA Fairness": f"{ttca['fairness']:.4f}",
        })

        print(f"\n{name} (N={len(data)})")
        print(f"  Avg Wait:  Normal={norm['average_waiting']:.2f} | Capped={cap['average_waiting']:.2f} | Cont(K=5)={cont['average_waiting']:.2f} | TTCA={ttca['average_waiting']:.2f}")
        print(f"  Max Wait:  Normal={norm['maximum_waiting']} | Capped={cap['maximum_waiting']} | Cont(K=5)={cont['maximum_waiting']} | TTCA={ttca['maximum_waiting']}")
        print(f"  Starved:   Normal={norm['starved_processes']} | Capped={cap['starved_processes']} | Cont(K=5)={cont['starved_processes']} | TTCA={ttca['starved_processes']}")
        print(f"  Fairness:  Normal={norm['fairness']:.4f} | Capped={cap['fairness']:.4f} | Cont(K=5)={cont['fairness']:.4f} | TTCA={ttca['fairness']:.4f}")
        print(f"  Aging Adj: Capped={cap['aging_interventions']} | Cont(K=5)={cont['aging_interventions']} | TTCA={ttca['aging_interventions']}")

    # Save historical comparison
    hist_csv = os.path.join(results_dir, "continuous_aging_comparison.csv")
    with open(hist_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fixed_rows[0].keys()))
        writer.writeheader()
        writer.writerows(fixed_rows)
    print(f"\nSaved historical comparison to {hist_csv}")

    # ---------------------------------------------------------
    # PART 2: Statistical Multi-Trial Benchmark (30 seeds per scale)
    # ---------------------------------------------------------
    print("\n" + "=" * 100)
    print("PART 2: Independent Statistical Benchmark (30 trials per scale: Small, Medium, Large)")
    print("=" * 100)

    scales = [
        ("small", 10, range(100, 130)),
        ("medium", 50, range(200, 230)),
        ("large", 100, range(300, 330)),
    ]

    policies = ["normal", "capped", "continuous_k3", "continuous_k5", "continuous_k10", "ttca"]
    metrics_keys = [
        "average_waiting",
        "maximum_waiting",
        "average_turnaround",
        "average_response",
        "starved_processes",
        "protected_processes",
        "aging_interventions",
        "fairness",
        "waiting_disparity",
        "runtime_ms",
    ]

    summary_rows = []
    sensitivity_rows = []

    for scale_name, n_procs, seed_range in scales:
        print(f"\n--- Running 30 independent trials for {scale_name.upper()} scale (N={n_procs}) ---")

        scale_data: Dict[str, Dict[str, List[float]]] = {
            p: {m: [] for m in metrics_keys} for p in policies
        }

        for seed in seed_range:
            workload = generate_independent_workload(scale_name, seed)
            eval_res = evaluate_workload(workload)

            for p in policies:
                for m in metrics_keys:
                    scale_data[p][m].append(float(eval_res[p][m]))

            # Log sensitivity trial row
            sensitivity_rows.append({
                "Scale": scale_name,
                "Seed": seed,
                "Processes": n_procs,
                "Normal Avg Wait": eval_res["normal"]["average_waiting"],
                "Capped Avg Wait": eval_res["capped"]["average_waiting"],
                "Cont_K3 Avg Wait": eval_res["continuous_k3"]["average_waiting"],
                "Cont_K5 Avg Wait": eval_res["continuous_k5"]["average_waiting"],
                "Cont_K10 Avg Wait": eval_res["continuous_k10"]["average_waiting"],
                "TTCA Avg Wait": eval_res["ttca"]["average_waiting"],
                "Normal Max Wait": eval_res["normal"]["maximum_waiting"],
                "Capped Max Wait": eval_res["capped"]["maximum_waiting"],
                "Cont_K3 Max Wait": eval_res["continuous_k3"]["maximum_waiting"],
                "Cont_K5 Max Wait": eval_res["continuous_k5"]["maximum_waiting"],
                "Cont_K10 Max Wait": eval_res["continuous_k10"]["maximum_waiting"],
                "TTCA Max Wait": eval_res["ttca"]["maximum_waiting"],
                "Normal Starved": eval_res["normal"]["starved_processes"],
                "Capped Starved": eval_res["capped"]["starved_processes"],
                "Cont_K3 Starved": eval_res["continuous_k3"]["starved_processes"],
                "Cont_K5 Starved": eval_res["continuous_k5"]["starved_processes"],
                "Cont_K10 Starved": eval_res["continuous_k10"]["starved_processes"],
                "TTCA Starved": eval_res["ttca"]["starved_processes"],
                "Normal Fairness": eval_res["normal"]["fairness"],
                "Capped Fairness": eval_res["capped"]["fairness"],
                "Cont_K3 Fairness": eval_res["continuous_k3"]["fairness"],
                "Cont_K5 Fairness": eval_res["continuous_k5"]["fairness"],
                "Cont_K10 Fairness": eval_res["continuous_k10"]["fairness"],
                "TTCA Fairness": eval_res["ttca"]["fairness"],
            })

        # Calculate statistics across the 30 trials
        for p in policies:
            row = {
                "Scale": scale_name,
                "Processes": n_procs,
                "Policy": p,
                "Trials": len(seed_range),
            }
            for m in metrics_keys:
                mean_val, std_val = compute_mean_and_std(scale_data[p][m])
                row[f"{m}_mean"] = round(mean_val, 4)
                row[f"{m}_std"] = round(std_val, 4)
            summary_rows.append(row)

            print(
                f"[{scale_name.upper():6s} | {p:14s}] "
                f"Wait: {row['average_waiting_mean']:.2f} ± {row['average_waiting_std']:.2f} | "
                f"MaxWait: {row['maximum_waiting_mean']:.1f} ± {row['maximum_waiting_std']:.1f} | "
                f"Resp: {row['average_response_mean']:.2f} ± {row['average_response_std']:.2f} | "
                f"Fairness: {row['fairness_mean']:.4f} ± {row['fairness_std']:.4f}"
            )

    # Save statistical summary CSV
    summary_csv = os.path.join(results_dir, "continuous_statistical_summary.csv")
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"\nSaved statistical summary (30 trials/scale) to {summary_csv}")

    # Save sensitivity detailed CSV
    sens_csv = os.path.join(results_dir, "continuous_sensitivity_results.csv")
    with open(sens_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(sensitivity_rows[0].keys()))
        writer.writeheader()
        writer.writerows(sensitivity_rows)
    print(f"Saved sensitivity results to {sens_csv}\n")


if __name__ == "__main__":
    run_comprehensive_evaluation()
