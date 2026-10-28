import unittest
from scheduler.process import Process
from scheduler.normal_priority_scheduler import NormalPriorityScheduler
from scheduler.priority_scheduler import PriorityScheduler
from aging.aging_manager import (
    ConservativeAgingPolicy,
    ConservativeAgingManager,
    AgingManager,
)
from comparison.comparator import SchedulerComparator
from metrics.calculator import MetricsCalculator
from scheduler.gantt import extract_gantt_segments


class TestConservativeAgingSuite(unittest.TestCase):
    """
    Rigorously verifies all 16 required behaviors for Threshold-Triggered
    Conservative Aging (TTCA) with Apex Isolation.
    """

    def setUp(self):
        self.policy = ConservativeAgingPolicy(
            threshold=20,
            k_starve=10,
            max_boost=3,
            floor=2
        )

    # 1. No boost for scores below 20
    def test_01_no_boost_below_threshold_20(self):
        p = Process("P1", 0, 10, original_priority=6)
        for w in [0, 5, 10, 15, 19]:
            p.waiting_time = w
            adjusted = self.policy.apply_aging(p)
            self.assertFalse(adjusted, f"Adjusted unexpectedly at waiting_time={w}")
            self.assertEqual(p.current_priority, 6)
            self.assertEqual(p.aging_adjustments, 0)
            self.assertEqual(self.policy.calculate_boost(w), 0)

    # 2. Correct first boost at score 20
    def test_02_first_boost_at_score_20(self):
        # Base priority 8 -> reaches 7 at score 20 (boost +1)
        p = Process("P1", 0, 10, original_priority=8)
        p.waiting_time = 20
        self.assertEqual(self.policy.calculate_boost(20), 1)
        adjusted = self.policy.apply_aging(p)
        self.assertTrue(adjusted)
        self.assertEqual(p.current_priority, 7)
        self.assertEqual(p.aging_adjustments, 1)

        # Same tier (W=29) produces no duplicate adjustment
        p.waiting_time = 29
        self.assertEqual(self.policy.calculate_boost(29), 1)
        adjusted_again = self.policy.apply_aging(p)
        self.assertFalse(adjusted_again)
        self.assertEqual(p.current_priority, 7)

    # 3. Correct second boost at score 30
    def test_03_second_boost_at_score_30(self):
        # Base priority 8 -> reaches 6 at score 30 (boost +2)
        p = Process("P1", 0, 10, original_priority=8)
        p.waiting_time = 20
        self.policy.apply_aging(p)
        self.assertEqual(p.current_priority, 7)

        p.waiting_time = 30
        self.assertEqual(self.policy.calculate_boost(30), 2)
        adjusted = self.policy.apply_aging(p)
        self.assertTrue(adjusted)
        self.assertEqual(p.current_priority, 6)
        self.assertEqual(p.aging_adjustments, 2)

    # 4. Correct maximum boost at score 40 and above
    def test_04_max_boost_cap_at_40_and_above(self):
        # Base priority 8 -> reaches 5 at score 40 (boost +3, 8 - 3 = 5)
        p = Process("P1", 0, 10, original_priority=8)
        p.waiting_time = 40
        self.assertEqual(self.policy.calculate_boost(40), 3)
        adjusted = self.policy.apply_aging(p)
        self.assertTrue(adjusted)
        self.assertEqual(p.current_priority, 5)

        # Score 100 or 200 must remain capped at boost 3 (priority 5)
        for w in [50, 100, 250]:
            p.waiting_time = w
            self.assertEqual(self.policy.calculate_boost(w), 3)
            self.assertFalse(self.policy.apply_aging(p))
            self.assertEqual(p.current_priority, 5)

    # 5. Apex isolation: originally non-1 priorities never rise above priority 2
    def test_05_apex_isolation_floor_two(self):
        # Base priority 3 with boost 3 reaches priority 2 (clamped by floor 2).
        p3 = Process("P3", 0, 10, original_priority=3)
        p3.waiting_time = 100
        self.policy.apply_aging(p3)
        self.assertEqual(p3.current_priority, 2)

        # Base priority 4: 4 - 3 = 1 -> clamped to 2
        p4 = Process("P4", 0, 10, original_priority=4)
        p4.waiting_time = 100
        self.policy.apply_aging(p4)
        self.assertEqual(p4.current_priority, 2)

    # 6. Original priority-1 processes remain at priority 1
    def test_06_original_priority_one_retention(self):
        p1 = Process("P1", 0, 10, original_priority=1)
        for w in [0, 20, 50, 100]:
            p1.waiting_time = w
            adjusted = self.policy.apply_aging(p1)
            self.assertFalse(adjusted)
            self.assertEqual(p1.current_priority, 1)
            self.assertEqual(p1.aging_adjustments, 0)

    # 7. A newly arriving authentic priority-1 process preempts an aged priority-2 process
    def test_07_priority_one_preempts_aged_priority_two(self):
        # Setup:
        # P_initial (arr 0, burst 30, prio 2) runs from t=0 to t=30.
        # P_aged (arr 0, burst 10, prio 4) waits while P_initial runs.
        # At t=20, P_aged has waited 20 ticks -> boost +1 -> prio 3.
        # At t=30, P_aged has waited 30 ticks -> boost +2 -> prio 2.
        # At t=30, P_initial completes. P_aged (effective prio 2) gets CPU and runs t=30..32.
        # At t=32, P_high (arr 32, burst 4, prio 1) arrives!
        # Because P_high is Priority 1 and P_aged is Priority 2, P_high preempts P_aged immediately at t=32!
        p_initial = Process("P_initial", arrival_time=0, burst_time=30, original_priority=2)
        p_aged = Process("P_aged", arrival_time=0, burst_time=10, original_priority=4)
        p_high = Process("P_high", arrival_time=32, burst_time=4, original_priority=1)

        sched = PriorityScheduler(
            [p_initial, p_aged, p_high],
            aging_policy="conservative",
            threshold=20,
            k_starve=10,
            max_boost=3,
            floor=2
        )
        sched.run()

        # Verify P_high ran at t=32 immediately upon arrival
        self.assertEqual(p_high.first_run_time, 32)
        self.assertEqual(p_high.completion_time, 36)
        self.assertEqual(p_high.waiting_time, 0)
        # P_aged ran for 2 units (30..32), was preempted by P_high (32..36), then finished remaining 8 units (36..44)
        self.assertEqual(p_aged.first_run_time, 30)
        self.assertEqual(p_aged.completion_time, 44)

    # 8. Deterministic arrival-time/PID tie-breaking among aged priority-2 processes
    def test_08_deterministic_tie_breaking_at_priority_two(self):
        # Two processes aged to priority 2: P_earlier (arr 0) and P_later (arr 2)
        # Clock at t=5 so both have arrived and are in ready queue
        p_later = Process("P_later", arrival_time=2, burst_time=5, original_priority=3)
        p_earlier = Process("P_earlier", arrival_time=0, burst_time=5, original_priority=3)

        sched = PriorityScheduler(
            [p_later, p_earlier],
            aging_policy="conservative",
            threshold=20,
            k_starve=10,
            max_boost=3,
            floor=2
        )
        sched.time = 5  # Both arrived
        p_earlier.waiting_time = 25
        p_later.waiting_time = 25
        sched.apply_starvation_prevention()

        self.assertEqual(p_earlier.current_priority, 2)
        self.assertEqual(p_later.current_priority, 2)

        # Earlier arrival must win tie-break
        selected = sched.select_process()
        self.assertEqual(selected.pid, "P_earlier")

    # 9. Exact equivalence to normal priority scheduling for workloads where no process reaches threshold
    def test_09_exact_equivalence_when_no_process_starves(self):
        # Workload where all processes finish within 15 ticks (W < 20)
        workload = [
            ("P1", 0, 5, 2),
            ("P2", 2, 4, 1),
            ("P3", 4, 3, 3)
        ]
        comp = SchedulerComparator(workload)
        res_normal = comp.run_normal()
        res_ttca = comp.run_starveguard_conservative()

        self.assertEqual(res_ttca["aging_interventions"], 0)
        self.assertEqual(res_ttca["starved_processes"], 0)
        self.assertEqual(res_normal["average_waiting"], res_ttca["average_waiting"])
        self.assertEqual(res_normal["average_response"], res_ttca["average_response"])
        self.assertEqual(res_normal["maximum_waiting"], res_ttca["maximum_waiting"])
        self.assertEqual(
            res_normal["scheduler"].gantt_chart,
            res_ttca["scheduler"].gantt_chart
        )

    # 10. Waiting-time and turnaround-time accounting invariants
    def test_10_accounting_invariants_preserved(self):
        workload = [
            Process("P1", 0, 25, 8),
            Process("P2", 2, 5, 2),
            Process("P3", 5, 5, 1)
        ]
        sched = PriorityScheduler(workload, aging_policy="conservative")
        sched.run()

        for p in workload:
            self.assertEqual(p.turnaround_time, p.completion_time - p.arrival_time)
            self.assertEqual(p.waiting_time, p.turnaround_time - p.burst_time)
            self.assertEqual(p.response_time, p.first_run_time - p.arrival_time)
            self.assertGreaterEqual(p.waiting_time, 0)

    # 11. Correct first-response-time recording under preemption
    def test_11_response_time_under_preemption(self):
        p1 = Process("P1", 0, 6, 2)
        p2 = Process("P2", 3, 2, 1)
        p3 = Process("P3", 1, 4, 3)

        sched = PriorityScheduler([p1, p2, p3], aging_policy="conservative")
        sched.run()

        self.assertEqual(p1.response_time, 0)
        self.assertEqual(p2.response_time, 0)
        self.assertEqual(p3.first_run_time, 8)
        self.assertEqual(p3.response_time, 7)

    # 12. Correct handling of idle periods and staggered arrivals
    def test_12_idle_periods_and_staggered_arrivals(self):
        p1 = Process("P1", 5, 4, 6)
        sched = PriorityScheduler([p1], aging_policy="conservative")
        sched.run()

        self.assertEqual(p1.first_run_time, 5)
        self.assertEqual(p1.waiting_time, 0)
        self.assertEqual(p1.current_priority, 6)
        self.assertEqual(p1.aging_adjustments, 0)
        segments = extract_gantt_segments(sched.gantt_chart)
        self.assertEqual(segments, [("IDLE", 0, 5), ("P1", 5, 9)])

    # 13. Independent process objects across policy comparisons
    def test_13_independent_process_objects(self):
        workload = [("P1", 0, 25, 8), ("P2", 0, 5, 1)]
        comparator = SchedulerComparator(workload)

        res_norm = comparator.run_normal()
        res_ttca = comparator.run_starveguard_conservative()

        self.assertIsNot(res_norm["processes"][0], res_ttca["processes"][0])
        res_norm["processes"][0].waiting_time = 999
        self.assertNotEqual(
            res_norm["processes"][0].waiting_time,
            res_ttca["processes"][0].waiting_time
        )

    # 14. Reproducibility across repeated identical runs
    def test_14_reproducibility_across_identical_runs(self):
        workload = [("P1", 0, 30, 8), ("P2", 5, 10, 2), ("P3", 10, 5, 1)]
        comp1 = SchedulerComparator(workload)
        comp2 = SchedulerComparator(workload)

        r1 = comp1.run_starveguard_conservative()
        r2 = comp2.run_starveguard_conservative()

        self.assertEqual(r1["average_waiting"], r2["average_waiting"])
        self.assertEqual(r1["maximum_waiting"], r2["maximum_waiting"])
        self.assertEqual(r1["fairness"], r2["fairness"])
        self.assertEqual(r1["scheduler"].gantt_chart, r2["scheduler"].gantt_chart)

    # 15. Boundary cases for priority 1, priority 2, and maximum supported priority
    def test_15_boundary_cases_priorities(self):
        # Priority 1: never boosted
        p1 = Process("P1", 0, 5, original_priority=1)
        p1.waiting_time = 100
        self.assertFalse(self.policy.apply_aging(p1))
        self.assertEqual(p1.current_priority, 1)

        # Priority 2: cannot go above floor 2
        p2 = Process("P2", 0, 5, original_priority=2)
        p2.waiting_time = 100
        self.assertFalse(self.policy.apply_aging(p2))
        self.assertEqual(p2.current_priority, 2)

        # High priority 10: reaches 7 (10 - 3 = 7)
        p10 = Process("P10", 0, 5, original_priority=10)
        p10.waiting_time = 45
        self.assertTrue(self.policy.apply_aging(p10))
        self.assertEqual(p10.current_priority, 7)

    # 16. Empty workloads and invalid inputs consistent with existing conventions
    def test_16_empty_and_invalid_inputs(self):
        sched = PriorityScheduler([], aging_policy="conservative")
        gantt = sched.run()
        self.assertEqual(gantt, [])

        with self.assertRaises(ValueError):
            ConservativeAgingPolicy(threshold=-1)
        with self.assertRaises(ValueError):
            ConservativeAgingPolicy(k_starve=0)
        with self.assertRaises(ValueError):
            ConservativeAgingPolicy(max_boost=-1)


if __name__ == "__main__":
    unittest.main()
