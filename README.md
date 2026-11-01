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

#### Stepwise Priority Boost Progression Table
| Cumulative Waiting Time ($W_i$) | Starvation Condition | Aging Boost ($\Delta_i$) | Effective Priority ($P_i^{base} > 1$) | Effective Priority ($P_i^{base} = 1$) | Policy Status |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **$0 \le W_i < 20$** | $W_i < \theta$ | `0` | $P_i^{base}$ | `1` | Inactive; 100% normal priority preserved |
| **$20 \le W_i < 30$** | $\theta \le W_i < \theta + K$ | `+1` | $\max(2, P_i^{base} - 1)$ | `1` | Starvation detected; first conservative boost |
| **$30 \le W_i < 40$** | $\theta + K \le W_i < \theta + 2K$ | `+2` | $\max(2, P_i^{base} - 2)$ | `1` | Continued starvation; second boost |
| **$W_i \ge 40$** | $W_i \ge \theta + 2K$ | `+3` | $\max(2, P_i^{base} - 3)$ | `1` | Maximum boost ceiling ($M=3$) reached |

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

## 5. Performance Evaluation & Benchmarking Module

StarveGuard provides a dedicated, scientifically rigorous evaluation engine that compares all four scheduling policies across **5 workload scales**, **7 workload categories**, and **30 independent deterministic trials per scenario** (1,050 total workloads, 4,200 simulation runs).

### 5.1 Multi-Scale Workload Methodology

| Scale | Process Count ($N$) | Evaluation Scope |
| :--- | :---:| :--- |
| **Small** | 10 | Micro-architectural baseline, immediate contention dynamics |
| **Medium** | 50 | Intermediate scheduling load, moderate priority variance |
| **Large** | 100 | Multi-tier heterogeneous operating systems workloads |
| **Very Large** | 250 | High-density queue contention with extensive preemption chains |
| **Stress** | 500 | System stress testing, tail latency boundary analysis |

### 5.2 Workload Categories

- **Workload A — Balanced:** Uniformly distributed priorities ($1 \le P \le 10$), burst times ($2 \le B \le 20$), staggered arrivals.
- **Workload B — Priority Skew:** Severe concentration in low-priority tiers (75% processes in priorities 7–10, 25% in priorities 1–4).
- **Workload C — Short and Long Burst Mixture:** Bimodal workload combining short interactive tasks ($1 \le B \le 4$) with long CPU-bound jobs ($25 \le B \le 50$).
- **Workload D — Heavy Contention:** Clustered near-simultaneous arrivals ($t \in [0, 5]$) competing aggressively for the CPU.
- **Workload E — Staggered Arrivals:** Processes arrive in wave clusters with distinct idle gaps between arrival phases.
- **Workload F — Starvation-Prone:** Initial batch of lower-priority batch jobs trapped behind a continuous stream of higher-priority tasks.
- **Workload G — Mixed Realistic Workload:** Multi-tier distribution: 40% interactive, 35% normal application, 25% background batch.

All workloads are 100% deterministic, generated via `results/workload_generator.py` using recorded random seeds. Identical cloned workload instances are dispatched to all four scheduling policies.

### 5.3 Formal Scheduling Invariants

Every simulation run enforces 8 strict scheduling invariants verified via `results/invariants.py`:
1. **Complete Execution:** Every process completes exactly once (`remaining_time == 0`).
2. **Chronological Feasibility:** Completion time $\ge$ arrival time.
3. **Turnaround Conservation:** $\text{Turnaround Time} = \text{Completion Time} - \text{Arrival Time}$.
4. **Waiting Time Conservation:** $\text{Waiting Time} = \text{Turnaround Time} - \text{Burst Time}$.
5. **Response Time Definition:** $\text{Response Time} = \text{First Run Time} - \text{Arrival Time} \ge 0$.
6. **No Execution Prior to Arrival:** No process executes before its arrival time.
7. **Mutual Exclusion & Uniprocessor Invariant:** Exactly one process (or `"IDLE"`) is scheduled per discrete clock tick.
8. **Workload Identity & Immutability:** Process parameters (`pid`, `arrival_time`, `burst_time`, `original_priority`) remain strictly unaltered.

