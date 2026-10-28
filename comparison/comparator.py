from typing import Any, Dict, List, Tuple, Union
from scheduler.process import Process
from scheduler.normal_priority_scheduler import NormalPriorityScheduler
from scheduler.priority_scheduler import PriorityScheduler
from starvation.detector import StarvationDetector
from metrics.calculator import MetricsCalculator


class SchedulerComparator:
    """
    Executes controlled comparisons between standard Preemptive Priority Scheduling
    and StarveGuard Adaptive Priority Scheduling on identical process workloads.
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
        detector: StarvationDetector = None
    ) -> Dict[str, Any]:
        processes = self.create_processes()
        scheduler = PriorityScheduler(processes, detector=detector)
        scheduler.run()

        metrics = MetricsCalculator(processes)

        return {
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
