# StarveGuard: Adaptive Process Starvation Detection and Aging-Based Prevention System

An Operating Systems CPU scheduling simulation and research framework that implements preemptive priority scheduling, detects thread starvation in the ready queue, and evaluates multi-tier capped aging, continuous waiting-time-based aging, and threshold-triggered conservative aging (TTCA) with apex isolation.

---

## 1. Project Overview & Motivation

In traditional preemptive priority scheduling, lower-priority processes are susceptible to **starvation** (indefinite postponement) when higher-priority processes arrive continuously. While dynamic aging algorithms are designed to elevate starved processes, naive implementations can cause severe collateral damage:
- **Runaway Escalation:** Low-priority batch jobs with long bursts reach top priority, monopolizing the CPU.
- **Throughput Inversion:** Arriving short, interactive tasks are blocked behind aged long-running jobs, causing average system waiting and response times to blow up by +70% to +85%.
- **Cascading Starvation:** Delaying interactive jobs pushes dozens of previously healthy processes across the starvation threshold.

**StarveGuard** addresses these fundamental operating systems challenges by modeling, measuring, and comparing four distinct scheduling policies under mathematically rigorous conditions:
1. **Normal Preemptive Priority Scheduling:** Unmodified baseline with static priorities.
2. **Multi-Tier Capped Aging:** Stepwise $+3$ priority boost ceiling anchored to original priority.
3. **Continuous Waiting-Time-Based Aging:** Floor-bounded dynamic aging ($K=5$) eliminating artificial boost caps.
4. **Threshold-Triggered Conservative Aging (TTCA):** Latency-neutral aging with apex isolation, intervening only when starvation occurs while protecting top-priority tasks.

---

## 2. Process Lifecycle & Starvation Detection Model

### 2.1 Discrete Preemptive Execution Model
All schedulers operate on discrete single-core clock cycles ($t \in \mathbb{N}_{\ge 0}$):
1. **Arrival & Queue Enqueue:** Arriving processes enter the ready queue at `arrival_time`.
2. **Dispatch & Response:** The process's first execution time is recorded as `first_run_time`. Its **Response Time** is calculated exactly once:
   $$\text{Response Time} = \text{first\_run\_time} - \text{arrival\_time}$$
3. **Execution & Preemption:** Remaining burst time is decremented per unit. If preempted by a higher-priority arrival or an aged process, the process returns to the ready queue.
4. **Completion & Invariants:** When `remaining_time == 0`, completion time ($CT$) is recorded:
   $$\text{Turnaround Time} = CT - \text{arrival\_time}$$
   $$\text{Waiting Time} = \text{Turnaround Time} - \text{burst\_time}$$
   The implementation strictly verifies the conservation invariant $\text{Waiting Time} = \text{Turnaround Time} - \text{burst\_time}$ across all lifecycles.
5. **Deterministic Tie-Breaking:** If two ready processes share identical effective priorities, ties are resolved strictly by **earliest arrival time** (First-Come, First-Served). If arrival times also match, ties are broken by **lexicographical process identifier** (`process_id`).

### 2.2 Starvation Metric & Threshold Model
At every clock tick $t$, StarveGuard evaluates waiting processes in the ready queue:
$$\text{Starvation Score} = \text{Waiting Time} + (\text{Bypass Count} \times \text{bypass\_weight})$$

- **Waiting Time ($W_p$):** Cumulative clock ticks spent ready in the queue without CPU allocation (`process.waiting_time`).
- **Bypass Count ($B_p$):** The number of scheduling dispatch switch events that selected another process while process $p$ was waiting in the ready queue.
- **Score Weighting:** In a single-core discrete simulation, incrementing both waiting time and bypass count every clock tick leads to redundant double-counting. In StarveGuard, `bypass_weight` defaults to `0`, directly equating the starvation score to queue waiting time ($W_p$), which provides the standard, uninflated Operating Systems metric for starvation. If `bypass_weight > 0` is explicitly configured, dispatch bypass switches add weighted penalty.
- **Starvation Threshold ($\theta = 20$):** When $\text{Score} \ge 20$, the process is formally flagged as having crossed the starvation threshold (`starvation_detected = True`).
- **Threshold-Crossing vs. Permanent Starvation:** A process crossing this threshold is recorded as a *threshold-crossing process*. This metric logs that the process experienced starvation-level wait times during its queue life; it does **not** indicate that the process remained permanently starved or deadlocked, because StarveGuard's aging mechanisms intervene to grant CPU time.