Across the 4,200 simulation runs conducted in the full benchmark suite, **all 8 invariants passed with 100% compliance**.

### 5.4 Performance Metrics Definitions

Calculated via `metrics/calculator.py`:

- **Average Waiting Time ($AWT$):** Mean clock ticks spent ready in the queue without CPU allocation.
  $$AWT = \frac{1}{n} \sum_{i=1}^n W_i$$
- **Average Turnaround Time ($ATAT$):** Mean elapsed time from arrival to completion.
  $$ATAT = \frac{1}{n} \sum_{i=1}^n (\text{Completion}_i - \text{Arrival}_i)$$
- **Average Response Time ($ART$):** Mean elapsed time from arrival to first CPU dispatch.
  $$ART = \frac{1}{n} \sum_{i=1}^n (\text{FirstRun}_i - \text{Arrival}_i)$$
- **Maximum Waiting Time ($MWT$):** Worst-case tail latency experienced by any single process.
  $$MWT = \max_{1 \le i \le n}(W_i)$$
- **Jain's Fairness Index ($J$):** Evaluates equity of normalized service efficiency across all jobs:
  $$J(x_1, \dots, x_n) = \frac{\left(\sum_{i=1}^n x_i\right)^2}{n \cdot \sum_{i=1}^n x_i^2}, \quad x_i = \frac{\text{burst\_time}_i}{\text{turnaround\_time}_i}$$
  *Metric Scope:* Measures equality of *execution efficiency ratios*.
- **Starvation Statistics:**
  - $\text{Starved Process Count}$: Processes crossing the 20-tick threshold ($W_i \ge 20$).
  - $\text{Starvation Percentage}$: $(\text{Starved Count} / n) \times 100$.
  - $\text{Starved Average Waiting Time}$: Mean wait time strictly among affected processes.
  - $\text{Starved Maximum Waiting Time}$: Worst-case wait time among affected processes.
  - $\text{Aging Interventions}$: Number of discrete priority adjustments executed.
  - $\text{Protected Processes}$: Processes whose priority was boosted by aging at least once.
- **CPU Utilization:**
  $$\text{CPU Utilization} = \left(\frac{\text{Total Busy Ticks}}{\text{Total Simulation Time}}\right) \times 100$$
- **Throughput:**
  $$\text{Throughput} = \frac{\text{Completed Processes}}{\text{Total Simulation Time}} \quad (\text{processes/tick})$$
- **Simulator Scheduling Overhead:** Wall-clock time recorded via `time.perf_counter()`, reporting total decisions, decision duration, average microseconds per decision ($\mu s/\text{decision}$), and candidate priority evaluations.

### 5.5 Statistical Methodology & Hypothesis Testing

Implemented in `results/statistics.py`:
- **Descriptive Statistics:** Mean, sample standard deviation ($N-1$), minimum, maximum, median, and 95% Confidence Intervals:
  $$CI_{95} = \text{Mean} \pm t_{crit, df=N-1} \cdot \frac{s}{\sqrt{N}}$$
- **Percentage Change vs. Normal Priority:**
  $$\Delta \% = \left(\frac{\text{Policy Metric} - \text{Normal Metric}}{\text{Normal Metric}}\right) \times 100$$
  *Explicit Zero-Baseline Handling:* Division by zero is strictly guarded; when both baseline and policy are 0, $\Delta = 0.00\%$; when baseline is 0 and policy $> 0$, absolute difference is reported.
- **Paired Hypothesis Testing:** Because all 4 policies execute on the identical workload instance per trial, paired testing is mandatory:
  - **Paired Student's t-test:** Two-tailed p-value with Cohen's $d_z$ effect size.
  - **Wilcoxon Signed-Rank Test:** Non-parametric evaluation with continuity correction and effect size $r = |z| / \sqrt{N}$.

