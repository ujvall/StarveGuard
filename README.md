# StarveGuard: Adaptive Process Starvation Detection and Aging-Based Prevention System

An Operating Systems CPU scheduling simulation and research framework that implements preemptive priority scheduling, detects thread starvation in the ready queue, and applies multi-tier adaptive aging to mitigate starvation for lower-priority jobs.

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
   The implementation strictly verifies the conservation invariant $\text{Waiting Time} = \text{Turnaround Time} - \text{burst\_time}$ across all lifecycles.
5. **Idle Time Tracking:** When the ready queue is empty, the scheduler explicitly advances the clock and logs an `"IDLE"` timeline slice, preserving timeline continuity in Gantt visualizers.

---

## 2. Starvation Detection & Scoring Formula

### Formulation and Academic Scope
In standard priority scheduling, lower-priority threads can be starved if higher-priority jobs continually arrive. StarveGuard monitors ready queue states to detect this condition.

The starvation score formula is:
$$\text{Starvation Score} = \text{Waiting Time} + (\text{Bypass Count} \times \text{bypass\_weight})$$

- **Waiting Time ($W_p$):** Cumulative discrete clock cycles spent by process $p$ in the ready queue without CPU allocation.
- **Bypass Count ($B_p$):** The number of scheduling dispatch switch events that selected another process while process $p$ was waiting in the ready queue.
- **Score Weighting:** In a single-core discrete simulation, incrementing both waiting time and bypass count every clock tick leads to redundant double-counting. In StarveGuard, `bypass_weight` defaults to `0`, directly equating the starvation score to queue waiting time ($W_p$), which provides the standard, uninflated Operating Systems metric for starvation. If `bypass_weight > 0` is explicitly configured, dispatch bypass switches add weighted penalty.
- **Starvation Threshold ($\theta = 20$):** When $\text{Score} \ge 20$, the process is formally flagged as having crossed the starvation threshold (`starvation_detected = True`).
- **Threshold-Crossing vs. Permanent Starvation:** A process crossing this threshold is recorded as a *threshold-crossing process*. This metric logs that the process experienced starvation-level wait times during its queue life; it does **not** indicate that the process remained permanently starved or deadlocked, because StarveGuard's aging mechanism intervenes to grant CPU time.

---

## 3. Multi-Tier Adaptive Aging Policy

To mitigate starvation risk without collapsing priority hierarchies, StarveGuard applies a tiered priority boost:

| Starvation Score (Waiting Duration) | Aging Tier | Priority Boost ($\Delta$) | Effective Priority Formula | Scheduling Status |
| :---: | :---: | :---: | :--- | :--- |
| **0 – 9** | Tier 0 | `0` | $\text{priority} = \text{original\_priority}$ | Normal execution |
| **10 – 19** | Tier 1 | `+1` | $\text{priority} = \max(1, \text{original\_priority} - 1)$ | Moderate wait; minor boost |
| **20 – 29** | Tier 2 | `+2` | $\text{priority} = \max(1, \text{original\_priority} - 2)$ | **Starvation flagged ($\theta \ge 20$)** |
| **30+** | Tier 3 | `+3` | $\text{priority} = \max(1, \text{original\_priority} - 3)$ | Severe wait; maximum boost ceiling |

### Theoretical Properties & Reachability Limitations
1. **Anchored to Original Priority:** The boost is subtracted from `original_priority`, avoiding compounding runaway escalation where processes collapse permanently to priority 1.
2. **Floor of 1:** The effective priority cannot drop below numerical value 1 (the highest possible priority). A process with initial priority 1 remains at priority 1.
3. **Maximum Boost Ceiling and Starvation Mitigation Limits:**
   - The maximum aging boost under the current policy is capped at $+3$.
   - **StarveGuard does not guarantee starvation elimination under all possible workloads.** For example, a process with base priority 8 can reach at most priority 5 ($8 - 3 = 5$). If processes with priorities 1 through 4 continually arrive in an unbroken stream, the priority-8 process will remain unserved until the high-priority queues empty. Strict bounded waiting is guaranteed only when arriving processes have priorities within the reach of the boosted tier ($\text{arriving priority} \ge \text{original\_priority} - 3$).

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

### Methodology and Workload Scope
- **Workload Generation:** The Small (10 processes), Medium (50 processes), and Large (100 processes) benchmarks are **deterministic synthetic workload instances** generated using Python's pseudo-random number generator with a fixed seed (`seed=42`).
- **Single-Instance Representation:** Each benchmark scale currently represents a **single generated instance**, not a Monte Carlo average, aggregated ensemble, or statistical study across repeated independent trials.
- **Scope of Claims:** The results demonstrate behavior on these specific tested instances only. They do not establish universal superiority across arbitrary, uncharacterized operating environments.

