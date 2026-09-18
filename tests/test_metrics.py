from scheduler.process import Process
from scheduler.priority_scheduler import PriorityScheduler
from starvation.detector import StarvationDetector
from metrics.calculator import MetricsCalculator

processes = [
    Process("P1", 0, 20, 6),
    Process("P2", 0, 5, 8),
    Process("P3", 0, 5, 9)
]

scheduler = PriorityScheduler(processes)
scheduler.run()

detector = StarvationDetector()
metrics = MetricsCalculator(processes)

print("Average Waiting Time:", metrics.average_waiting_time())
print("Average Turnaround Time:", metrics.average_turnaround_time())
print("Average Response Time:", metrics.average_response_time())
print("Maximum Waiting Time:", metrics.maximum_waiting_time())
print("Starved Process Count:", metrics.starved_process_count(detector))
print("Aging Intervention Count:", metrics.aging_intervention_count(scheduler))
