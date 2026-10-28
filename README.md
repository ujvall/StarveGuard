# StarveGuard: Adaptive Process Starvation Detection and Aging-Based Prevention System

An Operating Systems CPU scheduling simulation and research framework that implements preemptive priority scheduling, detects thread starvation in the ready queue, and applies multi-tier adaptive aging to guarantee forward progress for lower-priority jobs.

---

## 1. Operating System Concepts & Scheduling Model

### Preemptive Priority Scheduling
In priority scheduling, each process is assigned an integer priority rank upon arrival. Under the convention implemented in this project:
- **Lower numerical value represents higher scheduling priority** (e.g., Priority 1 is the highest priority; Priority 10 is low priority).
- **Preemption:** At every discrete scheduling boundary (time quantum = 1), the scheduler evaluates all ready processes. If a process with a strictly higher priority (lower numerical value) is ready, the currently running process is preempted and returned to the ready queue.
- **Deterministic Tie-Breaking:** When two ready processes possess identical priority ranks:
  1. **Primary criterion:** Earliest arrival time (First-Come, First-Served / FCFS).
  2. **Secondary criterion:** Lexicographical process ID (`PID`, e.g., `"P1" < "P2"`).

### Process Execution Lifecycle
```
[Unarrived] ──(arrival_time <= t)──> [Ready Queue] ──(highest priority)──> [Running on CPU]
                                            ▲                                      │
                                            │──────(preempted or time slice)───────│
                                            │                                      ▼
                                     [Dynamic Aging]                 (remaining_time == 0)
                                    (evaluates score)                              │
                                                                                   ▼
                                                                              [Completed]
```
1. **Arrival & Readiness:** A process enters the ready queue when simulation time $t \ge \text{arrival\_time}$.
2. **Dispatch & Response:** The process's first execution time is recorded as `first_run_time`. Its **Response Time** is calculated exactly once:
   $$\text{Response Time} = \text{first\_run\_time} - \text{arrival\_time}$$
3. **Execution & Preemption:** Remaining burst time is decremented per unit. If preempted by a higher-priority arrival or an aged process, the process returns to the ready queue.
4. **Completion & Consistency:** When `remaining_time == 0`, completion time ($CT$) is recorded:
   $$\text{Turnaround Time} = CT - \text{arrival\_time}$$
   $$\text{Waiting Time} = \text{Turnaround Time} - \text{burst\_time}$$
   The implementation strictly verifies the invariant $\text{Waiting Time} = \text{Turnaround Time} - \text{burst\_time}$ across all lifecycles.
5. **Idle Time Tracking:** When the ready queue is empty, the scheduler explicitly advances the clock and logs an `"IDLE"` timeline slice, preserving timeline continuity in Gantt visualizers.

---

## 2. Starvation Detection & Scoring Formula

### Academic Audit & Formulation
In standard priority scheduling, lower-priority threads can be indefinitely starved if higher-priority jobs continually arrive. Schedulers mitigate this via starvation tracking.

The starvation score formula is:
$$\text{Starvation Score} = \text{Waiting Time} + (\text{Bypass Count} \times \text{bypass\_weight})$$

- **Waiting Time ($W_p$):** Cumulative discrete clock cycles spent by process $p$ in the ready queue without CPU allocation.
- **Bypass Count ($B_p$):** The number of scheduling dispatch decisions that selected another process while process $p$ was waiting in the ready queue.
- **Score Simplification:** In a single-core discrete simulation, incrementing both waiting time and bypass count every clock tick leads to double-counting the same event. In StarveGuard, `bypass_weight` defaults to `0`, directly equating the starvation score to queue waiting time ($W_p$), which provides the standard, uninflated Operating Systems metric for starvation. If `bypass_weight > 0` is explicitly configured, dispatch bypasses add weighted penalty.
- **Starvation Threshold ($\theta = 20$):** When $\text{Score} \ge 20$, the process is formally flagged as having crossed the starvation threshold. This status records an internal starvation alert; it does not indicate permanent deadlock, because StarveGuard's aging engine intervenes to restore CPU allocation.

---

## 3. Multi-Tier Adaptive Aging Policy

To prevent indefinite starvation without destroying priority hierarchies, StarveGuard applies a tiered priority boost:

| Starvation Score (Waiting Duration) | Aging Tier | Priority Boost ($\Delta$) | Effective Priority Formula | Scheduling Status |
| :---: | :---: | :---: | :--- | :--- |
| **0 – 9** | Tier 0 | `0` | $\text{priority} = \text{original\_priority}$ | Normal execution |
| **10 – 19** | Tier 1 | `+1` | $\text{priority} = \max(1, \text{original\_priority} - 1)$ | Moderate wait; minor boost |
| **20 – 29** | Tier 2 | `+2` | $\text{priority} = \max(1, \text{original\_priority} - 2)$ | **Starvation flagged ($\theta \ge 20$)** |
| **30+** | Tier 3 | `+3` | $\text{priority} = \max(1, \text{original\_priority} - 3)$ | Severe wait; maximum boost |

