import unittest
from scheduler.process import Process
from starvation.detector import StarvationDetector


class TestStarvationDetector(unittest.TestCase):

    def test_default_waiting_time_score(self):
        # Default bypass_weight=0 ensures score equals queue waiting time
        detector = StarvationDetector(threshold=20, bypass_weight=0)
        p = Process("P1", 0, 10, 5)
        p.waiting_time = 15
        p.bypass_count = 3
        self.assertEqual(detector.calculate_score(p), 15)
        self.assertFalse(detector.is_starving(p))

        p.waiting_time = 20
        self.assertEqual(detector.calculate_score(p), 20)
        self.assertTrue(detector.is_starving(p))

    def test_weighted_bypass_score(self):
        # Optional weighted bypass count
        detector = StarvationDetector(threshold=20, bypass_weight=2)
        p = Process("P1", 0, 10, 5)
        p.waiting_time = 12
        p.bypass_count = 4
        # score = 12 + 4 * 2 = 20
        self.assertEqual(detector.calculate_score(p), 20)
        self.assertTrue(detector.is_starving(p))

    def test_threshold_boundary(self):
        detector = StarvationDetector(threshold=20)
        p = Process("P1", 0, 10, 5)
        p.waiting_time = 19
        self.assertFalse(detector.is_starving(p))
        p.waiting_time = 20
        self.assertTrue(detector.is_starving(p))
        p.waiting_time = 21
        self.assertTrue(detector.is_starving(p))


if __name__ == "__main__":
    unittest.main()
