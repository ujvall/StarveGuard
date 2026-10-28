import unittest
from scheduler.process import Process
from scheduler.priority_scheduler import PriorityScheduler


class TestAgingPrevention(unittest.TestCase):

    def test_aging_prevention_events(self):
        processes = [
            Process("P1", 0, 20, 6),
            Process("P2", 0, 5, 8),
            Process("P3", 0, 5, 9)
        ]

        scheduler = PriorityScheduler(processes)
        gantt = scheduler.run()

        self.assertGreater(len(gantt), 0)
        self.assertGreater(len(scheduler.aging_events), 0)

        # Verify aging event structure: (time, pid, old_prio, new_prio, score)
        for event in scheduler.aging_events:
            t, pid, old_p, new_p, score = event
            self.assertGreaterEqual(t, 0)
            self.assertIn(pid, ["P1", "P2", "P3"])
            self.assertGreater(old_p, new_p)  # Lower number = higher priority
            self.assertGreaterEqual(score, 10)


if __name__ == "__main__":
    unittest.main()
