import unittest
from scheduler.process import Process
from scheduler.priority_scheduler import PriorityScheduler
from scheduler.normal_priority_scheduler import NormalPriorityScheduler
from aging.aging_manager import QueuePressureAgingPolicy, AgingManager
from metrics.calculator import MetricsCalculator
from comparison.comparator import SchedulerComparator
from results.invariants import validate_scheduling_invariants


class TestTTCAv2BPlus(unittest.TestCase):
    """
    Unit tests for TTCA v2-B+ advanced optimization variants:
        - Candidate B0: Established Candidate B Baseline Control
        - Candidate B1: Queue-Pressure-Aware Aging
        - Candidate B2: Starvation-Aware SRTF Arbitration
        - Candidate B3: Preemption-Efficient Candidate B
        - Candidate B4: Best Justified Hybrid
        - Percentile, continuous wait, and preemption metrics
    """

    def test_queue_pressure_aging_policy(self):
        policy = QueuePressureAgingPolicy(threshold=20, k_base=10, min_k=6, pressure_scale=2, max_boost=3, floor=2)
        # Score < threshold -> 0 boost
        self.assertEqual(policy.calculate_boost(15, higher_prio_count=5), 0)

        # Score = 20 -> boost = 1
        self.assertEqual(policy.calculate_boost(20, higher_prio_count=0), 1)

        # When higher_prio_count = 0, k_eff = 10 -> at score 30, boost = 1 + (30-20)//10 = 2
        self.assertEqual(policy.calculate_boost(30, higher_prio_count=0), 2)

        # When higher_prio_count = 8, accel = min(4, 8//2) = 4, k_eff = 10 - 4 = 6
        # At score 26, boost = 1 + (26-20)//6 = 2 (accelerated boost under queue congestion!)
        self.assertEqual(policy.calculate_boost(26, higher_prio_count=8), 2)

    def test_starvation_aware_srtf_tie_breaking(self):
        # Two processes in same priority band:
        # P_SHORT: burst 5, waited 0 -> effective key burst = 5 - 0.05*0 = 5.0
        # P_STARVED: burst 15, waited 100 -> effective key burst = 15 - 0.05*(100-20) = 15 - 4.0 = 11.0
        # If P_STARVED waited 300 -> 15 - 0.05*280 = 15 - 14.0 = 1.0 < 5.0 (wins arbitration!)
        p_short = Process(pid="P_SHORT", arrival_time=0, burst_time=5, original_priority=2)
        p_starved = Process(pid="P_STARVED", arrival_time=0, burst_time=15, original_priority=2)
        p_starved.waiting_time = 300

        sched = PriorityScheduler([p_short, p_starved], tie_breaker="starvation_aware_srtf", gamma=0.05)
        selected = sched.select_process()
        self.assertEqual(selected.pid, "P_STARVED")

    def test_preemption_hysteresis(self):
        # Running process has 1 tick remaining. A new process with same priority arrives with 1 tick remaining.
        # Hysteresis prevents preemption: running process finishes!
        p_run = Process(pid="P_RUN", arrival_time=0, burst_time=2, original_priority=2)
        p_arr = Process(pid="P_ARR", arrival_time=1, burst_time=1, original_priority=2)

        sched = PriorityScheduler([p_run, p_arr], tie_breaker="srtf", preemption_hysteresis=True)
        # Step 0: P_RUN starts
        sched.time = 0
        p0 = sched.select_process()
        self.assertEqual(p0.pid, "P_RUN")
        sched._last_running_pid = "P_RUN"
        p_run.remaining_time = 1

        # Step 1: P_ARR arrives with burst 1. Both have priority 2 and burst 1.
        # With hysteresis, P_RUN is kept so it can finish!
        sched.time = 1
        p1 = sched.select_process()
        self.assertEqual(p1.pid, "P_RUN")

    def test_metrics_percentiles_and_streaks(self):
        procs = [
            Process(pid="P1", arrival_time=0, burst_time=5, original_priority=1),
            Process(pid="P2", arrival_time=0, burst_time=5, original_priority=2),
            Process(pid="P3", arrival_time=0, burst_time=5, original_priority=3),
        ]
        procs[0].waiting_time = 10
        procs[1].waiting_time = 50
        procs[2].waiting_time = 100
        procs[0].longest_continuous_wait = 10
        procs[1].longest_continuous_wait = 50
        procs[2].longest_continuous_wait = 100

        calc = MetricsCalculator(procs)
        self.assertEqual(calc.median_waiting_time(), 50.0)
        self.assertAlmostEqual(calc.percentile_waiting_time(50.0), 50.0)
        self.assertGreater(calc.percentile_waiting_time(95.0), 50.0)
        self.assertEqual(calc.longest_continuous_waiting_time(), 100)

    def test_comparator_b_variants_and_invariants(self):
        workload = [
            ("P1", 0, 10, 2),
            ("P2", 2, 4, 3),
            ("P3", 3, 25, 4),
            ("P4", 5, 2, 2),
            ("P5", 10, 8, 3),
        ]
        comp = SchedulerComparator(workload)
        for runner_name in ["run_ttca_cand_b0", "run_ttca_cand_b1", "run_ttca_cand_b2", "run_ttca_cand_b3", "run_ttca_cand_b4"]:
            res = getattr(comp, runner_name)()
            validate_scheduling_invariants(res["processes"], res["scheduler"], workload)
            self.assertIn("median_waiting", res)
            self.assertIn("waiting_p95", res)
            self.assertIn("waiting_p99", res)
            self.assertIn("preemption_count", res)
            self.assertIn("longest_continuous_wait", res)


if __name__ == "__main__":
    unittest.main()

