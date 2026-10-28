import unittest
from comparison.comparator import SchedulerComparator
from scheduler.process import Process


class TestSchedulerComparator(unittest.TestCase):

    def test_comparator_execution_and_exact_metrics(self):
        # Workload 1: Hand-verified 3-process workload
        # P1: (0, 20, 6), P2: (0, 5, 8), P3: (0, 5, 9)
        process_data = [
            ("P1", 0, 20, 6),
            ("P2", 0, 5, 8),
            ("P3", 0, 5, 9)
        ]

        comparator = SchedulerComparator(process_data)
        normal = comparator.run_normal()
        starveguard = comparator.run_starveguard()

        # Structural completeness
        for res in [normal, starveguard]:
            self.assertIn("processes", res)
            self.assertIn("scheduler", res)
            self.assertIn("average_waiting", res)
            self.assertIn("average_turnaround", res)
            self.assertIn("average_response", res)
            self.assertIn("maximum_waiting", res)
            self.assertIn("waiting_disparity", res)
            self.assertIn("fairness", res)

        # Exact hand-calculated values for Workload 1:
        # P1 runs 0..20 (CT=20, WT=0, TAT=20, RT=0)
        # P2 runs 20..25 (CT=25, WT=20, TAT=25, RT=20)
        # P3 runs 25..30 (CT=30, WT=25, TAT=30, RT=25)
        # Avg WT = (0 + 20 + 25) / 3 = 15.0
        # Avg TAT = (20 + 25 + 30) / 3 = 25.0
        # Avg RT = (0 + 20 + 25) / 3 = 15.0
        # Max WT = 25
        self.assertAlmostEqual(normal["average_waiting"], 15.0, places=2)
        self.assertAlmostEqual(normal["average_turnaround"], 25.0, places=2)
        self.assertAlmostEqual(normal["average_response"], 15.0, places=2)
        self.assertEqual(normal["maximum_waiting"], 25)
        self.assertEqual(normal["waiting_disparity"], 25)
        self.assertAlmostEqual(normal["fairness"], 0.5831, places=3)

        self.assertAlmostEqual(starveguard["average_waiting"], 15.0, places=2)
        self.assertAlmostEqual(starveguard["average_turnaround"], 25.0, places=2)
        self.assertAlmostEqual(starveguard["average_response"], 15.0, places=2)
        self.assertEqual(starveguard["maximum_waiting"], 25)
        self.assertEqual(starveguard["waiting_disparity"], 25)

        # StarveGuard specific metrics:
        # P2 and P3 cross starvation threshold (20) -> starved_processes = 2
        # P2 and P3 both receive aging boosts -> protected_processes = 2
        # P2 aged at t=10 and t=20; P3 aged at t=10 and t=20 -> total interventions = 4
        self.assertEqual(starveguard["starved_processes"], 2)
        self.assertEqual(starveguard["protected_processes"], 2)
        self.assertEqual(starveguard["aging_interventions"], 4)

    def test_independent_process_inputs(self):
        """Verify that normal and StarveGuard receive independent process instances."""
        process_data = [
            ("P1", 0, 5, 2),
            ("P2", 1, 3, 1)
        ]
        comparator = SchedulerComparator(process_data)
        normal = comparator.run_normal()
        starveguard = comparator.run_starveguard()

        # Memory references must be completely decoupled
        self.assertIsNot(normal["processes"][0], starveguard["processes"][0])
        self.assertIsNot(normal["processes"][1], starveguard["processes"][1])

        # State in one must not leak to the other
        normal["processes"][0].waiting_time = 999
        self.assertNotEqual(starveguard["processes"][0].waiting_time, 999)


if __name__ == "__main__":
    unittest.main()
