from scheduler.process import Process
from scheduler.normal_priority_scheduler import NormalPriorityScheduler
from scheduler.priority_scheduler import PriorityScheduler
from starvation.detector import StarvationDetector
from metrics.calculator import MetricsCalculator


class SchedulerComparator:

    def __init__(self, process_data):
        self.process_data = process_data

    def create_processes(self):
        return [
            Process(pid, arrival, burst, priority)
            for pid, arrival, burst, priority in self.process_data
        ]

    def run_normal(self):
        processes = self.create_processes()
        scheduler = NormalPriorityScheduler(processes)
        scheduler.run()

        metrics = MetricsCalculator(processes)

        return {
            "processes": processes,
            "scheduler": scheduler,
            "average_waiting": metrics.average_waiting_time(),
            "average_turnaround": metrics.average_turnaround_time(),
            "average_response": metrics.average_response_time(),
            "maximum_waiting": metrics.maximum_waiting_time(),
            "fairness": metrics.fairness_index()
        }

    def run_starveguard(self):
        processes = self.create_processes()
        scheduler = PriorityScheduler(processes)
        scheduler.run()

        metrics = MetricsCalculator(processes)

        return {
            "processes": processes,
            "scheduler": scheduler,
            "average_waiting": metrics.average_waiting_time(),
            "average_turnaround": metrics.average_turnaround_time(),
            "average_response": metrics.average_response_time(),
            "maximum_waiting": metrics.maximum_waiting_time(),
            "starved_processes": metrics.starved_process_count(),
            "protected_processes": metrics.protected_process_count(),
            "aging_interventions": metrics.aging_intervention_count(scheduler),
            "fairness": metrics.fairness_index()
        }