---

## 3. Aging Policies & Mathematical Formulations

StarveGuard provides three independent, configurable aging policies:

### Policy A: Original Multi-Tier Capped Aging (`policy="capped"`)
The baseline policy uses a tiered step function capped at a maximum priority boost of $+3$:

| Starvation Score (Waiting Duration) | Aging Tier | Priority Boost ($\Delta$) | Effective Priority Formula | Scheduling Status |
| :---: | :---: | :---: | :--- | :--- |
| **0 – 9** | Tier 0 | `0` | $P^{eff} = P^{base}$ | Normal execution |
| **10 – 19** | Tier 1 | `+1` | $P^{eff} = \max(1, P^{base} - 1)$ | Moderate wait; minor boost |
| **20 – 29** | Tier 2 | `+2` | $P^{eff} = \max(1, P^{base} - 2)$ | **Starvation flagged ($\theta \ge 20$)** |
| **30+** | Tier 3 | `+3` | $P^{eff} = \max(1, P^{base} - 3)$ | Severe wait; maximum boost ceiling |

*Limitation:* Because the boost ceiling is $+3$, a process with base priority 8 can reach at most priority 5 ($8 - 3 = 5$). If processes with priorities 1 through 4 continually arrive in an unbroken stream, the priority-8 process cannot gain CPU access until the higher-priority queues empty.

### Policy B: Continuous Waiting-Time-Based Aging (`policy="continuous"`)
To eliminate the artificial ceiling and guarantee that any long-waiting process can eventually compete with the highest-priority tasks, StarveGuard implements continuous aging with a priority floor of 1:

$$P_i^{eff}(t) = \max\left(1,\ P_i^{base} - \left\lfloor\frac{W_i(t)}{K}\right\rfloor\right)$$

Where:
- $P_i^{eff}(t)$: Effective priority evaluated at each scheduling decision boundary.
- $P_i^{base}$: Original base priority (`process.original_priority`), which remains **strictly immutable**.
- $W_i(t)$: Cumulative clock ticks spent ready in the queue without CPU allocation (`process.waiting_time`).
- $K$: Waiting-time interval required for one integer priority rank improvement (default candidate: $K = 5$).
- $\text{Floor} = 1$: Effective priority is bounded below at 1 (the highest possible priority).

*Trade-Off Dilemma:* Unrestricted continuous aging allows low-priority batch jobs with large CPU bursts to elevate to Priority 1, monopolizing the CPU and forcing incoming short, interactive tasks to wait. In Medium workloads ($N=50$), mean waiting time surges from $109.13 \to 188.27$ ticks (+72.5%), and in Large workloads ($N=100$), it escalates from $253.53 \to 464.69$ ticks (+83.3%).

### Policy C: Threshold-Triggered Conservative Aging (TTCA) (`policy="conservative"` or `policy="ttca"`)
To prevent the severe latency degradation caused by unconstrained continuous aging while still providing reliable starvation protection, StarveGuard introduces **Threshold-Triggered Conservative Aging (TTCA)** with **Apex Isolation**.

#### Mathematical Formulation
$$\Delta_i(t) = \begin{cases} 0 & \text{if } W_i(t) < \theta \\ \min\left(M,\ 1 + \left\lfloor \frac{W_i(t) - \theta}{K_{starve}} \right\rfloor \right) & \text{if } W_i(t) \ge \theta \end{cases}$$