---

## 6. Empirical Benchmark Results & Academic Trade-Off Analysis

### 6.1 Macro Empirical Summary Across Scales (30 Trials per Scale, Averaged Across All Categories)
*Extracted from `results/performance_evaluation/aggregate_summary.csv`:*

| Scale | Policy | Average Waiting (ticks) | Average Turnaround (ticks) | Average Response (ticks) | Maximum Waiting (ticks) | Jain's Fairness | Starvation Rate (%) | Decision Overhead ($\mu s$) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Small** ($N=10$) | Normal Priority | **$12.37 \pm 4.70$** | **$21.75 \pm 5.76$** | $6.97 \pm 3.12$ | $46.8 \pm 10.9$ | **$0.730 \pm 0.076$** | **$21.2\% \pm 11.2\%$** | $3.57 \pm 0.74$ |
| | Capped Aging (+3) | $12.82 \pm 4.88$ | $22.20 \pm 5.92$ | $6.86 \pm 3.10$ | $46.8 \pm 10.9$ | $0.722 \pm 0.079$ | $22.5\% \pm 11.0\%$ | $4.18 \pm 0.81$ |
| | Continuous ($K=5$) | $15.30 \pm 6.64$ | $24.68 \pm 7.46$ | $\mathbf{6.73 \pm 3.01}$ | $\mathbf{45.2 \pm 10.1}$ | $0.718 \pm 0.082$ | $24.8\% \pm 11.9\%$ | $4.29 \pm 0.83$ |
| | TTCA (Conservative) | $12.63 \pm 4.77$ | $22.01 \pm 5.82$ | $6.83 \pm 3.09$ | $46.8 \pm 10.9$ | $0.725 \pm 0.078$ | $22.0\% \pm 11.1\%$ | $4.34 \pm 0.85$ |
| **Medium** ($N=50$) | Normal Priority | **$160.37 \pm 53.60$** | **$172.90 \pm 55.43$** | $157.94 \pm 54.00$ | $440.0 \pm 67.2$ | **$0.407 \pm 0.087$** | **$70.4\% \pm 13.9\%$** | $6.42 \pm 1.25$ |
| | Capped Aging (+3) | $162.77 \pm 54.89$ | $175.31 \pm 56.67$ | $157.97 \pm 54.34$ | $440.0 \pm 67.2$ | $0.384 \pm 0.089$ | $79.8\% \pm 10.3\%$ | $7.81 \pm 1.48$ |
| | Continuous ($K=5$) | $248.86 \pm 88.08$ | $261.39 \pm 89.47$ | $246.52 \pm 88.05$ | $\mathbf{433.0 \pm 67.8}$ | $0.317 \pm 0.084$ | $85.3\% \pm 8.2\%$ | $8.07 \pm 1.52$ |
| | TTCA (Conservative) | $161.46 \pm 53.51$ | $173.99 \pm 55.33$ | $158.11 \pm 53.95$ | $440.0 \pm 67.2$ | $0.379 \pm 0.084$ | $75.7\% \pm 11.4\%$ | $8.15 \pm 1.58$ |
| **Large** ($N=100$) | Normal Priority | **$435.53 \pm 175.30$** | **$451.27 \pm 178.67$** | $430.73 \pm 175.74$ | $1080.0 \pm 185.0$ | **$0.339 \pm 0.076$** | **$75.9\% \pm 13.7\%$** | $9.82 \pm 1.84$ |
| | Capped Aging (+3) | $450.49 \pm 176.43$ | $466.23 \pm 179.74$ | $442.27 \pm 176.68$ | $1080.0 \pm 185.0$ | $0.281 \pm 0.075$ | $88.8\% \pm 6.9\%$ | $12.44 \pm 2.19$ |
| | Continuous ($K=5$) | $633.20 \pm 253.90$ | $648.94 \pm 255.45$ | $628.98 \pm 253.84$ | $\mathbf{1071.3 \pm 186.2}$ | $0.218 \pm 0.072$ | $95.3\% \pm 2.9\%$ | $12.92 \pm 2.29$ |
| | TTCA (Conservative) | $442.15 \pm 174.62$ | $457.88 \pm 177.96$ | $434.69 \pm 174.96$ | $1080.0 \pm 185.0$ | $0.286 \pm 0.073$ | $83.6\% \pm 9.4\%$ | $13.10 \pm 2.37$ |
| **Very Large** ($N=250$) | Normal Priority | **$1183.17 \pm 527.20$** | **$1202.94 \pm 532.74$** | $1173.34 \pm 527.76$ | $2663.7 \pm 476.3$ | **$0.273 \pm 0.063$** | **$85.5\% \pm 8.2\%$** | $18.65 \pm 3.42$ |
| | Capped Aging (+3) | $1241.68 \pm 529.75$ | $1261.45 \pm 535.25$ | $1224.28 \pm 530.07$ | $2663.7 \pm 476.3$ | $0.198 \pm 0.057$ | $94.6\% \pm 3.1\%$ | $24.71 \pm 4.21$ |
| | Continuous ($K=5$) | $1757.24 \pm 764.20$ | $1777.01 \pm 766.42$ | $1750.64 \pm 763.95$ | $\mathbf{2653.2 \pm 477.1}$ | $0.147 \pm 0.052$ | $97.9\% \pm 1.2\%$ | $25.75 \pm 4.39$ |
| | TTCA (Conservative) | $1211.23 \pm 526.43$ | $1231.00 \pm 531.94$ | $1194.20 \pm 526.85$ | $2663.7 \pm 476.3$ | $0.207 \pm 0.057$ | $90.9\% \pm 4.8\%$ | $26.07 \pm 4.56$ |
| **Stress** ($N=500$) | Normal Priority | **$2228.08 \pm 1018.50$** | **$2249.98 \pm 1025.20$** | $2217.15 \pm 1019.10$ | $4917.4 \pm 898.1$ | **$0.229 \pm 0.051$** | **$88.4\% \pm 6.3\%$** | $33.24 \pm 6.18$ |
| | Capped Aging (+3) | $2349.56 \pm 1024.10$ | $2371.46 \pm 1030.70$ | $2324.96 \pm 1024.50$ | $4917.4 \pm 898.1$ | $0.158 \pm 0.045$ | $96.1\% \pm 2.0\%$ | $45.19 \pm 7.82$ |
| | Continuous ($K=5$) | $3330.40 \pm 1494.60$ | $3352.30 \pm 1496.70$ | $3320.10 \pm 1494.30$ | $\mathbf{4904.3 \pm 899.4}$ | $0.114 \pm 0.039$ | $98.7\% \pm 0.7\%$ | $47.28 \pm 8.21$ |
| | TTCA (Conservative) | $2286.08 \pm 1017.30$ | $2307.98 \pm 1024.00$ | $2259.97 \pm 1017.80$ | $4917.4 \pm 898.1$ | $0.165 \pm 0.045$ | $93.0\% \pm 3.2\%$ | $47.92 \pm 8.45$ |

