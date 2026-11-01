from typing import Any, Dict, List, Optional, Tuple, Union
from scheduler.process import Process
from scheduler.normal_priority_scheduler import NormalPriorityScheduler
from scheduler.priority_scheduler import PriorityScheduler
from starvation.detector import StarvationDetector
from aging.aging_manager import AgingManager
from metrics.calculator import MetricsCalculator


class SchedulerComparator:
    """
    Executes controlled comparisons between standard Preemptive Priority Scheduling
    and StarveGuard Adaptive Priority Scheduling on identical process workloads.

    Supports comparing:
        - Normal Preemptive Priority Scheduling (fixed priorities)
        - StarveGuard Capped Aging (+3 max boost)
        - StarveGuard Continuous Aging (P_eff = max(1, P_base - floor(W / K)))
        - StarveGuard Conservative Aging (TTCA, threshold-triggered with apex isolation)
    """

    def __init__(self, process_data: List[Union[Tuple[str, int, int, int], Process]]):
        self.process_data = process_data

    def create_processes(self) -> List[Process]:
        processes = []
        for item in self.process_data:
            if isinstance(item, Process):
                processes.append(item.clone())
            else:
                pid, arrival, burst, priority = item
                processes.append(Process(pid, arrival, burst, priority))
        return processes

    def run_normal(self) -> Dict[str, Any]:
        processes = self.create_processes()
        scheduler = NormalPriorityScheduler(processes)
        scheduler.run()

        metrics = MetricsCalculator(processes)
        detector = StarvationDetector()
        # In normal scheduling, evaluate how many processes crossed starvation threshold (waiting >= 20)
        starved_in_normal = sum(detector.is_starving(p) for p in processes)
        starved_procs = [p for p in processes if detector.is_starving(p)]
        starved_avg_wt = sum(p.waiting_time for p in starved_procs) / len(starved_procs) if starved_procs else 0.0
        starved_max_wt = max((p.waiting_time for p in starved_procs), default=0)
        overhead = metrics.scheduling_overhead(scheduler)

        return {
            "policy": "normal",
            "k": None,
            "processes": processes,
            "scheduler": scheduler,
            "average_waiting": metrics.average_waiting_time(),
            "average_turnaround": metrics.average_turnaround_time(),
            "average_response": metrics.average_response_time(),
            "maximum_waiting": metrics.maximum_waiting_time(),
            "waiting_disparity": metrics.waiting_time_disparity(),
            "starved_processes": starved_in_normal,
            "starvation_percentage": (starved_in_normal / len(processes) * 100.0) if processes else 0.0,
            "starved_average_waiting": starved_avg_wt,
            "starved_maximum_waiting": starved_max_wt,
            "post_threshold_average_waiting": metrics.post_threshold_average_waiting_time(threshold=20),
            "post_threshold_maximum_waiting": metrics.post_threshold_maximum_waiting_time(threshold=20),
            "median_waiting": metrics.median_waiting_time(),
            "waiting_p95": metrics.percentile_waiting_time(95.0),
            "waiting_p99": metrics.percentile_waiting_time(99.0),
            "post_threshold_waiting_p95": metrics.percentile_post_threshold_waiting_time(95.0, threshold=20),
            "longest_continuous_wait": metrics.longest_continuous_waiting_time(),
            "preemption_count": metrics.preemption_count(scheduler),
            "protected_processes": 0,
            "aging_interventions": 0,
            "fairness": metrics.fairness_index(),
            "cpu_utilization": metrics.cpu_utilization(scheduler),
            "throughput": metrics.throughput(scheduler),
            "scheduling_decisions": overhead["total_decisions"],
            "decision_time_sec": overhead["total_decision_time_sec"],
            "avg_decision_time_us": overhead["avg_decision_time_us"],
            "priority_evaluations": overhead["priority_evaluations"],
        }

    def run_starveguard(
        self,
        detector: Optional[StarvationDetector] = None,
        aging_policy: str = "capped",
        k: int = 5,
        threshold: int = 20,
        k_starve: int = 10,
        max_boost: int = 3,
        floor: Optional[int] = None,
        aging_manager: Optional[AgingManager] = None,
        tie_breaker: Union[str, Any] = "fcfs",
        emergency_threshold: int = 40,
        gamma: float = 0.05,
        preemption_hysteresis: bool = False,
        policy_label: Optional[str] = None
    ) -> Dict[str, Any]:
        processes = self.create_processes()
        if aging_manager is None:
            aging_manager = AgingManager(
                policy=aging_policy,
                k=k,
                threshold=threshold,
                k_starve=k_starve,
                max_boost=max_boost,
                floor=floor
            )

        scheduler = PriorityScheduler(
            processes,
            detector=detector,
            aging_manager=aging_manager,
            tie_breaker=tie_breaker,
            emergency_threshold=emergency_threshold,
            gamma=gamma,
            preemption_hysteresis=preemption_hysteresis
        )
        scheduler.run()

        metrics = MetricsCalculator(processes)
        overhead = metrics.scheduling_overhead(scheduler)
        th = getattr(aging_manager, "threshold", 20) or 20

        return {
            "policy": policy_label if policy_label is not None else aging_manager.policy_name,
            "tie_breaker": getattr(scheduler, "tie_breaker", "fcfs") if isinstance(getattr(scheduler, "tie_breaker", "fcfs"), str) else "custom",
            "k": getattr(aging_manager, "k", None),
            "threshold": getattr(aging_manager, "threshold", None),
            "max_boost": getattr(aging_manager, "max_boost", None),
            "processes": processes,
            "scheduler": scheduler,
            "average_waiting": metrics.average_waiting_time(),
            "average_turnaround": metrics.average_turnaround_time(),
            "average_response": metrics.average_response_time(),
            "maximum_waiting": metrics.maximum_waiting_time(),
            "waiting_disparity": metrics.waiting_time_disparity(),
            "median_waiting": metrics.median_waiting_time(),
            "waiting_p95": metrics.percentile_waiting_time(95.0),
            "waiting_p99": metrics.percentile_waiting_time(99.0),
            "starved_processes": metrics.starved_process_count(),
            "starvation_percentage": metrics.starvation_percentage(),
            "starved_average_waiting": metrics.starved_average_waiting_time(),
            "starved_maximum_waiting": metrics.starved_maximum_waiting_time(),
            "post_threshold_average_waiting": metrics.post_threshold_average_waiting_time(threshold=th),
            "post_threshold_maximum_waiting": metrics.post_threshold_maximum_waiting_time(threshold=th),
            "post_threshold_waiting_p95": metrics.percentile_post_threshold_waiting_time(95.0, threshold=th),
            "longest_continuous_wait": metrics.longest_continuous_waiting_time(),
            "preemption_count": metrics.preemption_count(scheduler),
            "protected_processes": metrics.protected_process_count(),
            "priority_changed_count": metrics.priority_changed_count(),
            "aging_interventions": metrics.aging_intervention_count(scheduler),
            "fairness": metrics.fairness_index(),
            "cpu_utilization": metrics.cpu_utilization(scheduler),
            "throughput": metrics.throughput(scheduler),
            "scheduling_decisions": overhead["total_decisions"],
            "decision_time_sec": overhead["total_decision_time_sec"],
            "avg_decision_time_us": overhead["avg_decision_time_us"],
            "priority_evaluations": overhead["priority_evaluations"],
        }

    def run_starveguard_continuous(
        self,
        k: int = 5,
        detector: Optional[StarvationDetector] = None
    ) -> Dict[str, Any]:
        """Convenience method to run continuous aging with parameter K."""
        return self.run_starveguard(
            detector=detector,
            aging_policy="continuous",
            k=k
        )

    def run_starveguard_conservative(
        self,
        detector: Optional[StarvationDetector] = None,
        threshold: int = 20,
        k_starve: int = 10,
        max_boost: int = 3,
        floor: int = 2
    ) -> Dict[str, Any]:
        """Convenience method to run Threshold-Triggered Conservative Aging (TTCA)."""
        return self.run_starveguard(
            detector=detector,
            aging_policy="conservative",
            threshold=threshold,
            k_starve=k_starve,
            max_boost=max_boost,
            floor=floor,
            tie_breaker="fcfs",
            policy_label="ttca"
        )

    def run_ttca_cand_a(
        self,
        detector: Optional[StarvationDetector] = None,
        threshold: int = 20,
        k_base: int = 10,
        burst_scale: int = 10,
        max_boost: int = 3,
        floor: int = 2
    ) -> Dict[str, Any]:
        """Runs Candidate A: TTCA with Adaptive Aging (burst pacing) and FCFS tie-breaking."""
        return self.run_starveguard(
            detector=detector,
            aging_policy="adaptive",
            threshold=threshold,
            k_starve=k_base,
            max_boost=max_boost,
            floor=floor,
            tie_breaker="fcfs",
            policy_label="ttca_v2_cand_a"
        )

    def run_ttca_cand_b(
        self,
        detector: Optional[StarvationDetector] = None,
        threshold: int = 20,
        k_starve: int = 10,
        max_boost: int = 3,
        floor: int = 2
    ) -> Dict[str, Any]:
        """Runs Candidate B: TTCA with Shortest-Remaining-Time (SRTF) tie-breaking."""
        return self.run_starveguard(
            detector=detector,
            aging_policy="conservative",
            threshold=threshold,
            k_starve=k_starve,
            max_boost=max_boost,
            floor=floor,
            tie_breaker="srtf",
            policy_label="ttca_v2_cand_b"
        )

    def run_ttca_cand_c(
        self,
        detector: Optional[StarvationDetector] = None,
        threshold: int = 20,
        k_starve: int = 10,
        max_boost: int = 3,
        floor: int = 2,
        emergency_threshold: int = 40,
        aging_policy: str = "conservative"
    ) -> Dict[str, Any]:
        """Runs Candidate C: Dual-Tiered Hybrid TTCA (Emergency Anti-Starvation SRTF)."""
        return self.run_starveguard(
            detector=detector,
            aging_policy=aging_policy,
            threshold=threshold,
            k_starve=k_starve,
            max_boost=max_boost,
            floor=floor,
            tie_breaker="dual_tier",
            emergency_threshold=emergency_threshold,
            policy_label="ttca_v2_cand_c"
        )

    # =========================================================================
    # TTCA v2-B+ Advanced Optimization Variants (Phases 1-3)
    # =========================================================================

    def run_ttca_cand_b0(
        self,
        detector: Optional[StarvationDetector] = None,
        threshold: int = 20,
        k_starve: int = 10,
        max_boost: int = 3,
        floor: int = 2
    ) -> Dict[str, Any]:
        """Runs Candidate B0: Established Candidate B Baseline Control."""
        return self.run_starveguard(
            detector=detector,
            aging_policy="conservative",
            threshold=threshold,
            k_starve=k_starve,
            max_boost=max_boost,
            floor=floor,
            tie_breaker="srtf",
            policy_label="ttca_v2b_cand_b0"
        )

    def run_ttca_cand_b1(
        self,
        detector: Optional[StarvationDetector] = None,
        threshold: int = 20,
        k_base: int = 10,
        max_boost: int = 3,
        floor: int = 2
    ) -> Dict[str, Any]:
        """Runs Candidate B1: Queue-Pressure-Aware Aging."""
        return self.run_starveguard(
            detector=detector,
            aging_policy="queue_pressure",
            threshold=threshold,
            k_starve=k_base,
            max_boost=max_boost,
            floor=floor,
            tie_breaker="srtf",
            policy_label="ttca_v2b_cand_b1"
        )

    def run_ttca_cand_b2(
        self,
        detector: Optional[StarvationDetector] = None,
        threshold: int = 20,
        k_starve: int = 10,
        max_boost: int = 3,
        floor: int = 2,
        gamma: float = 0.05
    ) -> Dict[str, Any]:
        """Runs Candidate B2: Starvation-Aware SRTF Arbitration."""
        return self.run_starveguard(
            detector=detector,
            aging_policy="conservative",
            threshold=threshold,
            k_starve=k_starve,
            max_boost=max_boost,
            floor=floor,
            tie_breaker="starvation_aware_srtf",
            gamma=gamma,
            policy_label="ttca_v2b_cand_b2"
        )

    def run_ttca_cand_b3(
        self,
        detector: Optional[StarvationDetector] = None,
        threshold: int = 20,
        k_starve: int = 10,
        max_boost: int = 3,
        floor: int = 2
    ) -> Dict[str, Any]:
        """Runs Candidate B3: Preemption-Efficient Candidate B."""
        return self.run_starveguard(
            detector=detector,
            aging_policy="conservative",
            threshold=threshold,
            k_starve=k_starve,
            max_boost=max_boost,
            floor=floor,
            tie_breaker="srtf",
            preemption_hysteresis=True,
            policy_label="ttca_v2b_cand_b3"
        )

    def run_ttca_cand_b4(
        self,
        detector: Optional[StarvationDetector] = None,
        threshold: int = 20,
        k_base: int = 10,
        max_boost: int = 3,
        floor: int = 2,
        gamma: float = 0.05
    ) -> Dict[str, Any]:
        """Runs Candidate B4: Best Justified Hybrid (B1 Queue-Pressure + B2 Starvation-Aware SRTF + B3 Preemption Efficiency)."""
        return self.run_starveguard(
            detector=detector,
            aging_policy="queue_pressure",
            threshold=threshold,
            k_starve=k_base,
            max_boost=max_boost,
            floor=floor,
            tie_breaker="starvation_aware_srtf",
            gamma=gamma,
            preemption_hysteresis=True,
            policy_label="ttca_v2b_cand_b4"
        )
