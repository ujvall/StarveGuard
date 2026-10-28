import unittest
from scheduler.process import Process
from scheduler.normal_priority_scheduler import NormalPriorityScheduler
from scheduler.priority_scheduler import PriorityScheduler
from scheduler.gantt import extract_gantt_segments
from starvation.detector import StarvationDetector
from aging.aging_manager import AgingManager
from metrics.calculator import MetricsCalculator
from comparison.comparator import SchedulerComparator


class TestAlgorithmRegressionSuite(unittest.TestCase):
    """
    Comprehensive regression test suite verifying all 16 algorithmic edge cases
    identified during the academic correctness audit.
    """

    # 1. A process arriving after an idle CPU period.
    def test_01_process_arriving_after_idle_period(self):
        # CPU is idle from t=0 to t=5, then P1 arrives at t=5 and runs for 3 units
        p1 = Process("P1", arrival_time=5, burst_time=3, original_priority=2)
        sched = PriorityScheduler([p1])
        sched.run()

        self.assertEqual(p1.first_run_time, 5)
        self.assertEqual(p1.completion_time, 8)
        self.assertEqual(p1.waiting_time, 0)
        self.assertEqual(p1.turnaround_time, 3)

        # Gantt segments must show IDLE from 0 to 5 and P1 from 5 to 8
        segments = extract_gantt_segments(sched.gantt_chart)
        self.assertEqual(segments, [("IDLE", 0, 5), ("P1", 5, 8)])

    # 2. Processes arriving at different times.
    def test_02_processes_arriving_at_different_times(self):
        # P1 arrives at 0 (burst 4, prio 3)
        # P2 arrives at 2 (burst 2, prio 1) -> preempts P1 at t=2
        # P3 arrives at 6 (burst 2, prio 2)
        procs = [
            Process("P1", 0, 4, 3),
            Process("P2", 2, 2, 1),
            Process("P3", 6, 2, 2)
        ]
        sched = PriorityScheduler(procs)
        sched.run()

        p1 = [p for p in procs if p.pid == "P1"][0]
        p2 = [p for p in procs if p.pid == "P2"][0]
        p3 = [p for p in procs if p.pid == "P3"][0]

        # P1 runs 0..2, P2 runs 2..4, P1 finishes 4..6, P3 runs 6..8
        self.assertEqual(p2.completion_time, 4)
        self.assertEqual(p1.completion_time, 6)
        self.assertEqual(p3.completion_time, 8)

    # 3. Several processes with equal priorities.
    def test_03_equal_priorities_deterministic_tie_breaking(self):
        # P1 arrives at 0, prio 2
        # P2 arrives at 0, prio 2 (tie-broken by PID 'P1' < 'P2')
        # P3 arrives at 1, prio 2 (tie-broken by arrival time: P1/P2 arrived at 0 before P3 at 1)
        procs = [
            Process("P2", 0, 3, 2),
            Process("P1", 0, 3, 2),
            Process("P3", 1, 3, 2)
        ]
        sched = PriorityScheduler(procs)
        sched.run()

        # FCFS on arrival time + alphabetical PID tie-breaker:
        # P1 runs 0..3, P2 runs 3..6, P3 runs 6..9
        segments = extract_gantt_segments(sched.gantt_chart)
        self.assertEqual(segments, [("P1", 0, 3), ("P2", 3, 6), ("P3", 6, 9)])

    # 4. A process with the highest possible priority under chosen convention (priority 1).
    def test_04_highest_priority_process_execution(self):
        procs = [
            Process("P_low", 0, 10, 5),
            Process("P_high", 2, 3, 1)
        ]
        sched = PriorityScheduler(procs)
        sched.run()

        p_high = [p for p in procs if p.pid == "P_high"][0]
        # P_high immediately preempts at arrival t=2 and completes without preemption
        self.assertEqual(p_high.first_run_time, 2)
        self.assertEqual(p_high.response_time, 0)
        self.assertEqual(p_high.completion_time, 5)
        self.assertEqual(p_high.waiting_time, 0)

    # 5. Aging when a process crosses each score boundary (10, 20, 30).
    def test_05_aging_score_boundary_transitions(self):
        aging = AgingManager()
        p = Process("P1", 0, 10, 6)

        # Before 10 -> boost 0
        aging.apply_aging(p, 9)
        self.assertEqual(p.current_priority, 6)

        # Boundary 10 -> boost 1 (priority becomes 5)
        self.assertTrue(aging.apply_aging(p, 10))
        self.assertEqual(p.current_priority, 5)

        # Boundary 20 -> boost 2 (priority becomes 4)
        self.assertTrue(aging.apply_aging(p, 20))
        self.assertEqual(p.current_priority, 4)

        # Boundary 30 -> boost 3 (priority becomes 3)
        self.assertTrue(aging.apply_aging(p, 30))
        self.assertEqual(p.current_priority, 3)

    # 6. A process whose original priority is already 1.
    def test_06_priority_one_process_aging_boundary(self):
        aging = AgingManager()
        p = Process("P_apex", 0, 10, 1)

        # Max aging must never decrease numerical priority below 1
        adjusted = aging.apply_aging(p, 50)
        self.assertFalse(adjusted)
        self.assertEqual(p.current_priority, 1)
        self.assertEqual(p.aging_adjustments, 0)

    # 7. A process crossing starvation threshold and later completing.
    def test_07_starvation_threshold_crossing_and_completion(self):
        # P1 (burst 25, prio 1) runs from 0 to 25.
        # P2 (burst 5, prio 5) arrives at 0.
        # At t=20, P2's waiting time reaches 20 (crosses threshold 20).
        procs = [
            Process("P1", 0, 25, 1),
            Process("P2", 0, 5, 5)
        ]
        sched = PriorityScheduler(procs)
        sched.run()

        p2 = [p for p in procs if p.pid == "P2"][0]
        self.assertTrue(p2.starvation_detected)
        self.assertEqual(p2.remaining_time, 0)
        self.assertEqual(p2.completion_time, 30)

        # Metrics must report threshold crossing without misrepresenting it as permanent dead-lock
        metrics = MetricsCalculator(procs)
        self.assertEqual(metrics.starvation_threshold_crossed_count(), 1)
        self.assertEqual(metrics.protected_process_count(), 1)

    # 8. A process whose priority boost changes scheduling order.
    def test_08_priority_boost_changes_scheduling_order(self):
        # P1 arrives at 0, burst 12, prio 5.
        # P2 arrives at 0, burst 3, prio 7.
        # At t=10, P2 waited 10 units -> boosted from prio 7 to 6.
        # At t=12, P1 finishes -> P2 executes because of forward progress.
        # If P3 arrives at t=10 with prio 7:
        # P2 (boosted to 6) runs BEFORE P3 (prio 7)!
        procs = [
            Process("P1", 0, 12, 5),
            Process("P2", 0, 4, 7),
            Process("P3", 10, 4, 7)
        ]
        sched = PriorityScheduler(procs)
        sched.run()

        p2 = [p for p in procs if p.pid == "P2"][0]
        p3 = [p for p in procs if p.pid == "P3"][0]

        # P2 runs before P3 because P2 was boosted to priority 6 at t=10
        self.assertEqual(p2.current_priority, 6)
        self.assertEqual(p3.current_priority, 7)
        self.assertLess(p2.completion_time, p3.completion_time)

    # 9. A process that reaches the maximum aging boost.
    def test_09_maximum_aging_boost_ceiling(self):
        aging = AgingManager()
        p = Process("P_deep", 0, 10, 8)

        # Scores >= 30 get maximum boost of 3
        self.assertEqual(aging.calculate_boost(30), 3)
        self.assertEqual(aging.calculate_boost(45), 3)
        self.assertEqual(aging.calculate_boost(100), 3)

        aging.apply_aging(p, 100)
        self.assertEqual(p.current_priority, 5)  # 8 - 3 = 5

    # 10. Correct first response time under preemption.
    def test_10_first_response_time_under_preemption(self):
        # P1 arrives at 0, burst 6, prio 4.
        # P2 arrives at 1, burst 2, prio 1 (preempts P1).
        # P1 first ran at t=0, so response time is 0 - 0 = 0.
        # P1 is preempted at t=1, resumes at t=3. Its response time must REMAIN 0!
        procs = [
            Process("P1", 0, 6, 4),
            Process("P2", 1, 2, 1)
        ]
        sched = PriorityScheduler(procs)
        sched.run()

        p1 = [p for p in procs if p.pid == "P1"][0]
        self.assertEqual(p1.first_run_time, 0)
        self.assertEqual(p1.response_time, 0)
        self.assertEqual(p1.completion_time, 8)

    # 11. Waiting-time and turnaround-time consistency (WT = TAT - BT).
    def test_11_waiting_and_turnaround_time_consistency(self):
        workload = [
            Process("P1", 0, 7, 3),
            Process("P2", 2, 4, 1),
            Process("P3", 4, 8, 4),
            Process("P4", 5, 2, 2)
        ]
        sched = PriorityScheduler(workload)
        sched.run()

        for p in workload:
            self.assertEqual(
                p.waiting_time,
                p.turnaround_time - p.burst_time,
                f"Process {p.pid} violated WT = TAT - BT consistency"
            )
            self.assertEqual(
                p.turnaround_time,
                p.completion_time - p.arrival_time,
                f"Process {p.pid} violated TAT = CT - AT consistency"
            )

    # 12. Empty workloads and invalid process inputs.
    def test_12_empty_workloads_and_safe_metric_defaults(self):
        # Empty scheduler runs
        s1 = PriorityScheduler([])
        s2 = NormalPriorityScheduler([])
        self.assertEqual(s1.run(), [])
        self.assertEqual(s2.run(), [])

        # Empty comparator run
        comp = SchedulerComparator([])
        norm = comp.run_normal()
        sg = comp.run_starveguard()

        self.assertEqual(norm["average_waiting"], 0.0)
        self.assertEqual(norm["average_turnaround"], 0.0)
        self.assertEqual(norm["average_response"], 0.0)
        self.assertEqual(norm["maximum_waiting"], 0)
        self.assertEqual(norm["fairness"], 1.0)

        self.assertEqual(sg["average_waiting"], 0.0)
        self.assertEqual(sg["starved_processes"], 0)
        self.assertEqual(sg["protected_processes"], 0)
        self.assertEqual(sg["aging_interventions"], 0)

    # 13. Identical workloads being compared fairly across both schedulers.
    def test_13_fair_comparison_identical_workloads(self):
        workload_data = [
            ("P1", 0, 10, 4),
            ("P2", 2, 5, 2),
            ("P3", 4, 6, 3)
        ]
        comp = SchedulerComparator(workload_data)
        norm = comp.run_normal()
        sg = comp.run_starveguard()

        # Input data must match exactly
        for np, sp in zip(norm["processes"], sg["processes"]):
            self.assertEqual(np.pid, sp.pid)
            self.assertEqual(np.arrival_time, sp.arrival_time)
            self.assertEqual(np.burst_time, sp.burst_time)
            self.assertEqual(np.original_priority, sp.original_priority)
            # Memory objects must be independent
            self.assertIsNot(np, sp)

    # 14. Reproducible results across repeated runs.
    def test_14_reproducibility_across_repeated_runs(self):
        workload_data = [
            ("P1", 0, 15, 5),
            ("P2", 1, 6, 3),
            ("P3", 3, 8, 4),
            ("P4", 5, 4, 2)
        ]
        comp1 = SchedulerComparator(workload_data)
        res1 = comp1.run_starveguard()

        comp2 = SchedulerComparator(workload_data)
        res2 = comp2.run_starveguard()

        self.assertEqual(res1["average_waiting"], res2["average_waiting"])
        self.assertEqual(res1["average_turnaround"], res2["average_turnaround"])
        self.assertEqual(res1["average_response"], res2["average_response"])
        self.assertEqual(res1["maximum_waiting"], res2["maximum_waiting"])
        self.assertEqual(res1["fairness"], res2["fairness"])
        self.assertEqual(res1["scheduler"].gantt_chart, res2["scheduler"].gantt_chart)

    # 15. Gantt chart intervals matching actual execution.
    def test_15_gantt_chart_intervals_match_execution(self):
        # Workload with gap: P1 (0..2), idle (2..4), P2 (4..7)
        procs = [
            Process("P1", 0, 2, 1),
            Process("P2", 4, 3, 1)
        ]
        sched = PriorityScheduler(procs)
        sched.run()

        segments = extract_gantt_segments(sched.gantt_chart)
        # Total time span is 0 to 7
        self.assertEqual(segments[0], ("P1", 0, 2))
        self.assertEqual(segments[1], ("IDLE", 2, 4))
        self.assertEqual(segments[2], ("P2", 4, 7))

        # Sum of segment lengths must match total timeline
        total_duration = sum(end - start for _, start, end in segments)
        self.assertEqual(total_duration, 7)

    # 16. Correct counting of aging events and protected processes.
    def test_16_aging_events_and_protected_process_counting(self):
        # P1 (burst 30, prio 1) causes P2 (prio 8) and P3 (prio 9) to age through all 3 tiers
        procs = [
            Process("P1", 0, 30, 1),
            Process("P2", 0, 5, 8),
            Process("P3", 0, 5, 9)
        ]
        sched = PriorityScheduler(procs)
        sched.run()

        metrics = MetricsCalculator(procs)

        # P2 aged 3 times (prio 8 -> 7 -> 6 -> 5)
        # P3 aged 3 times (prio 9 -> 8 -> 7 -> 6)
        # Total aging interventions = 3 + 3 = 6
        self.assertEqual(metrics.aging_intervention_count(sched), 6)
        self.assertEqual(len(sched.aging_events), 6)

        # Protected processes = 2 (P2 and P3 were protected, P1 was never aged)
        self.assertEqual(metrics.protected_process_count(), 2)
        p1 = [p for p in procs if p.pid == "P1"][0]
        self.assertEqual(p1.aging_adjustments, 0)


if __name__ == "__main__":
    unittest.main()