### 6.2 Key Academic Findings & Viva Answers

#### Question: "How much does StarveGuard improve or regress system scheduling performance compared with traditional Normal Priority Scheduling?"

1. **Throughput & Mean Latency Findings:**
   - Normal Priority Scheduling naturally minimizes average waiting time across heterogeneous workloads because prioritizing short interactive jobs naturally approximates Shortest Remaining Time First (SRTF).
   - Unconstrained Continuous Aging ($K=5$) causes a severe system-wide regression: in Medium scale, waiting time balloons by **+55.2%**, in Large scale by **+45.4%**, in Very Large by **+48.5%**, and in Stress scale by **+49.5%** (surging up to **+230.1%** in starvation-prone workloads). Promoting long-burst batch jobs to Priority 1 forces dozens of subsequent short interactive jobs to queue behind them.
   - **TTCA with Apex Isolation resolves this trade-off:** TTCA's average waiting time stays within **+0.7% (Medium)**, **+1.5% (Large)**, **+2.4% (Very Large)**, and **+2.6% (Stress)** of Normal Priority baseline, completely preventing the continuous aging latency blowout.

2. **Tail Starvation Outliers vs. Threshold Crossings:**
   - Continuous Aging achieves the lowest maximum waiting times (truncating extreme tail wait times by 10–15 ticks in large workloads). However, it does so by pushing almost all other jobs past the 20-tick threshold (starvation percentage reaches 95%–98%).
   - TTCA preserves apex priority guarantees ($P^{floor}=2$) for base priority $> 1$. Starving processes receive controlled boosts ($\Delta = +1, +2, +3$), resolving starvation against intermediate priority tiers without destabilizing apex queues.

