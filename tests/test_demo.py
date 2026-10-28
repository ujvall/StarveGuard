import unittest
from comparison.comparator import SchedulerComparator


class TestDemoWorkload(unittest.TestCase):

    def test_demo_execution(self):
        process_data = [
            ("P1", 0, 15, 6),
            ("P2", 0, 5, 3),
            ("P3", 5, 5, 3),
            ("P4", 10, 5, 3)
        ]

        comparator = SchedulerComparator(process_data)
        normal = comparator.run_normal()
        starveguard = comparator.run_starveguard()

        # Both runs finish all jobs
        for p in normal["processes"]:
            self.assertEqual(p.remaining_time, 0)
        for p in starveguard["processes"]:
            self.assertEqual(p.remaining_time, 0)

        # StarveGuard P1 waited while P2, P3 ran and received aging
        p1 = [p for p in starveguard["processes"] if p.pid == "P1"][0]
        self.assertGreater(p1.aging_adjustments, 0)
        self.assertLess(p1.current_priority, p1.original_priority)


if __name__ == "__main__":
    unittest.main()