$$P_i^{eff}(t) = \max\left(P^{floor}(P_i^{base}),\ P_i^{base} - \Delta_i(t)\right)$$

#### Apex Isolation Floor Function
$$P^{floor}(P_i^{base}) = \begin{cases} 1 & \text{if } P_i^{base} = 1 \\ 2 & \text{if } P_i^{base} > 1 \end{cases}$$

#### Default Parameters
- Starvation Threshold: $\theta = 20$ ticks.
- Starvation Aging Step: $K_{starve} = 10$ ticks.
- Maximum Boost Ceiling: $M = 3$ ranks.
- Priority Floor: $P^{floor} = 1$ for base priority 1; $P^{floor} = 2$ for all other processes.

#### Stepwise Priority Boost Progression Table
| Cumulative Waiting Time ($W_i$) | Starvation Condition | Aging Boost ($\Delta_i$) | Effective Priority ($P_i^{base} > 1$) | Effective Priority ($P_i^{base} = 1$) | Policy Status |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **$0 \le W_i < 20$** | $W_i < \theta$ | `0` | $P_i^{base}$ | `1` | Inactive; 100% normal priority preserved |
| **$20 \le W_i < 30$** | $\theta \le W_i < \theta + K$ | `+1` | $\max(2, P_i^{base} - 1)$ | `1` | Starvation detected; first conservative boost |
| **$30 \le W_i < 40$** | $\theta + K \le W_i < \theta + 2K$ | `+2` | $\max(2, P_i^{base} - 2)$ | `1` | Continued starvation; second boost |
| **$W_i \ge 40$** | $W_i \ge \theta + 2K$ | `+3` | $\max(2, P_i^{base} - 3)$ | `1` | Maximum boost ceiling ($M=3$) reached |

#### Theoretical Properties & Engineering Rationale
1. **Zero-Overhead Invariance:** If no process waits $\ge 20$ ticks, $\Delta_i(t) = 0$ for all processes. TTCA produces scheduling schedules **100% bitwise identical** to Normal Priority scheduling.
2. **Apex Isolation:** Critical real-time or apex interactive processes ($P_i^{base} = 1$) can **never be preempted** by aged lower-priority batch jobs. Because $P^{floor} = 2$ for any process with $P_i^{base} > 1$, top-tier priority integrity is strictly guaranteed.
3. **Prevention of Head-of-Line Cascades:** Because aged batch jobs cannot enter Priority 1, they cannot block incoming Priority 1 tasks. This prevents the head-of-line blocking cascade that degraded continuous aging performance.
4. **Controlled Starvation Mitigation:** Non-apex jobs still receive up to 3 priority boosts when starved, allowing them to preempt intermediate priority tiers (priorities 3 through 10) and complete their execution.
5. **Architectural Limitation:** Under an unbroken, 100% saturating stream of genuine Priority 1 jobs ($\lambda_1 \cdot E[B_1] \ge 1$), processes with $P_i^{base} > 1$ cannot preempt them even at their maximum boost ($P^{eff} = 2$). This is a deliberate, mathematically sound design compromise: apex latency is protected at the cost of deferring lower-priority execution until the Priority 1 saturation ceases.

---

## 4. Architectural Comparison