### Benchmark Data (`results/workload_results.csv`)

| Workload Scenario | $N$ | Normal Wait | SG Wait | Normal Resp | SG Resp | Normal Fairness | SG Fairness | Starved | Protected | Aging Interventions |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Workload 1 (Classic Starvation)** | 3 | 15.00 | 15.00 | 15.00 | 15.00 | 0.583 | 0.583 | 2 | 2 | 4 |
| **Workload 2 (Staggered Arrivals)** | 4 | 6.25 | 6.25 | 5.25 | 5.25 | 0.765 | 0.765 | 0 | 2 | 2 |
| **Workload 3 (Long-Burst Starvation)** | 3 | 23.33 | 23.33 | 23.33 | 23.33 | 0.636 | 0.636 | 2 | 2 | 6 |
| **Workload 4 (Sequential Non-Contested)** | 3 | 0.00 | 0.00 | 0.00 | 0.00 | 1.000 | 1.000 | 0 | 0 | 0 |
| **Small Scale (High Contention)** | 10 | 7.60 | 8.40 | 4.50 | 3.10 | 0.892 | 0.883 | 2 | 2 | 6 |
| **Medium Scale (Skewed Arrivals)** | 50 | 104.90 | 104.20 | 98.36 | 100.36 | 0.399 | 0.418 | 39 | 39 | 97 |
| **Large Scale (Multi-tier 100 Jobs)** | 100 | 278.81 | 294.23 | 274.85 | 290.40 | 0.315 | 0.224 | 95 | 86 | 218 |

### Academic Analysis of Trade-offs & Limitations
1. **Instance-Specific Response Time Reduction:** In the tested 10-process contention instance, StarveGuard reduced average response time from 4.50 to 3.10 (-31.1%) by elevating starved low-priority processes before long initial dispatch delays accrued. This behavior is specific to the arrival timing of this instance and should not be generalized to all contention patterns.
2. **Medium-Scale Fairness Improvement:** In the 50-process medium workload instance, Jain's fairness index increased from 0.399 to 0.418 (+4.8%), with 39 processes crossing the starvation threshold and receiving 97 aging interventions.
3. **Large-Scale Latency and Fairness Degradation (System Trade-off):** In the 100-process large workload instance:
   - Average waiting time **increased** from 278.81 to 294.23 ticks (+5.5%).
   - Jain's fairness index **decreased** from 0.315 to 0.224 (-28.8%).
   - Maximum waiting time was unchanged at 1011 ticks.
   *Reason for degradation:* Elevating 86 long-burst lower-priority processes preempted newly arriving short, high-priority processes. This lengthened the turnaround time of short interactive jobs, thereby reducing their efficiency ratios ($x_i$) and lowering the overall fairness index. This represents a fundamental OS scheduling trade-off: mitigating indefinite starvation for batch jobs imposes preemption latency on high-priority arrivals and reduces efficiency equality across heterogeneous workloads.

---

## 6. Performance & Fairness Metrics

Calculated via `metrics/calculator.py`:

- **Jain's Fairness Index:** Evaluates equity of normalized service efficiency across all jobs:
  $$J(x_1, \dots, x_n) = \frac{\left(\sum_{i=1}^n x_i\right)^2}{n \cdot \sum_{i=1}^n x_i^2}, \quad x_i = \frac{\text{burst\_time}_i}{\text{turnaround\_time}_i}$$
  *Metric Scope & Limitations:* Because $x_i$ reflects the fraction of in-system lifetime spent actively computing, jobs with short bursts that wait behind long tasks receive small ratios. This metric evaluates the equality of *execution efficiency ratios*, rather than the equality of raw CPU time allocations. If short jobs are preempted by aged batch jobs, $J$ decreases even though lower-priority jobs gained forward progress.
- **Waiting Time Disparity:** Measures direct spread between longest and shortest waiting times:
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
├── tests/                      # Full unittest regression test suite (37 tests)
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
*(37 tests covering all 16 edge cases and exact hand-calculated assertions should execute and pass with `OK`).*

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
*Note on GUI Testing: Automated testing verified successful module import, widget instantiation, style loading, and event registration. Full interactive manual verification requires a desktop environment.*

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
2. **Discrete Time Quantum:** Time is modeled in integer quanta ($\Delta t = 1$), representing discrete clock cycles.
3. **Maximum Aging Ceiling:** Because the aging boost ceiling is $+3$, processes with very low base priorities ($\ge 8$) cannot overtake apex processes (priorities 1–4) under constant high-priority arrival streams.
4. **Single-Trial Benchmark Representation:** The multi-scale experiments evaluate single deterministic synthetic instances generated with seed 42. Statistical characterization across diverse arrival distributions remains future work.
