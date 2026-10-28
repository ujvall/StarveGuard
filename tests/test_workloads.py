import csv
import unittest
from comparison.comparator import SchedulerComparator


WORKLOADS = {
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


class TestWorkloadBenchmarks(unittest.TestCase):

    def test_all_workloads_completion(self):
        for name, data in WORKLOADS.items():
            comparator = SchedulerComparator(data)
            normal = comparator.run_normal()
            starveguard = comparator.run_starveguard()

            # Verify all processes completed
            for p in normal["processes"]:
                self.assertEqual(p.remaining_time, 0, f"{name}: normal {p.pid} did not finish")
                self.assertEqual(p.waiting_time, p.turnaround_time - p.burst_time)

            for p in starveguard["processes"]:
                self.assertEqual(p.remaining_time, 0, f"{name}: SG {p.pid} did not finish")
                self.assertEqual(p.waiting_time, p.turnaround_time - p.burst_time)

            self.assertGreaterEqual(normal["fairness"], 0.0)
            self.assertLessEqual(normal["fairness"], 1.0)
            self.assertGreaterEqual(starveguard["fairness"], 0.0)
            self.assertLessEqual(starveguard["fairness"], 1.0)


def generate_results_csv(output_path="results/workload_results.csv"):
    results = []
    for name, data in WORKLOADS.items():
        comparator = SchedulerComparator(data)
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

    with open(output_path, "w", newline="") as file:
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

    print(f"Results saved to {output_path}")


if __name__ == "__main__":
    generate_results_csv()
    unittest.main()
