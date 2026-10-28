import unittest
from scheduler.process import Process
from scheduler.normal_priority_scheduler import NormalPriorityScheduler
from scheduler.priority_scheduler import PriorityScheduler
from aging.aging_manager import AgingManager, ContinuousAgingManager, ContinuousAgingPolicy, CappedAgingPolicy
from starvation.detector import StarvationDetector
from comparison.comparator import SchedulerComparator
from metrics.calculator import MetricsCalculator
from scheduler.gantt import extract_gantt_segments


class TestContinuousAgingSuite(unittest.TestCase):
    """
    Rigorously verifies the 20 algorithm correctness and regression requirements
    for continuous waiting-time-based aging with a priority floor of 1.
    """

    # 1. Priority does not change before the first aging interval
    def test_01_priority_unchanged_before_first_interval(self):
        # K = 5. P1 runs for 4 ticks (0 to 4). P2 (prio 6) waits for 4 ticks.
        # At t=4, P2 waiting_time = 4 < 5. Effective priority must remain 6.
        p1 = Process("P1", arrival_time=0, burst_time=10, original_priority=1)
        p2 = Process("P2", arrival_time=0, burst_time=5, original_priority=6)

        sched = PriorityScheduler([p1, p2], aging_policy="continuous", k=5)
        # Advance 4 ticks
        for _ in range(4):
            sched.apply_starvation_prevention()
            proc = sched.select_process()
            self.assertEqual(proc.pid, "P1")
            for p in sched.get_ready_processes():
                if p.pid != proc.pid:
                    p.waiting_time += 1
            proc.remaining_time -= 1
            sched.time += 1

        self.assertEqual(p2.waiting_time, 4)
        self.assertEqual(p2.current_priority, 6)
        self.assertEqual(p2.aging_adjustments, 0)
        self.assertEqual(len(sched.aging_events), 0)

    # 2. Priority improves exactly at the first interval boundary
    def test_02_priority_improves_at_first_interval_boundary(self):
        # K = 5. P1 runs for 10 ticks. P2 (prio 6) waits.
        # At t=5, P2 waiting_time reaches 5. Effective priority must become max(1, 6 - 5//5) = 5.
        p1 = Process("P1", 0, 10, 1)
        p2 = Process("P2", 0, 5, 6)

        sched = PriorityScheduler([p1, p2], aging_policy="continuous", k=5)
        for _ in range(5):
            sched.apply_starvation_prevention()
            proc = sched.select_process()
            for p in sched.get_ready_processes():
                if p.pid != proc.pid:
                    p.waiting_time += 1
            proc.remaining_time -= 1
            sched.time += 1

        # Now evaluate starvation prevention at t=5
        sched.apply_starvation_prevention()
        self.assertEqual(p2.waiting_time, 5)
        self.assertEqual(p2.current_priority, 5)
        self.assertEqual(p2.aging_adjustments, 1)
        self.assertEqual(len(sched.aging_events), 1)
        # Event: (time=5, pid='P2', old_prio=6, new_prio=5, score=5)
        self.assertEqual(sched.aging_events[0], (5, "P2", 6, 5, 5))

    # 3. Priority improves correctly at subsequent interval boundaries
    def test_03_priority_improves_at_subsequent_boundaries(self):
        # K = 5. P1 runs 20 ticks. P2 starts with prio 8.
        # W=5 -> prio 7. W=10 -> prio 6. W=15 -> prio 5.
        p1 = Process("P1", 0, 20, 1)
        p2 = Process("P2", 0, 5, 8)
        sched = PriorityScheduler([p1, p2], aging_policy="continuous", k=5)
        sched.run()

        # P2 had to wait 20 ticks while P1 completed
        # Aging boundaries at 5 (prio 7), 10 (prio 6), 15 (prio 5), 20 (prio 4)
        self.assertEqual(p2.original_priority, 8)
        self.assertEqual(p2.current_priority, 4)
        self.assertEqual(p2.aging_adjustments, 4)
        self.assertEqual(len(sched.aging_events), 4)

    # 4. Priority never falls below 1
    def test_04_priority_never_falls_below_one(self):
        # Process has original priority 2. K = 5.
        # Even after waiting 100 ticks, effective priority cannot drop below 1.
        p = Process("P_low", 0, 5, 2)
        policy = ContinuousAgingPolicy(k=5, floor=1)
        p.waiting_time = 100

        adjusted = policy.apply_aging(p)
        self.assertTrue(adjusted)
        self.assertEqual(p.current_priority, 1)

        # Further aging attempts cannot reduce priority further
        p.waiting_time = 200
        adjusted_again = policy.apply_aging(p)
        self.assertFalse(adjusted_again)
        self.assertEqual(p.current_priority, 1)

    # 5. Original priority remains unchanged
    def test_05_original_priority_remains_unchanged(self):
        procs = [
            Process("P1", 0, 30, 2),
            Process("P2", 0, 5, 9),
            Process("P3", 0, 5, 7)
        ]
        sched = PriorityScheduler(procs, aging_policy="continuous", k=5)
        sched.run()

        p2 = [p for p in procs if p.pid == "P2"][0]
        p3 = [p for p in procs if p.pid == "P3"][0]
        self.assertEqual(p2.original_priority, 9)
        self.assertEqual(p3.original_priority, 7)
        self.assertLess(p2.current_priority, 9)
        self.assertLess(p3.current_priority, 7)

    # 6. Effective priority is computed from original priority, not cumulatively
    def test_06_effective_priority_anchored_to_original(self):
        p = Process("P1", 0, 10, original_priority=6)
        policy = ContinuousAgingPolicy(k=5, floor=1)

        # W = 10: boost = 10//5 = 2. New priority = 6 - 2 = 4.
        p.waiting_time = 10
        policy.apply_aging(p)
        self.assertEqual(p.current_priority, 4)

        # If a bug cumulatively subtracted from current_priority, W=15 would subtract 3 from 4 = 1.
        # But correct formula: max(1, 6 - 15//5) = max(1, 6 - 3) = 3.
        p.waiting_time = 15
        policy.apply_aging(p)
        self.assertEqual(p.current_priority, 3)

    # 7. Waiting time accumulates only while process is ready and not executing
    def test_07_waiting_time_accumulates_only_when_ready_and_not_executing(self):
        # P1 arrives at 0 (burst 4). P2 arrives at 2 (burst 4).
        # t=0..2: P1 runs (P2 not arrived yet, P2 waiting=0).
        # t=2..4: P1 continues running (P2 ready, waiting accumulates 2 ticks).
        # t=4..8: P2 runs (P2 waiting stops accumulating).
        p1 = Process("P1", 0, 4, 1)
        p2 = Process("P2", 2, 4, 3)
        sched = PriorityScheduler([p1, p2], aging_policy="continuous", k=5)
        sched.run()

        self.assertEqual(p1.waiting_time, 0)
        self.assertEqual(p2.waiting_time, 2)

    # 8. Arrival time and CPU idle periods are handled correctly
    def test_08_arrival_time_and_cpu_idle_periods(self):
        # CPU is idle from t=0 to t=6. P1 arrives at t=6 (burst 4, prio 5).
        # Idle ticks 0..6 must NOT age P1 before its arrival.
        p1 = Process("P1", arrival_time=6, burst_time=4, original_priority=5)
        sched = PriorityScheduler([p1], aging_policy="continuous", k=5)
        sched.run()

        self.assertEqual(p1.first_run_time, 6)
        self.assertEqual(p1.completion_time, 10)
        self.assertEqual(p1.waiting_time, 0)
        self.assertEqual(p1.current_priority, 5)
        self.assertEqual(p1.aging_adjustments, 0)
        segments = extract_gantt_segments(sched.gantt_chart)
        self.assertEqual(segments, [("IDLE", 0, 6), ("P1", 6, 10)])

    # 9. Preempted processes accumulate waiting time correctly
    def test_09_preempted_process_accumulates_waiting_time(self):
        # P1 (arr 0, burst 6, prio 3) runs from t=0 to t=2.
        # P2 (arr 2, burst 2, prio 1) preempts P1 at t=2 and runs from t=2 to t=4.
        # While P2 runs, P1 waits in ready queue for 2 ticks.
        # At t=4, P2 completes; P1 resumes and runs to t=8.
        p1 = Process("P1", 0, 6, 3)
        p2 = Process("P2", 2, 2, 1)
        sched = PriorityScheduler([p1, p2], aging_policy="continuous", k=5)
        sched.run()

        self.assertEqual(p1.first_run_time, 0)
        self.assertEqual(p1.response_time, 0)
        self.assertEqual(p1.completion_time, 8)
        self.assertEqual(p1.turnaround_time, 8)
        self.assertEqual(p1.waiting_time, 2)  # 8 - 6 = 2
        self.assertEqual(p2.waiting_time, 0)

    # 10. Response time remains the time of first execution
    def test_10_response_time_is_first_dispatch_minus_arrival(self):
        # P1 (arr 0, burst 7, prio 1). P2 (arr 3, burst 4, prio 4).
        # P2 is first dispatched at t=7. Response time must be 7 - 3 = 4.
        p1 = Process("P1", 0, 7, 1)
        p2 = Process("P2", 3, 4, 4)
        sched = PriorityScheduler([p1, p2], aging_policy="continuous", k=5)
        sched.run()

        self.assertEqual(p2.first_run_time, 7)
        self.assertEqual(p2.response_time, 4)

    # 11. Completion, turnaround, and waiting-time invariants remain correct
    def test_11_metrics_invariants_hold(self):
        procs = [
            Process("P1", 0, 15, 6),
            Process("P2", 0, 5, 3),
            Process("P3", 5, 5, 3),
            Process("P4", 10, 5, 3)
        ]
        sched = PriorityScheduler(procs, aging_policy="continuous", k=5)
        sched.run()

        for p in procs:
            self.assertEqual(p.turnaround_time, p.completion_time - p.arrival_time)
            self.assertEqual(p.waiting_time, p.turnaround_time - p.burst_time)
            self.assertEqual(p.response_time, p.first_run_time - p.arrival_time)
            self.assertGreaterEqual(p.waiting_time, 0)

    # 12. Aging events are logged only when the effective priority changes
    def test_12_aging_events_logged_only_on_priority_change(self):
        p1 = Process("P1", 0, 12, 1)
        p2 = Process("P2", 0, 4, 5)  # Needs boost at W=5 (prio 4) and W=10 (prio 3)
        sched = PriorityScheduler([p1, p2], aging_policy="continuous", k=5)
        sched.run()

        # P2 waited 12 ticks while P1 completed
        # Changes occurred only at t=5 (6->5 or 5->4) and t=10 (4->3)
        self.assertEqual(len(sched.aging_events), 2)
        # Verify times
        self.assertEqual(sched.aging_events[0][0], 5)
        self.assertEqual(sched.aging_events[1][0], 10)

    # 13. Aging intervention counts match recorded events
    def test_13_intervention_counts_match_events(self):
        procs = [
            Process("P1", 0, 25, 2),
            Process("P2", 0, 5, 8),
            Process("P3", 0, 5, 9)
        ]
        sched = PriorityScheduler(procs, aging_policy="continuous", k=5)
        sched.run()

        calc = MetricsCalculator(procs)
        self.assertEqual(calc.aging_intervention_count(sched), len(sched.aging_events))
        self.assertEqual(sum(p.aging_adjustments for p in procs), len(sched.aging_events))

    # 14. Completed processes are not scheduled again
    def test_14_completed_processes_never_scheduled_again(self):
        p1 = Process("P1", 0, 3, 1)
        p2 = Process("P2", 0, 4, 2)
        sched = PriorityScheduler([p1, p2], aging_policy="continuous", k=5)
        sched.run()

        # P1 runs 0..3 and completes. Afterwards only P2 runs.
        p1_ticks_after_completion = [
            (pid, t) for pid, t in sched.gantt_chart if pid == "P1" and t >= 3
        ]
        self.assertEqual(p1_ticks_after_completion, [])
        self.assertEqual(p1.remaining_time, 0)
        self.assertEqual(p2.remaining_time, 0)

    # 15. Equal-priority tie-breaking is deterministic (earliest arrival, then PID)
    def test_15_equal_priority_deterministic_tie_breaking(self):
        # Two processes with same priority and arrival: P_B and P_A
        # Lexicographical PID tie-break: P_A should run before P_B
        p_b = Process("P_B", 0, 3, 2)
        p_a = Process("P_A", 0, 3, 2)
        sched = PriorityScheduler([p_b, p_a], aging_policy="continuous", k=5)
        sched.run()

        self.assertEqual(sched.gantt_chart[0][0], "P_A")
        self.assertEqual(p_a.completion_time, 3)
        self.assertEqual(p_b.completion_time, 6)

    # 16. Original capped aging remains reproducible
    def test_16_original_capped_aging_reproducible(self):
        # Capped aging with max boost +3
        procs = [
            Process("P1", 0, 35, 1),
            Process("P2", 0, 5, 8)
        ]
        sched = PriorityScheduler(procs, aging_policy="capped")
        sched.run()

        p2 = [p for p in procs if p.pid == "P2"][0]
        # Under capped policy, max boost is 3 (original 8 -> effective 5)
        self.assertEqual(p2.current_priority, 5)
        self.assertEqual(p2.aging_adjustments, 3)

    # 17. Both aging policies receive independent process instances
    def test_17_policies_receive_independent_process_instances(self):
        workload = [("P1", 0, 20, 6), ("P2", 0, 5, 8)]
        comparator = SchedulerComparator(workload)

        res_normal = comparator.run_normal()
        res_capped = comparator.run_starveguard(aging_policy="capped")
        res_cont = comparator.run_starveguard(aging_policy="continuous", k=5)

        # Mutating a process in one result should not affect the others
        self.assertIsNot(res_normal["processes"][0], res_capped["processes"][0])
        self.assertIsNot(res_capped["processes"][0], res_cont["processes"][0])

    # 18. Repeated runs produce identical results for identical inputs
    def test_18_determinism_across_repeated_runs(self):
        workload = [("P1", 0, 15, 6), ("P2", 0, 5, 3), ("P3", 5, 5, 3)]
        comp1 = SchedulerComparator(workload)
        comp2 = SchedulerComparator(workload)

        r1 = comp1.run_starveguard_continuous(k=5)
        r2 = comp2.run_starveguard_continuous(k=5)

        self.assertEqual(r1["average_waiting"], r2["average_waiting"])
        self.assertEqual(r1["fairness"], r2["fairness"])
        self.assertEqual(r1["scheduler"].gantt_chart, r2["scheduler"].gantt_chart)

    # 19. Empty and invalid inputs remain safely handled
    def test_19_empty_and_invalid_inputs_handled(self):
        # Empty process list
        sched = PriorityScheduler([], aging_policy="continuous", k=5)
        gantt = sched.run()
        self.assertEqual(gantt, [])

        # Invalid K <= 0 should raise ValueError
        with self.assertRaises(ValueError):
            ContinuousAgingPolicy(k=0)
        with self.assertRaises(ValueError):
            ContinuousAgingPolicy(k=-5)

    # 20. Gantt charts match actual execution timeline
    def test_20_gantt_chart_matches_timeline(self):
        procs = [
            Process("P1", 0, 3, 2),
            Process("P2", 1, 2, 1)  # Preempts P1 at t=1
        ]
        sched = PriorityScheduler(procs, aging_policy="continuous", k=5)
        gantt = sched.run()

        # Timeline:
        # t=0: P1 (prio 2) runs
        # t=1: P2 (prio 1) arrives and preempts P1, runs t=1..3
        # t=3: P1 resumes, runs t=3..5
        expected_gantt = [("P1", 0), ("P2", 1), ("P2", 2), ("P1", 3), ("P1", 4)]
        self.assertEqual(gantt, expected_gantt)
        segments = extract_gantt_segments(gantt)
        self.assertEqual(segments, [("P1", 0, 1), ("P2", 1, 3), ("P1", 3, 5)])


if __name__ == "__main__":
    unittest.main()

