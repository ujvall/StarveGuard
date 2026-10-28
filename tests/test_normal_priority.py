import unittest
from scheduler.process import Process
from scheduler.normal_priority_scheduler import NormalPriorityScheduler


class TestNormalPriorityScheduler(unittest.TestCase):

    def test_strict_priority_execution(self):
        # P1 priority 6 (low), P2 priority 2 (high), P3 priority 4 (mid)
        processes = [
            Process("P1", 0, 4, 6),
            Process("P2", 0, 3, 2),
            Process("P3", 0, 3, 4)
        ]
        scheduler = NormalPriorityScheduler(processes)
        scheduler.run()

        # In normal priority: P2 (0..3), P3 (3..6), P1 (6..10)
        p1 = [p for p in processes if p.pid == "P1"][0]
        p2 = [p for p in processes if p.pid == "P2"][0]
        p3 = [p for p in processes if p.pid == "P3"][0]

        self.assertEqual(p2.completion_time, 3)
        self.assertEqual(p2.waiting_time, 0)
        self.assertEqual(p2.response_time, 0)

        self.assertEqual(p3.completion_time, 6)
        self.assertEqual(p3.waiting_time, 3)
        self.assertEqual(p3.response_time, 3)

        self.assertEqual(p1.completion_time, 10)
        self.assertEqual(p1.waiting_time, 6)
        self.assertEqual(p1.response_time, 6)

    def test_preemption_on_higher_priority_arrival(self):
        # P1 arrives at 0 with priority 5, burst 6.
        # P2 arrives at 2 with priority 2, burst 2 (preempts P1).
        processes = [
            Process("P1", 0, 6, 5),
            Process("P2", 2, 2, 2)
        ]
        scheduler = NormalPriorityScheduler(processes)
        scheduler.run()

        p1 = [p for p in processes if p.pid == "P1"][0]
        p2 = [p for p in processes if p.pid == "P2"][0]

        # P1 runs 0..2, preempted by P2 at 2..4, P1 finishes 4..8
        self.assertEqual(p2.first_run_time, 2)
        self.assertEqual(p2.response_time, 0)
        self.assertEqual(p2.completion_time, 4)

        self.assertEqual(p1.first_run_time, 0)
        self.assertEqual(p1.response_time, 0)
        self.assertEqual(p1.completion_time, 8)
        self.assertEqual(p1.waiting_time, 2)
        self.assertEqual(p1.turnaround_time, 8)
        self.assertEqual(p1.waiting_time, p1.turnaround_time - p1.burst_time)


if __name__ == "__main__":
    unittest.main()
