import sys
from comparison.comparator import SchedulerComparator
from scheduler.gantt import generate_gantt_chart


def get_processes():
    # If stdin is not a tty or --demo is supplied, load standard demonstration workload
    if "--demo" in sys.argv or not sys.stdin.isatty():
        print("Loading default demonstration workload (P1-P4)...")
        return [
            ("P1", 0, 15, 6),
            ("P2", 0, 5, 3),
            ("P3", 5, 5, 3),
            ("P4", 10, 5, 3)
        ]

    processes = []
    try:
        raw_n = input("Enter number of processes: ").strip()
        if not raw_n:
            print("No input provided. Loading default demonstration workload...")
            return [
                ("P1", 0, 15, 6),
                ("P2", 0, 5, 3),
                ("P3", 5, 5, 3),
                ("P4", 10, 5, 3)
            ]
        n = int(raw_n)
        for i in range(n):
            print(f"\nProcess P{i + 1}")
            arrival = int(input("Arrival Time: ").strip())
            burst = int(input("Burst Time: ").strip())
            priority = int(input("Priority (lower = higher priority): ").strip())
            processes.append((f"P{i + 1}", arrival, burst, priority))
        return processes
    except (EOFError, ValueError) as e:
        print(f"Interactive input ended or invalid ({e}). Using demonstration workload.")
        return [
            ("P1", 0, 15, 6),
            ("P2", 0, 5, 3),
            ("P3", 5, 5, 3),
            ("P4", 10, 5, 3)
        ]


def main():
    process_data = get_processes()

    comparator = SchedulerComparator(process_data)

    normal = comparator.run_normal()
    starveguard = comparator.run_starveguard()

    print("\nNORMAL PRIORITY GANTT")
    generate_gantt_chart(normal["scheduler"].gantt_chart)

    print("\nSTARVEGUARD GANTT")
    generate_gantt_chart(starveguard["scheduler"].gantt_chart)

    print("\nNORMAL PRIORITY")
    print(f"Average Waiting: {normal['average_waiting']:.2f}")
    print(f"Average Turnaround: {normal['average_turnaround']:.2f}")
    print(f"Average Response: {normal['average_response']:.2f}")
    print(f"Maximum Waiting: {normal['maximum_waiting']}")
    print(f"Fairness Index: {normal['fairness']:.4f}")

    print("\nSTARVEGUARD")
    print(f"Average Waiting: {starveguard['average_waiting']:.2f}")
    print(f"Average Turnaround: {starveguard['average_turnaround']:.2f}")
    print(f"Average Response: {starveguard['average_response']:.2f}")
    print(f"Maximum Waiting: {starveguard['maximum_waiting']}")
    print(f"Fairness Index: {starveguard['fairness']:.4f}")
    print(f"Starvation Threshold Crossings: {starveguard['starved_processes']}")
    print(f"Protected Processes: {starveguard['protected_processes']}")
    print(f"Aging Interventions: {starveguard['aging_interventions']}")

    print("\nSTARVEGUARD PROCESS RESULTS")
    for p in starveguard["processes"]:
        print(
            f"{p.pid} | Arrival: {p.arrival_time} | Burst: {p.burst_time} | "
            f"Completion: {p.completion_time} | Waiting: {p.waiting_time} | "
            f"Turnaround: {p.turnaround_time} | Response: {p.response_time} | "
            f"Orig Prio: {p.original_priority} | Final Prio: {p.current_priority} | "
            f"Bypass: {p.bypass_count} | Aging Adjustments: {p.aging_adjustments}"
        )

    print("\nAGING EVENTS")
    for event in starveguard["scheduler"].aging_events:
        time, pid, old_priority, new_priority, score = event
        print(
            f"Time: {time:<3} | Process: {pid:<4} | Priority: {old_priority} -> {new_priority} | "
            f"Starvation Score: {score}"
        )

    print("\nCOMPARISON (STARVEGUARD - NORMAL)")
    print(f"Average Waiting Change: {starveguard['average_waiting'] - normal['average_waiting']:+.2f}")
    print(f"Average Turnaround Change: {starveguard['average_turnaround'] - normal['average_turnaround']:+.2f}")
    print(f"Average Response Change: {starveguard['average_response'] - normal['average_response']:+.2f}")
    print(f"Maximum Waiting Change: {starveguard['maximum_waiting'] - normal['maximum_waiting']:+d}")
    print(f"Fairness Change: {starveguard['fairness'] - normal['fairness']:+.4f}")


if __name__ == "__main__":
    main()
