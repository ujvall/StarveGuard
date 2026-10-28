import unittest
from scheduler.process import Process


class TestProcess(unittest.TestCase):

    def test_process_initialization(self):
        p = Process(pid="P1", arrival_time=0, burst_time=8, original_priority=3)
        self.assertEqual(p.pid, "P1")
        self.assertEqual(p.arrival_time, 0)
        self.assertEqual(p.burst_time, 8)
        self.assertEqual(p.original_priority, 3)
        self.assertEqual(p.current_priority, 3)
        self.assertEqual(p.remaining_time, 8)
        self.assertEqual(p.waiting_time, 0)
        self.assertEqual(p.bypass_count, 0)
        self.assertEqual(p.response_time, -1)
        self.assertEqual(p.first_run_time, -1)
        self.assertFalse(p.starvation_detected)
        self.assertEqual(p.aging_adjustments, 0)

    def test_process_clone(self):
        p = Process(pid="P1", arrival_time=2, burst_time=10, original_priority=4)
        p.remaining_time = 5
        p.current_priority = 2
        p.waiting_time = 7

        clone = p.clone()
        self.assertEqual(clone.pid, "P1")
        self.assertEqual(clone.arrival_time, 2)
        self.assertEqual(clone.burst_time, 10)
        self.assertEqual(clone.original_priority, 4)
        # Fresh clone starts with fresh remaining_time and current_priority
        self.assertEqual(clone.remaining_time, 10)
        self.assertEqual(clone.current_priority, 4)
        self.assertEqual(clone.waiting_time, 0)


if __name__ == "__main__":
    unittest.main()
