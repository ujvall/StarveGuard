from comparison.comparator import SchedulerComparator
from scheduler.gantt import generate_gantt_chart


process_data = [
    ("P1", 0, 30, 6),
    ("P2", 0, 10, 8),
    ("P3", 0, 10, 9)
]

comparator = SchedulerComparator(process_data)

normal = comparator.run_normal()
starveguard = comparator.run_starveguard()

print("\nNORMAL PRIORITY")
generate_gantt_chart(normal["scheduler"].gantt_chart)

print("\nSTARVEGUARD")
generate_gantt_chart(starveguard["scheduler"].gantt_chart)

print("\nPROCESS RESULTS")

for p in starveguard["processes"]:
    print(
        p.pid,
        "Waiting:", p.waiting_time,
        "Original Priority:", p.original_priority,
        "Final Priority:", p.current_priority,
        "Aging Adjustments:", p.aging_adjustments
    )

print("\nAGING EVENTS")

for event in starveguard["scheduler"].aging_events:
    time, pid, old_priority, new_priority, score = event

    print(
        "Time:", time,
        "Process:", pid,
        "Priority:", old_priority, "->", new_priority,
        "Score:", score
    )

print("\nCOMPARISON")

print(
    "Average Waiting:",
    normal["average_waiting"],
    "->",
    starveguard["average_waiting"]
)

print(
    "Average Turnaround:",
    normal["average_turnaround"],
    "->",
    starveguard["average_turnaround"]
)

print(
    "Average Response:",
    normal["average_response"],
    "->",
    starveguard["average_response"]
)

print(
    "Maximum Waiting:",
    normal["maximum_waiting"],
    "->",
    starveguard["maximum_waiting"]
)

print(
    "Fairness:",
    normal["fairness"],
    "->",
    starveguard["fairness"]
)