### Theoretical Properties & Boundaries
1. **Anchored to Original Priority:** The boost is subtracted from `original_priority`, not compounding from `current_priority`. This prevents runaway escalation where a process collapses permanently to priority 1.
2. **Floor of 1:** The effective priority cannot drop below numerical value 1 (the highest possible priority). A process with initial priority 1 remains at priority 1.
3. **Reachability and Bounded-Waiting Limits:**
   Because the maximum boost is $+3$, a process with initial priority 8 can reach at most priority 5. If processes with priorities 1 through 4 continually arrive, a priority-8 process can still experience starvation. Thus, strict bounded waiting is guaranteed under the condition that arriving processes have priorities within the reach of the boosted tier ($\text{arrival priority} \ge \text{original\_priority} - 3$).

---

## 4. Architectural Comparison

| Dimension | Normal Priority Scheduler | StarveGuard Priority Scheduler |
| :--- | :---: | :---: |
| **Implementation** | `scheduler.normal_priority_scheduler` | `scheduler.priority_scheduler` |
| **Preemption Model** | Preemptive per discrete time unit | Preemptive per discrete time unit |
| **Priority Handling** | Static (Fixed rank throughout life) | Dynamic (Multi-tier aging evaluated at each tick) |
| **Dispatch Bypass Tracking** | Yes (`bypass_count` on dispatch switch) | Yes (`bypass_count` on dispatch switch) |
| **Starvation Alerting** | None (Processes starve silently) | Explicit ($\text{Score} \ge 20$, threshold crossing log) |
| **Idle Period Logging** | Yes (`"IDLE"` time slices recorded) | Yes (`"IDLE"` time slices recorded) |
| **Audit Log** | None | Timestamped transition log `(t, pid, old, new, score)` |
| **Fairness Evaluation** | Post-simulation (Jain's index & WT spread) | Post-simulation (Jain's index & WT spread) |

---

## 5. Experimental Benchmark Results

Experiments were conducted across controlled, reproducible workloads using deterministic seeds (`seed=42`).

### Summary of Benchmark Runs (`results/workload_results.csv`)

| Workload Scenario | $N$ | Normal Wait | SG Wait | Normal Resp | SG Resp | Normal Fairness | SG Fairness | Starved | Protected | Aging Interventions |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Workload 1 (Classic Starvation)** | 3 | 15.00 | 15.00 | 15.00 | 15.00 | 0.583 | 0.583 | 2 | 2 | 4 |
| **Workload 2 (Staggered Arrivals)** | 4 | 6.25 | 6.25 | 5.25 | 5.25 | 0.765 | 0.765 | 0 | 2 | 2 |
| **Workload 3 (Long-Burst Starvation)** | 3 | 23.33 | 23.33 | 23.33 | 23.33 | 0.636 | 0.636 | 2 | 2 | 6 |
| **Workload 4 (Sequential Non-Contested)** | 3 | 0.00 | 0.00 | 0.00 | 0.00 | 1.000 | 1.000 | 0 | 0 | 0 |
| **Small Scale (High Contention)** | 10 | 7.60 | 8.40 | 4.50 | **3.10 (-31%)** | 0.892 | 0.883 | 2 | 2 | 6 |
| **Medium Scale (Skewed Arrivals)** | 50 | 104.90 | **104.20 (-0.7%)** | 98.36 | 100.36 | 0.399 | **0.418 (+4.8%)** | 39 | 39 | 97 |
| **Large Scale (Multi-tier 100 Jobs)** | 100 | 278.81 | 294.23 | 274.85 | 290.40 | 0.315 | 0.224 | 95 | 86 | 218 |

### Academic Analysis of Trade-offs
1. **Response Time Improvement in Contended Systems:** In the 10-process contention workload, StarveGuard cut average response time from **4.50 to 3.10 (-31.1%)** by elevating starving processes before they suffered prolonged initial dispatch delay.
2. **Fairness Improvement in Skewed Systems:** In the 50-process medium workload, Jain's Fairness Index improved from **0.399 to 0.418 (+4.8%)**, and 39 starving jobs were protected through 97 aging interventions.
3. **System-Level Trade-offs:** In saturated, heavy-tail workloads (Large Scale 100 jobs), elevating long-burst lower-priority jobs preempts newly arrived higher-priority jobs. This increases the average waiting time across all 100 jobs (278.81 vs. 294.23 ticks) while successfully preventing any single low-priority job from experiencing unbounded starvation.

