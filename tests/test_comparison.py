from comparison.comparator import SchedulerComparator
from scheduler.gantt import generate_gantt_chart

process_data = [
    ("P1", 0, 20, 6),
    ("P2", 0, 5, 8),
    ("P3", 0, 5, 9)
]

comparator = SchedulerComparator(process_data)

normal = comparator.run_normal()
starveguard = comparator.run_starveguard()

print("\nNORMAL PRIORITY GANTT")
generate_gantt_chart(normal["scheduler"].gantt_chart)

print("\nSTARVEGUARD GANTT")
generate_gantt_chart(starveguard["scheduler"].gantt_chart)

print("\nNORMAL PRIORITY")
print("Average Waiting:", normal["average_waiting"])
print("Average Turnaround:", normal["average_turnaround"])
print("Average Response:", normal["average_response"])
print("Maximum Waiting:", normal["maximum_waiting"])

print("\nSTARVEGUARD")
print("Average Waiting:", starveguard["average_waiting"])
print("Average Turnaround:", starveguard["average_turnaround"])
print("Average Response:", starveguard["average_response"])
print("Maximum Waiting:", starveguard["maximum_waiting"])
print("Starved Processes:", starveguard["starved_processes"])
print("Aging Interventions:", starveguard["aging_interventions"])