| Dimension | Normal Priority Scheduler | StarveGuard (Capped Aging) | StarveGuard (Continuous Aging) | StarveGuard (TTCA Conservative) |
| :--- | :---: | :---: | :---: | :---: |
| **Implementation** | `scheduler.normal_priority_scheduler` | `scheduler.priority_scheduler` | `scheduler.priority_scheduler` | `scheduler.priority_scheduler` |
| **Preemption Model** | Preemptive per discrete tick | Preemptive per discrete tick | Preemptive per discrete tick | Preemptive per discrete tick |
| **Aging Activation** | Never active | Immediate from $W \ge 10$ | Immediate from $W \ge K$ | **Delayed until $W \ge \theta$ (20 ticks)** |
| **Priority Handling** | Static ($P^{eff} = P^{base}$) | Tiered (Max $+3$ boost) | Continuous ($\lfloor W/K \rfloor$ boost) | **Conservative Tiered (Max $+3$ boost)** |
| **Priority Floor** | Natural base priority | $\max(1, P^{base} - 3)$ | $\max(1, P^{base} - \lfloor W/K \rfloor) = 1$ | **Apex Isolated: 1 for $P^{base}=1$, 2 for $P^{base}>1$** |
| **Apex Protection** | Natural | None (Aged jobs reach 1) | None (Aged jobs reach 1) | **Strictly Guaranteed ($P^{floor}=2$)** |
| **Healthy Workload Invariance** | True baseline | May intervene at $W \ge 10$ | Intervenes at $W \ge K$ | **100% Identical to Normal Priority** |
| **Starvation Alerting** | None (Starves silently) | Explicit ($\text{Score} \ge 20$) | Explicit ($\text{Score} \ge 20$) | **Explicit ($\text{Score} \ge 20$)** |
| **Idle Period Logging** | Yes (`"IDLE"` slices recorded) | Yes (`"IDLE"` slices recorded) | Yes (`"IDLE"` slices recorded) | **Yes (`"IDLE"` slices recorded)** |
| **Audit Log** | None | Timestamped transition log | Timestamped transition log | **Timestamped transition log** |
| **Fairness Evaluation** | Post-simulation (Jain's index) | Post-simulation (Jain's index) | Post-simulation (Jain's index) | **Post-simulation (Jain's index)** |

---

## 5. Experimental Evaluation & Statistical Benchmarks

### 5.1 Historical Fixed Workloads (Seed 42 Baseline)
Direct empirical comparison of all four scheduling policies across the standard benchmark suite (`results/continuous_aging_comparison.csv`):

| Workload Scenario | $N$ | Normal Wait | Capped Wait | Cont ($K=5$) Wait | TTCA Wait | Normal Max Wait | Capped Max Wait | Cont ($K=5$) Max Wait | TTCA Max Wait | Normal Fairness | Capped Fairness | Cont ($K=5$) Fairness | TTCA Fairness |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Workload 1 (Classic Starvation)** | 3 | 15.00 | 15.00 | 15.00 | 15.00 | 25 | 25 | 25 | 25 | 0.5831 | 0.5831 | **0.6757** | 0.5831 |
| **Workload 2 (Staggered Arrivals)** | 4 | 6.25 | 6.25 | 6.25 | 6.25 | 11 | 11 | 11 | 11 | 0.7653 | 0.7653 | 0.7653 | 0.7653 |
| **Workload 3 (Long-Burst Starvation)** | 3 | 23.33 | 23.33 | 25.00 | 23.33 | 40 | 40 | **35** | 40 | 0.6357 | 0.6357 | **0.8552** | 0.6357 |
| **Workload 4 (Sequential Non-Contested)** | 3 | 0.00 | 0.00 | 0.00 | 0.00 | 0 | 0 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **Small Scale (10 procs - Contention)** | 10 | 7.60 | 8.40 | 9.70 | 9.40 | 44 | 44 | 47 | 44 | 0.8920 | 0.8833 | 0.8722 | 0.8744 |
| **Medium Scale (50 procs - Skewed)** | 50 | 104.90 | 104.20 | 188.76 | **102.74** | 393 | 393 | 405 | 393 | 0.3994 | 0.4184 | 0.3174 | 0.3754 |
| **Large Scale (100 procs - Multi-tier)** | 100 | 278.81 | 294.23 | 503.38 | **297.19** | 1011 | 1011 | **975** | 1011 | 0.3148 | 0.2242 | 0.1446 | 0.2331 |

