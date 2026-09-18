from comparison.comparator import SchedulerComparator
from scheduler.gantt import generate_gantt_chart


def get_processes():
    processes = []

    n = int(input("Enter number of processes: "))

    for i in range(n):
        print(f"\nProcess P{i + 1}")

        arrival = int(input("Arrival Time: "))
        burst = int(input("Burst Time: "))
        priority = int(input("Priority: "))

        processes.append(
            (f"P{i + 1}", arrival, burst, priority)
        )

    return processes


process_data = get_processes()

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
print("Fairness:", normal["fairness"])

print("\nSTARVEGUARD")
print("Average Waiting:", starveguard["average_waiting"])
print("Average Turnaround:", starveguard["average_turnaround"])
print("Average Response:", starveguard["average_response"])
print("Maximum Waiting:", starveguard["maximum_waiting"])
print("Fairness:", starveguard["fairness"])
print("Starved Processes:", starveguard["starved_processes"])
print("Protected Processes:", starveguard["protected_processes"])
print("Aging Interventions:", starveguard["aging_interventions"])

print("\nSTARVEGUARD PROCESS RESULTS")

for p in starveguard["processes"]:
    print(
        p.pid,
        "Completion:", p.completion_time,
        "Waiting:", p.waiting_time,
        "Turnaround:", p.turnaround_time,
        "Response:", p.response_time,
        "Original Priority:", p.original_priority,
        "Final Priority:", p.current_priority,
        "Bypass:", p.bypass_count,
        "Aging Adjustments:", p.aging_adjustments
    )

print("\nAGING EVENTS")

for event in starveguard["scheduler"].aging_events:
    time, pid, old_priority, new_priority, score = event

    print(
        "Time:", time,
        "Process:", pid,
        "Priority:", old_priority, "->", new_priority,
        "Starvation Score:", score
    )

print("\nCOMPARISON")

print(
    "Average Waiting Change:",
    starveguard["average_waiting"] - normal["average_waiting"]
)

print(
    "Average Turnaround Change:",
    starveguard["average_turnaround"] - normal["average_turnaround"]
)

print(
    "Average Response Change:",
    starveguard["average_response"] - normal["average_response"]
)

print(
    "Maximum Waiting Change:",
    starveguard["maximum_waiting"] - normal["maximum_waiting"]
)

print(
    "Fairness Change:",
    starveguard["fairness"] - normal["fairness"]
)
