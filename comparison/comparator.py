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
            "protected_processes": 0,
            "aging_interventions": 0,
            "fairness": metrics.fairness_index()
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
        aging_manager: Optional[AgingManager] = None
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

        scheduler = PriorityScheduler(processes, detector=detector, aging_manager=aging_manager)
        scheduler.run()

        metrics = MetricsCalculator(processes)

        return {
            "policy": aging_manager.policy_name,
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
            "starved_processes": metrics.starved_process_count(),
            "protected_processes": metrics.protected_process_count(),
            "priority_changed_count": metrics.priority_changed_count(),
            "aging_interventions": metrics.aging_intervention_count(scheduler),
            "fairness": metrics.fairness_index()
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
            floor=floor
        )
