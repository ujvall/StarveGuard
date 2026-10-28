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

    def test_all_workloads_completion_and_invariants(self):
        for name, data in WORKLOADS.items():
            comparator = SchedulerComparator(data)
            normal = comparator.run_normal()
            starveguard = comparator.run_starveguard()

            # Verify all processes completed and satisfied conservation invariants
            for p in normal["processes"]:
                self.assertEqual(p.remaining_time, 0, f"{name}: normal {p.pid} did not finish")
                self.assertEqual(p.waiting_time, p.turnaround_time - p.burst_time)
                self.assertEqual(p.turnaround_time, p.completion_time - p.arrival_time)

            for p in starveguard["processes"]:
                self.assertEqual(p.remaining_time, 0, f"{name}: SG {p.pid} did not finish")
                self.assertEqual(p.waiting_time, p.turnaround_time - p.burst_time)
                self.assertEqual(p.turnaround_time, p.completion_time - p.arrival_time)

            self.assertGreaterEqual(normal["fairness"], 0.0)
            self.assertLessEqual(normal["fairness"], 1.0)
            self.assertGreaterEqual(starveguard["fairness"], 0.0)
            self.assertLessEqual(starveguard["fairness"], 1.0)

    def test_workload_4_exact_sequential_values(self):
        # Workload 4 is completely non-contested:
        # P1 runs 3..7 (WT=0, TAT=4, RT=0)
        # P2 runs 7..10 (WT=0, TAT=3, RT=0)
        # P3 runs 10..12 (WT=0, TAT=2, RT=0)
        comp = SchedulerComparator(WORKLOADS["Workload 4"])
        norm = comp.run_normal()
        sg = comp.run_starveguard()

        self.assertEqual(norm["average_waiting"], 0.0)
        self.assertEqual(norm["average_turnaround"], 3.0)
        self.assertEqual(norm["average_response"], 0.0)
        self.assertEqual(norm["maximum_waiting"], 0)
        self.assertEqual(norm["fairness"], 1.0)

        self.assertEqual(sg["average_waiting"], 0.0)
        self.assertEqual(sg["average_turnaround"], 3.0)
        self.assertEqual(sg["average_response"], 0.0)
        self.assertEqual(sg["maximum_waiting"], 0)
        self.assertEqual(sg["fairness"], 1.0)
        self.assertEqual(sg["starved_processes"], 0)
        self.assertEqual(sg["protected_processes"], 0)
        self.assertEqual(sg["aging_interventions"], 0)

    def test_workload_2_exact_staggered_values(self):
        # Workload 2: Hand-calculated staggered preemption
        # P1 (0..1, resumes 5..12: WT=4, TAT=12, RT=0)
        # P2 (runs 1..5: WT=0, TAT=4, RT=0)
        # P3 (runs 12..15: WT=10, TAT=13, RT=10, boosted from prio 4 to 3 at t=12)
        # P4 (runs 15..20: WT=11, TAT=16, RT=11, boosted from prio 8 to 7 at t=14)
        comp = SchedulerComparator(WORKLOADS["Workload 2"])
        norm = comp.run_normal()
        sg = comp.run_starveguard()

        # Avg WT = (4 + 0 + 10 + 11) / 4 = 6.25
        # Avg TAT = (12 + 4 + 13 + 16) / 4 = 11.25
        # Avg RT = (0 + 0 + 10 + 11) / 4 = 5.25
        # Max WT = 11
        self.assertAlmostEqual(norm["average_waiting"], 6.25, places=2)
        self.assertAlmostEqual(norm["average_turnaround"], 11.25, places=2)
        self.assertAlmostEqual(norm["average_response"], 5.25, places=2)
        self.assertEqual(norm["maximum_waiting"], 11)

        self.assertAlmostEqual(sg["average_waiting"], 6.25, places=2)
        self.assertAlmostEqual(sg["average_turnaround"], 11.25, places=2)
        self.assertAlmostEqual(sg["average_response"], 5.25, places=2)
        self.assertEqual(sg["maximum_waiting"], 11)
        self.assertEqual(sg["starved_processes"], 0)
        self.assertEqual(sg["protected_processes"], 2)
        self.assertEqual(sg["aging_interventions"], 2)


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
