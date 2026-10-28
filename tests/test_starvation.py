import unittest
from scheduler.process import Process
from scheduler.priority_scheduler import PriorityScheduler
from starvation.detector import StarvationDetector


class TestStarvationDetection(unittest.TestCase):

    def test_starvation_detection_flagging(self):
        # Long job P1 (burst 30, priority 1) keeps CPU while P2 (prio 8) and P3 (prio 9) wait
        processes = [
            Process("P1", 0, 30, 1),
            Process("P2", 0, 5, 8),
            Process("P3", 0, 5, 9)
        ]

        scheduler = PriorityScheduler(processes)
        scheduler.run()

        p2 = [p for p in processes if p.pid == "P2"][0]
        p3 = [p for p in processes if p.pid == "P3"][0]

        # P2 waited 30 units, P3 waited 35 units -> both >= threshold 20
        self.assertTrue(p2.starvation_detected)
        self.assertTrue(p3.starvation_detected)
        self.assertEqual(p2.aging_adjustments, 3)
        self.assertEqual(p3.aging_adjustments, 3)


if __name__ == "__main__":
    unittest.main()
