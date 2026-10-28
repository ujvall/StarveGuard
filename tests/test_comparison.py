import unittest
from comparison.comparator import SchedulerComparator


class TestSchedulerComparator(unittest.TestCase):

    def test_comparator_execution(self):
        process_data = [
            ("P1", 0, 20, 6),
            ("P2", 0, 5, 8),
            ("P3", 0, 5, 9)
        ]

        comparator = SchedulerComparator(process_data)
        normal = comparator.run_normal()
        starveguard = comparator.run_starveguard()

        # Both runs must contain complete results
        for res in [normal, starveguard]:
            self.assertIn("processes", res)
            self.assertIn("scheduler", res)
            self.assertIn("average_waiting", res)
            self.assertIn("average_turnaround", res)
            self.assertIn("average_response", res)
            self.assertIn("maximum_waiting", res)
            self.assertIn("fairness", res)

        # StarveGuard specific metrics
        self.assertIn("starved_processes", starveguard)
        self.assertIn("protected_processes", starveguard)
        self.assertIn("aging_interventions", starveguard)

        # Independent process instances
        self.assertIsNot(normal["processes"][0], starveguard["processes"][0])


if __name__ == "__main__":
    unittest.main()