---

## 6. Performance & Fairness Metrics

Calculated via `metrics/calculator.py`:

- **Jain's Fairness Index:** Evaluates equity of normalized service efficiency across all jobs:
  $$J(x_1, \dots, x_n) = \frac{\left(\sum_{i=1}^n x_i\right)^2}{n \cdot \sum_{i=1}^n x_i^2}, \quad x_i = \frac{\text{burst\_time}_i}{\text{turnaround\_time}_i}$$
  *(1.0 denotes equal execution efficiency; lower values reflect starvation imbalance).*
- **Waiting Time Disparity:** Measures spread between longest and shortest waiting times:
  $$\text{Disparity} = \max(WT) - \min(WT)$$
- **Average Waiting Time ($AWT$):** $\frac{1}{n} \sum WT_i$.
- **Average Turnaround Time ($ATAT$):** $\frac{1}{n} \sum TAT_i$.
- **Average Response Time ($ART$):** $\frac{1}{n} \sum RT_i$.

---

## 7. Project Structure

```
StarveGuard/
├── aging/                      # Multi-tier priority boost and aging manager
│   └── aging_manager.py
├── comparison/                 # Dual scheduler comparator running identical inputs
│   └── comparator.py
├── metrics/                    # Performance, disparity, and Jain's fairness metrics
│   └── calculator.py
├── results/                    # Benchmark results, CSV summaries, and Matplotlib plots
│   ├── baseline_workload_results.csv   # Preserved original pre-audit baseline
│   ├── workload_results.csv            # Verified multi-scale experimental results
│   ├── benchmark_experiments.py       # Deterministic workload generator & runner
│   ├── generate_graphs.py             # Headless Matplotlib chart generator
│   └── summary.py                     # Formatted CLI summary table
├── scheduler/                  # Core scheduling infrastructure
│   ├── process.py                      # Process dataclass and state lifecycle
│   ├── normal_priority_scheduler.py   # Baseline preemptive priority scheduler
│   ├── priority_scheduler.py          # StarveGuard adaptive priority scheduler
│   └── gantt.py                       # Gantt chart segment extraction and ASCII renderer
├── tests/                      # Full unittest regression test suite (34 tests)
│   ├── test_process.py
│   ├── test_detector.py
│   ├── test_aging.py
│   ├── test_aging_prevention.py
│   ├── test_normal_priority.py
│   ├── test_scheduler.py
│   ├── test_metrics.py
│   ├── test_comparison.py
│   ├── test_demo.py
│   ├── test_starvation.py
│   ├── test_workloads.py
│   └── test_regression.py             # Rigorous coverage of all 16 audit edge cases
├── ui/                         # Tkinter desktop GUI dashboard
│   └── app.py
├── main.py                     # Interactive and non-interactive CLI runner
└── README.md                   # Technical documentation
```

---

## 8. Getting Started & Reproducibility

### Prerequisites
- **Python 3.10+** (standard libraries: `tkinter`, `dataclasses`, `csv`, `random`).
- **Matplotlib** (for generating chart images in `results/`):
  ```bash
  pip install matplotlib
  ```

### Running the Test Suite
Run the complete regression suite using Python's standard `unittest` framework:
```bash
python -m unittest discover tests
```
*(34 tests covering all 16 edge cases should execute and pass with `OK`).*

### Running the Benchmark Suite
To regenerate the multi-scale benchmark CSV and formatted terminal summary:
```bash
python results/benchmark_experiments.py
python results/summary.py
```

### Generating Benchmark Comparison Plots
```bash
python results/generate_graphs.py
```
Outputs:
- `results/average_waiting_comparison.png`
- `results/average_response_comparison.png`
- `results/fairness_comparison.png`

### Running the Desktop GUI
```bash
python ui/app.py
```
*Click **Load Demo Workload** then **Run Simulation** to view dual Gantt charts, process metrics, and chronological aging logs.*

### Running via CLI
```bash
# Interactive mode:
python main.py

# Automated demonstration mode:
python main.py --demo
```

---

## 9. Assumptions, Scope & Limitations

1. **Uniprocessor Scope:** The scheduling engine models a single execution core. Multi-core scheduling with processor affinity is outside project scope.
2. **Discrete Time Quantum:** Time is modeled in integer quanta ($\Delta t = 1$), representing CPU clock cycles.
3. **Maximum Aging Ceiling:** Because the aging boost ceiling is $+3$, processes with very low base priorities ($\ge 8$) cannot overtake apex processes (priorities 1–4) under constant high-priority arrival streams.
