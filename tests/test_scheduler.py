import unittest
from scheduler.process import Process
from scheduler.priority_scheduler import PriorityScheduler


class TestPriorityScheduler(unittest.TestCase):

    def test_starveguard_preemption_and_aging(self):
        # Workload where P1 has burst 20, priority 6.
        # P2 has burst 5, priority 8.
        # P3 has burst 5, priority 9.
        processes = [
            Process("P1", 0, 20, 6),
            Process("P2", 0, 5, 8),
            Process("P3", 0, 5, 9)
        ]
        scheduler = PriorityScheduler(processes)
        scheduler.run()

        p1 = [p for p in processes if p.pid == "P1"][0]
        p2 = [p for p in processes if p.pid == "P2"][0]
        p3 = [p for p in processes if p.pid == "P3"][0]

        # Verify all processes completed
        self.assertEqual(p1.remaining_time, 0)
        self.assertEqual(p2.remaining_time, 0)
        self.assertEqual(p3.remaining_time, 0)

        # Check WT = TAT - BT consistency
        self.assertEqual(p1.waiting_time, p1.turnaround_time - p1.burst_time)
        self.assertEqual(p2.waiting_time, p2.turnaround_time - p2.burst_time)
        self.assertEqual(p3.waiting_time, p3.turnaround_time - p3.burst_time)

        # Check that aging was applied
        self.assertGreater(p2.aging_adjustments, 0)
        self.assertGreater(p3.aging_adjustments, 0)
        self.assertGreater(len(scheduler.aging_events), 0)


if __name__ == "__main__":
    unittest.main()
