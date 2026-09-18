import csv
from comparison.comparator import SchedulerComparator


workloads = {
    "Workload 1": [
        ("P1", 0, 20, 6),
        ("P2", 0, 5, 8),
        ("P3", 0, 5, 9)
    ],
    "Workload 2": [
        ("P1", 0, 8, 3),
        ("P2", 1, 4, 1),
        ("P3", 2, 3, 4),
        ("P4", 4, 5, 8)
    ],
    "Workload 3": [
        ("P1", 0, 30, 6),
        ("P2", 0, 10, 8),
        ("P3", 0, 10, 9)
    ],
    "Workload 4": [
        ("P1", 3, 4, 2),
        ("P2", 7, 3, 1),
        ("P3", 10, 2, 3)
    ]
}

results = []

for name, process_data in workloads.items():

    comparator = SchedulerComparator(process_data)

    normal = comparator.run_normal()
    starveguard = comparator.run_starveguard()

    results.append([
        name,
        normal["average_waiting"],
        starveguard["average_waiting"],
        normal["average_turnaround"],
        starveguard["average_turnaround"],
        normal["average_response"],
        starveguard["average_response"],
        normal["maximum_waiting"],
        starveguard["maximum_waiting"],
        normal["fairness"],
        starveguard["fairness"],
        starveguard["starved_processes"],
        starveguard["protected_processes"],
        starveguard["aging_interventions"]
    ])

    print(f"\n{name}")
    print("-" * 40)

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

    print(
        "Starved Processes:",
        starveguard["starved_processes"]
    )

    print(
        "Protected Processes:",
        starveguard["protected_processes"]
    )

    print(
        "Aging Interventions:",
        starveguard["aging_interventions"]
    )

with open("results/workload_results.csv", "w", newline="") as file:
    writer = csv.writer(file)

    writer.writerow([
        "Workload",
        "Normal Avg Waiting",
        "StarveGuard Avg Waiting",
        "Normal Avg Turnaround",
        "StarveGuard Avg Turnaround",
        "Normal Avg Response",
        "StarveGuard Avg Response",
        "Normal Max Waiting",
        "StarveGuard Max Waiting",
        "Normal Fairness",
        "StarveGuard Fairness",
        "Starved Processes",
        "Protected Processes",
        "Aging Interventions"
    ])

    writer.writerows(results)

print("\nResults saved to results/workload_results.csv")