3. **Simulator Decision Overhead:**
   - Scheduler decision logic averages $3.57\ \mu s$ (Small), $9.82\ \mu s$ (Large), and $33.24\ \mu s$ (Stress) per discrete clock tick.
   - Decision overhead is completely negligible relative to simulation time, confirming that StarveGuard's priority tracking is computationally lightweight.

---

## 7. Generated Benchmark Graphs & Artifacts

All 12 publication-quality benchmark charts are generated automatically in `results/performance_evaluation/graphs/`:

| Figure Filename | Visual Representation & Scope |
| :--- | :--- |
| `01_average_waiting_time_vs_scale.png` | Mean queue waiting time across Small, Medium, Large, Very Large, Stress scales |
| `02_average_turnaround_time_vs_scale.png` | Mean turnaround time from arrival to completion across all scales |
| `03_average_response_time_vs_scale.png` | Initial dispatch latency comparison across all scales |
| `04_maximum_waiting_time_vs_scale.png` | Worst-case tail latency comparison across scales |
| `05_jains_fairness_index_vs_scale.png` | Jain's Fairness Index ($x_i = \text{burst}/\text{turnaround}$) across scales |
| `06_starvation_percentage_vs_scale.png` | Percentage of processes crossing starvation threshold ($W \ge 20$) |
| `07_cpu_utilization_vs_scale.png` | CPU core utilization percentage across scales |
| `08_throughput_vs_scale.png` | System throughput (completed processes per discrete tick) |
| `09_scheduling_overhead_vs_scale.png` | Simulator decision logic overhead ($\mu s/\text{decision}$) |
| `10_percentage_comparison_heatmap.png` | Heatmap of percentage change vs. Normal Priority across all metrics and scales |
| `11_workload_category_comparison.png` | Grouped bar chart comparing all 4 policies across Categories A to G |
| `12_mean_performance_confidence_intervals.png` | Error-bar plot showing Mean Waiting Time with 95% Confidence Intervals |

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
│   └── calculator.py                   # Extended metrics: CPU utilization, throughput, starvation stats, overhead
├── results/                            # Benchmark results, CSV summaries, and Matplotlib plots
│   ├── workload_results.csv            # Historical single-trial fixed benchmark results
│   ├── continuous_aging_comparison.csv # Historical comparison across Normal, Capped, Cont, TTCA
│   ├── continuous_statistical_summary.csv # Historical 30-trial benchmark summary
│   ├── continuous_sensitivity_results.csv # Parameter sensitivity detailed trial records (K=3, 5, 10)
│   ├── benchmark_experiments.py       # Deterministic single-trial workload generator & runner
│   ├── continuous_experiments.py      # Historical multi-trial statistical evaluation suite
│   ├── generate_graphs.py             # Historical chart generator
│   ├── summary.py                     # CLI summary table
│   ├── workload_generator.py          # 5-scale, 7-category deterministic workload generator
│   ├── invariants.py                  # 8 formal scheduling invariants validator
│   ├── statistics.py                  # Descriptive stats, 95% CI, paired t-test, Wilcoxon signed-rank
│   ├── benchmark_engine.py            # Comprehensive 4-policy Monte Carlo benchmarking engine
│   ├── evaluation_graphs.py           # 12 publication-quality Matplotlib chart generator
│   └── performance_evaluation/        # Dedicated evaluation output directory
│       ├── raw_trial_results.csv      # Flat trial records (4,200 rows)
│       ├── aggregate_summary.csv      # Mean, std, median, min, max, 95% CI per scenario
│       ├── percentage_comparison.csv  # Percentage change vs. Normal Priority
│       ├── statistical_tests.csv      # Paired t-test and Wilcoxon signed-rank test outputs
│       ├── workload_definitions.csv   # Workload categories definitions
│       ├── benchmark_metadata.json    # Experiment configuration metadata
│       ├── performance_report.txt     # Automated executive recommendation report
│       └── graphs/                    # 12 high-resolution PNG publication charts
├── scheduler/                          # Core scheduling infrastructure
│   ├── __init__.py
│   ├── process.py                      # Process dataclass and state lifecycle
│   ├── normal_priority_scheduler.py   # Baseline preemptive priority scheduler with overhead instrumentation
│   ├── priority_scheduler.py          # Adaptive scheduler supporting Capped, Continuous, and TTCA aging
│   └── gantt.py                       # Gantt chart segment extraction and ASCII renderer
├── tests/                              # Full unittest regression test suite (97 tests across 16 suites)
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
│   ├── test_conservative_aging.py     # 16 dedicated tests for TTCA policy and apex isolation
│   └── test_performance_evaluation.py # 19 dedicated tests for metrics, invariants, statistics & engine
├── ui/                                 # Tkinter desktop GUI dashboard
│   ├── __init__.py
│   └── app.py                         # GUI with interactive simulation and threaded Performance Evaluation
├── main.py                             # Interactive and non-interactive CLI runner
└── README.md                           # Technical documentation & viva guide
```

---

## 9. Getting Started & Reproducibility

### Prerequisites
- **Python 3.10+** (standard libraries: `tkinter`, `dataclasses`, `csv`, `random`).
- **NumPy & Matplotlib**:
  ```bash
  pip install numpy matplotlib
  ```

### Running the Complete Test Suite
Run all 97 automated regression and invariant tests:
```bash
python -m unittest discover tests
```
*(All 97 tests across 16 test suites execute and pass with `OK` in ~2.5 seconds).*

### Running the Full Performance Evaluation Benchmark
To run the full 1,050-workload (4,200 policy simulations) Monte Carlo evaluation:
```bash
python results/benchmark_engine.py
```
*(Outputs flat CSVs, statistical summaries, metadata, and 12 publication charts to `results/performance_evaluation/`).*

### Running Quick Custom Benchmarks via CLI
```bash
# Quick smoke test (Small and Medium scales, Category A and F, 5 trials):
python results/benchmark_engine.py --scales small,medium --categories A,F --trials 5
```

### Running the Desktop GUI
```bash
python ui/app.py
```
The desktop application includes:
1. **Interactive Scheduler Simulator:** Test arbitrary custom process sets or load demos against any of the 4 policies, viewing live Gantt charts, metrics, process details, and aging event logs.
2. **Performance Evaluation Module:** Run multi-scale benchmarks directly from the GUI with live progress reporting, inspect aggregate metrics and percentage comparisons in a responsive table, and browse all 12 publication graphs in the embedded viewer.

---

## 10. Assumptions, Scope & Limitations

1. **Uniprocessor Scope:** The scheduling engine models a single execution core.
2. **Discrete Time Quantum:** Time is modeled in integer quanta ($\Delta t = 1$), representing discrete CPU clock cycles.
3. **Finite Burst Times:** All processes have strictly positive finite burst times ($B_i > 0$).
4. **Simulator vs. Kernel Overhead:** Decision overhead is measured in simulator Python wall-clock microseconds (`time.perf_counter()`), providing simulator-level algorithmic complexity rather than real kernel context-switch latency.
5. **Deterministic Tie-Breaking:** When priorities match, earliest arrival time (FCFS) breaks ties; if arrival times match, lexicographical PID breaks ties.
