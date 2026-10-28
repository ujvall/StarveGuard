import unittest
from scheduler.process import Process
from aging.aging_manager import AgingManager


class TestAgingManager(unittest.TestCase):

    def setUp(self):
        self.aging = AgingManager()

    def test_score_boundaries_boost_calculation(self):
        # Score < 10 -> boost 0
        self.assertEqual(self.aging.calculate_boost(0), 0)
        self.assertEqual(self.aging.calculate_boost(9), 0)
        # Score 10..19 -> boost 1
        self.assertEqual(self.aging.calculate_boost(10), 1)
        self.assertEqual(self.aging.calculate_boost(19), 1)
        # Score 20..29 -> boost 2
        self.assertEqual(self.aging.calculate_boost(20), 2)
        self.assertEqual(self.aging.calculate_boost(29), 2)
        # Score >= 30 -> boost 3
        self.assertEqual(self.aging.calculate_boost(30), 3)
        self.assertEqual(self.aging.calculate_boost(100), 3)

    def test_apply_aging_and_adjustments_count(self):
        p = Process("P1", 0, 5, 8)
        # Score 5 -> boost 0, no adjustment
        adjusted = self.aging.apply_aging(p, 5)
        self.assertFalse(adjusted)
        self.assertEqual(p.current_priority, 8)
        self.assertEqual(p.aging_adjustments, 0)

        # Score 12 -> boost 1, priority becomes 7
        adjusted = self.aging.apply_aging(p, 12)
        self.assertTrue(adjusted)
        self.assertEqual(p.current_priority, 7)
        self.assertEqual(p.aging_adjustments, 1)

        # Score 15 -> same tier (boost 1), no re-adjustment
        adjusted = self.aging.apply_aging(p, 15)
        self.assertFalse(adjusted)
        self.assertEqual(p.current_priority, 7)
        self.assertEqual(p.aging_adjustments, 1)

        # Score 20 -> tier 2 (boost 2), priority becomes 6
        adjusted = self.aging.apply_aging(p, 20)
        self.assertTrue(adjusted)
        self.assertEqual(p.current_priority, 6)
        self.assertEqual(p.aging_adjustments, 2)

        # Score 35 -> tier 3 (boost 3), priority becomes 5
        adjusted = self.aging.apply_aging(p, 35)
        self.assertTrue(adjusted)
        self.assertEqual(p.current_priority, 5)
        self.assertEqual(p.aging_adjustments, 3)

    def test_priority_one_floor(self):
        p = Process("P_top", 0, 5, 1)
        adjusted = self.aging.apply_aging(p, 50)
        # Cannot go below priority 1
        self.assertFalse(adjusted)
        self.assertEqual(p.current_priority, 1)
        self.assertEqual(p.aging_adjustments, 0)


if __name__ == "__main__":
    unittest.main()
