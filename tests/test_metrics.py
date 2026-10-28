import unittest
from scheduler.process import Process
from scheduler.priority_scheduler import PriorityScheduler
from starvation.detector import StarvationDetector
from metrics.calculator import MetricsCalculator


class TestMetricsCalculator(unittest.TestCase):

    def test_metrics_calculation(self):
        processes = [
            Process("P1", 0, 20, 6),
            Process("P2", 0, 5, 8),
            Process("P3", 0, 5, 9)
        ]
        scheduler = PriorityScheduler(processes)
        scheduler.run()

        detector = StarvationDetector()
        metrics = MetricsCalculator(processes)

        avg_wait = metrics.average_waiting_time()
        avg_tat = metrics.average_turnaround_time()
        avg_resp = metrics.average_response_time()
        max_wait = metrics.maximum_waiting_time()

        self.assertGreaterEqual(avg_wait, 0.0)
        self.assertGreaterEqual(avg_tat, avg_wait)
        self.assertGreaterEqual(avg_resp, 0.0)
        self.assertGreaterEqual(max_wait, avg_wait)

        # starved_process_count must accept detector as optional argument without crashing
        starved_count_with_arg = metrics.starved_process_count(detector)
        starved_count_no_arg = metrics.starved_process_count()
        self.assertIsInstance(starved_count_with_arg, int)
        self.assertIsInstance(starved_count_no_arg, int)

        interventions = metrics.aging_intervention_count(scheduler)
        self.assertEqual(interventions, len(scheduler.aging_events))

    def test_empty_workload_safety(self):
        metrics = MetricsCalculator([])
        self.assertEqual(metrics.average_waiting_time(), 0.0)
        self.assertEqual(metrics.average_turnaround_time(), 0.0)
        self.assertEqual(metrics.average_response_time(), 0.0)
        self.assertEqual(metrics.maximum_waiting_time(), 0)
        self.assertEqual(metrics.waiting_time_disparity(), 0)
        self.assertEqual(metrics.fairness_index(), 1.0)
        self.assertEqual(metrics.starved_process_count(), 0)
        self.assertEqual(metrics.protected_process_count(), 0)


if __name__ == "__main__":
    unittest.main()