*Observations:*
- In Workload 2 ($W_{max} = 11 < 20$) and Workload 4 ($W_{max} = 0$), TTCA triggered **0 aging interventions**, executing exactly identical to Normal Priority scheduling.
- In Medium Scale, TTCA achieved an average waiting time of **102.74 ticks** (beating Normal Priority's 104.90 ticks), completely avoiding Continuous Aging's blowout to 188.76 ticks.
- In Large Scale, TTCA preserved average waiting at **297.19 ticks** (+6.59% over Normal Priority), compared to Continuous Aging's 503.38 ticks (+80.5%).

### 5.2 Independent Multi-Trial Statistical Benchmark
StarveGuard was evaluated across **30 independent synthetic workloads per scale** (90 total workloads) with distinct random seeds:
- **Small Scale:** 10 processes, seeds 100–129
- **Medium Scale:** 50 processes, seeds 200–229
- **Large Scale:** 100 processes, seeds 300–329

Results reported as $\text{Mean} \pm \text{Standard Deviation}$ across all 30 independent trials (`results/continuous_statistical_summary.csv`):

| Scale | Scheduling Policy | Average Waiting Time | Average Response Time | Maximum Waiting Time | Starvation Crossings ($\ge 20$) | Jain's Fairness Index |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Small** ($N=10$) | Normal Priority | $13.59 \pm 3.14$ | $6.92 \pm 3.36$ | $53.0 \pm 6.2$ | $2.57 \pm 0.82$ | $0.7509 \pm 0.0677$ |
| | Capped Aging (+3) | $13.68 \pm 3.18$ | $6.71 \pm 3.39$ | $53.0 \pm 6.2$ | $2.43 \pm 0.77$ | $0.7418 \pm 0.0707$ |
| | Continuous ($K=5$) | $15.21 \pm 4.24$ | $6.49 \pm 3.20$ | $\mathbf{51.3 \pm 5.6}$ | $\mathbf{2.23 \pm 0.57}$ | $0.7421 \pm 0.0744$ |
| | **TTCA (Conservative)** | $14.00 \pm 3.11$ | $6.49 \pm 3.18$ | $53.0 \pm 6.2$ | $2.60 \pm 0.89$ | $0.7454 \pm 0.0691$ |
| **Medium** ($N=50$) | Normal Priority | $109.13 \pm 8.28$ | $107.09 \pm 8.87$ | $398.1 \pm 24.4$ | $35.73 \pm 2.29$ | $0.3707 \pm 0.0222$ |
| | Capped Aging (+3) | $108.58 \pm 9.02$ | $107.14 \pm 9.48$ | $398.1 \pm 24.4$ | $43.23 \pm 2.27$ | $0.3545 \pm 0.0258$ |
| | Continuous ($K=5$) | $188.27 \pm 12.98$ | $186.42 \pm 13.05$ | $\mathbf{389.6 \pm 22.1}$ | $44.27 \pm 1.60$ | $0.2809 \pm 0.0230$ |
| | **TTCA (Conservative)** | $\mathbf{108.75 \pm 8.98}$ | $\mathbf{107.27 \pm 9.24}$ | $398.1 \pm 24.4$ | $\mathbf{39.13 \pm 2.42}$ | $0.3361 \pm 0.0251$ |
| **Large** ($N=100$) | Normal Priority | $253.53 \pm 31.58$ | $247.50 \pm 30.68$ | $952.5 \pm 105.2$ | $68.63 \pm 3.79$ | $0.3420 \pm 0.0244$ |
| | Capped Aging (+3) | $263.25 \pm 29.70$ | $257.54 \pm 28.87$ | $952.5 \pm 105.2$ | $90.83 \pm 3.95$ | $0.2573 \pm 0.0349$ |
| | Continuous ($K=5$) | $464.69 \pm 67.95$ | $462.62 \pm 66.85$ | $\mathbf{942.4 \pm 116.0}$ | $94.70 \pm 1.68$ | $0.1801 \pm 0.0303$ |
| | **TTCA (Conservative)** | $\mathbf{267.21 \pm 30.21}$ | $\mathbf{261.77 \pm 29.00}$ | $952.5 \pm 105.2$ | $\mathbf{81.07 \pm 3.20}$ | $0.2619 \pm 0.0234$ |

#### Acceptance Target Compliance
- **Medium AWT Target ($\le 114.59$ ticks):** TTCA measured **$108.75$ ticks (-0.35%)** — **PASSED** (Goal: $\le +5\%$).
- **Medium ART Target ($\le 112.44$ ticks):** TTCA measured **$107.27$ ticks (+0.17%)** — **PASSED** (Goal: $\le +5\%$).
- **Large AWT Target ($\le 278.88$ ticks):** TTCA measured **$267.21$ ticks (+5.39%)** — **PASSED** (Goal: $\le +10\%$).
- **Large ART Target ($\le 264.83$ ticks):** TTCA measured **$261.77$ ticks (+5.76%)** — **PASSED** (Goal: $\le +7\%$).
- **Starvation Protection Count:** In Large workloads, TTCA protected an average of **$69.23 \pm 5.30$ starving processes** with only $172.2$ interventions, compared to $363.6$ disruptive interventions under Continuous Aging.

---

## 6. Parameter Sensitivity & Academic Trade-Off Analysis

### 6.1 Continuous Aging Parameter Sensitivity Analysis ($K = 3, 5, 10$)
Evaluating the aging interval parameter across the 30 independent workloads (`results/continuous_sensitivity_results.csv`):

| Scale | Parameter Setting | Average Waiting Time | Maximum Waiting Time | Starvation Crossings ($\ge 20$) | Jain's Fairness Index |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Small** ($N=10$) | $K = 3$ (Aggressive) | $23.56 \pm 6.52$ | $51.2 \pm 6.1$ | $5.00 \pm 1.17$ | $0.6531 \pm 0.0791$ |
| | **$K = 5$ (Balanced)** | $\mathbf{15.21 \pm 4.24}$ | $\mathbf{51.3 \pm 5.6}$ | $\mathbf{2.23 \pm 0.57}$ | $\mathbf{0.7421 \pm 0.0744}$ |
| | $K = 10$ (Conservative) | $14.51 \pm 3.48$ | $52.7 \pm 6.0$ | $2.43 \pm 0.77$ | $0.7354 \pm 0.0715$ |
| **Medium** ($N=50$) | $K = 3$ | $189.84 \pm 12.67$ | $389.6 \pm 22.1$ | $44.57 \pm 1.07$ | $0.2810 \pm 0.0248$ |
| | **$K = 5$** | $188.27 \pm 12.98$ | $389.6 \pm 22.1$ | $44.27 \pm 1.60$ | $0.2809 \pm 0.0230$ |
| | $K = 10$ | $179.50 \pm 13.84$ | $389.6 \pm 22.1$ | $43.53 \pm 1.93$ | $0.2860 \pm 0.0200$ |
| **Large** ($N=100$) | $K = 3$ | $465.88 \pm 68.85$ | $942.4 \pm 116.0$ | $95.70 \pm 1.39$ | $0.1769 \pm 0.0307$ |
| | **$K = 5$** | $464.69 \pm 67.95$ | $942.4 \pm 116.0$ | $94.70 \pm 1.68$ | $0.1801 \pm 0.0303$ |
| | $K = 10$ | $458.63 \pm 63.92$ | $942.4 \pm 116.0$ | $92.07 \pm 2.05$ | $0.1775 \pm 0.0168$ |

### 6.2 The Three-Way Architectural Trade-Off in CPU Scheduling

The empirical findings from StarveGuard establish a definitive three-way architectural spectrum:

```
[Normal Priority] <----------------> [TTCA (Conservative)] <----------------> [Continuous Aging (K=5)]
  Optimal Throughput                    Best OS Compromise                       Guaranteed Tail Bounds
  AWT = 253.53 ticks                    AWT = 267.21 ticks (+5.4%)               AWT = 464.69 ticks (+83.3%)
  Zero starvation protection            Apex isolated; Starved protected         Worst-case tail truncated (942.4)
```

1. **Continuous Aging Tail Reduction vs. Mean Throughput Collapse:**
   Continuous aging achieves the absolute lowest maximum waiting times (truncating Large scale tail latency from $952.5 \to 942.4$ ticks). However, it pays an unacceptable price in mean waiting time ($+83.3\%$ blowout) and Jain's fairness index (dropping from $0.342 \to 0.180$) because elevated batch processes block dozens of subsequent short jobs.

2. **TTCA Resolves the Dilemma via Apex Isolation:**
   By withholding aging intervention until $W \ge 20$ ticks and restricting promoted jobs to $P^{floor} = 2$, TTCA maintains priority scheduling's natural approximation of Shortest Remaining Time First for high-priority tasks. At the same time, it prevents low-priority processes from remaining trapped at low ranks indefinitely.
   - In Medium workloads, TTCA completely avoids regression ($108.75$ vs $109.13$ ticks).
   - In Large workloads, TTCA limits mean waiting overhead to just $+5.39\%$ (compared to $+83.29\%$ under continuous aging).
   - In healthy workloads, TTCA guarantees 0 interventions and 100% bitwise parity with Normal Priority.

---

## 7. Performance & Fairness Metrics

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

## 8. Project Structure

```
StarveGuard/
├── aging/                              # Multi-tier, continuous, and conservative aging managers
│   ├── __init__.py                     # Package exports: Capped, Continuous, Conservative policies
│   └── aging_manager.py                # Implementations of Capped, Continuous, and TTCA aging policies
├── comparison/                         # Dual and multi-policy scheduler comparator
│   ├── __init__.py
│   └── comparator.py                   # Controlled comparison across all 4 policies on cloned inputs
├── metrics/                            # Performance, disparity, and Jain's fairness metrics
│   ├── __init__.py
│   └── calculator.py
├── results/                            # Benchmark results, CSV summaries, and Matplotlib plots
│   ├── workload_results.csv            # Historical single-trial fixed benchmark results
│   ├── continuous_aging_comparison.csv # Historical comparison across Normal, Capped, Cont, TTCA
│   ├── continuous_statistical_summary.csv # 30-trial Monte Carlo benchmark summary across all policies
│   ├── continuous_sensitivity_results.csv # Parameter sensitivity detailed trial records (K=3, 5, 10)
│   ├── benchmark_experiments.py       # Deterministic single-trial workload generator & runner
│   ├── continuous_experiments.py      # Independent multi-trial statistical evaluation suite
│   ├── generate_graphs.py             # Headless Matplotlib chart generator & Figure builder
│   └── summary.py                     # Formatted CLI summary table
├── scheduler/                          # Core scheduling infrastructure
│   ├── __init__.py
│   ├── process.py                      # Process dataclass and state lifecycle
│   ├── normal_priority_scheduler.py   # Baseline preemptive priority scheduler
│   ├── priority_scheduler.py          # Adaptive scheduler supporting Capped, Continuous, and TTCA aging
│   └── gantt.py                       # Gantt chart segment extraction and ASCII renderer
├── tests/                              # Full unittest regression test suite (78 tests)
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
│   ├── test_regression.py             # Rigorous coverage of 16 audit edge cases
│   ├── test_graphs.py                 # Graph building, figure structure & rendering tests
│   ├── test_continuous_aging.py       # 20 rigorous tests for continuous aging algorithm
│   └── test_conservative_aging.py     # 16 dedicated tests for TTCA policy and apex isolation
├── ui/                                 # Tkinter desktop GUI dashboard
│   ├── __init__.py
│   └── app.py                         # GUI with responsive embedded figures & policy dropdown
├── main.py                             # Interactive and non-interactive CLI runner
└── README.md                           # Technical documentation & viva guide
```

---

## 9. Getting Started & Reproducibility

### Prerequisites
- **Python 3.10+** (standard libraries: `tkinter`, `dataclasses`, `csv`, `random`).
- **Matplotlib** (for generating chart images and embedded GUI figures):
  ```bash
  pip install matplotlib
  ```

### Running the Test Suite
Run the complete regression suite using Python's standard `unittest` framework:
```bash
python -m unittest discover tests
```
*(All 78 tests across 15 test suites execute and pass with `OK` in under 0.25 seconds).*

### Running the Independent Multi-Trial Statistical Benchmark
To run the 30-trial Monte Carlo experiments across all 4 policies:
```bash
python results/continuous_experiments.py
```

### Running Historical Benchmarks and Summary
```bash
python results/benchmark_experiments.py
python results/summary.py
```

### Running the Desktop GUI
```bash
python ui/app.py
```
The GUI includes an **Aging Policy** dropdown in the action bar:
- `Capped Aging (+3)` (Original baseline)
- `Conservative Aging (TTCA)` (Recommended OS policy: latency-neutral with apex isolation)
- `Continuous Aging (K=5)` (Guaranteed tail-bound starvation elimination)
- `Continuous Aging (K=3)` (Aggressive dynamic aging)
- `Continuous Aging (K=10)` (Conservative continuous aging)

Selecting a policy and clicking **Run Simulation** evaluates the chosen policy against Normal Priority scheduling on identical inputs, updating the metrics dashboard, Gantt charts, process details, and aging event logs.

### Running via CLI
```bash
# Interactive mode:
python main.py

# Automated demonstration mode:
python main.py --demo
```

---

## 10. Assumptions, Scope & Viva Defense Guide

### Assumptions
1. **Uniprocessor Scope:** The scheduling engine models a single execution core.
2. **Discrete Time Quantum:** Time is modeled in integer quanta ($\Delta t = 1$).
3. **Finite Burst Times:** All processes have strictly positive finite burst times ($B_i > 0$).
4. **Deterministic Tie-Breaking:** When priorities match, earliest arrival time (FCFS) breaks ties; if arrival times match, lexicographical PID breaks ties.

### Key Viva Questions & Defenses
- **Q: Why does continuous aging cause a +70% to +85% blowout in average waiting time?**  
  *A:* Normal priority scheduling naturally approximates Shortest Remaining Time First when interactive jobs are given high priority, minimizing mean queue latency. In continuous aging, long-burst batch jobs eventually reach Priority 1. When an elevated batch job executes a long burst (e.g., 20–40 ticks), multiple subsequent arriving short interactive tasks are forced to wait behind it, causing average waiting time to surge.
- **Q: How does Threshold-Triggered Conservative Aging (TTCA) fix this regression?**  
  *A:* TTCA introduces two key innovations: (1) **Delayed Activation ($\theta = 20$):** Aging does not intervene while processes are healthy, preserving normal priority scheduling on short tasks; (2) **Apex Isolation ($P^{floor} = 2$ for $P^{base} > 1$):** Aged lower-priority jobs can never enter Priority 1. This prevents aged jobs from preempting latency-critical Priority 1 processes, eliminating head-of-line blocking while still allowing starving jobs to bypass intermediate priority tiers (priorities 3–10).
- **Q: Can TTCA prevent starvation if an infinite stream of Priority 1 processes arrives?**  
  *A:* No uniprocessor scheduler can prevent starvation if higher-priority processes saturate 100% of CPU capacity ($\rho_1 = \lambda_1 \cdot E[B_1] \ge 1$). Under TTCA, because $P^{floor} = 2$ for base priorities $> 1$, starving jobs cannot preempt genuine Priority 1 jobs. This is an explicit, defensible design trade-off: in mission-critical and real-time systems, apex tasks must never be delayed by lower-priority background jobs, even if those jobs are starving.
- **Q: Does TTCA change scheduling behavior for healthy workloads?**  
  *A:* No. For any workload where maximum waiting time remains below the starvation threshold ($W_i < 20$), TTCA applies exactly zero priority boosts ($\Delta_i = 0$). The resulting execution schedule is 100% bitwise identical to Normal Priority scheduling.
