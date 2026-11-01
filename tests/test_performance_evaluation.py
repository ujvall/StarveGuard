"""
StarveGuard Performance Evaluation & Benchmarking Unit Test Suite.

Tests:
    1. Extended metrics: CPU utilization, throughput, starvation percentage, starved WT, scheduling overhead.
    2. Formal scheduling invariants verification (positive and negative cases).
    3. Multi-scale deterministic workload generation (all 5 scales and 7 categories).
    4. Statistical analysis: descriptive statistics, confidence intervals, percentage delta, paired tests.
    5. Zero-baseline handling and boundary conditions.
    6. Benchmark engine execution and CSV/JSON persistence.
    7. 12-figure publication graph generation.
"""

import json
import os
import shutil
import unittest
from comparison.comparator import SchedulerComparator
from metrics.calculator import MetricsCalculator
from results.benchmark_engine import BenchmarkEngine
from results.evaluation_graphs import generate_all_evaluation_graphs
from results.invariants import InvariantViolationError, validate_scheduling_invariants
from results.statistics import (
    compute_paired_ttest,
    compute_percentage_change,
    compute_summary_statistics,
    compute_wilcoxon_signed_rank,
    student_t_critical_value,
    student_t_pvalue,
)
from results.workload_generator import (
    SCALE_SIZES,
    WORKLOAD_CATEGORIES,
    generate_benchmark_workload,
)
from scheduler.normal_priority_scheduler import NormalPriorityScheduler
from scheduler.priority_scheduler import PriorityScheduler
from scheduler.process import Process


class TestPerformanceMetrics(unittest.TestCase):
    def setUp(self):
        # 3 processes:
        # P1: arr=0, burst=5, prio=1 -> runs t=0..5, CT=5, TAT=5, WT=0, RT=0
        # P2: arr=0, burst=5, prio=2 -> runs t=5..10, CT=10, TAT=10, WT=5, RT=5
        # P3: arr=2, burst=2, prio=3 -> runs t=10..12, CT=12, TAT=10, WT=8, RT=8
        self.procs = [
            Process("P1", 0, 5, 1),
            Process("P2", 0, 5, 2),
            Process("P3", 2, 2, 3),
        ]
        self.sched = NormalPriorityScheduler([p.clone() for p in self.procs])
        self.sched.run()
        self.calc = MetricsCalculator(self.sched.processes)

    def test_cpu_utilization(self):
        # No idle time in this simulation: total time = 12, busy = 12 -> 100%
        util = self.calc.cpu_utilization(self.sched)
        self.assertEqual(util, 100.0)

    def test_cpu_utilization_with_idle(self):
        # Process arrives at t=5
        procs = [Process("P1", 5, 2, 1)]
        sched = NormalPriorityScheduler(procs)
        sched.run()
        # time = 7, busy = 2, idle = 5 -> util = (2/7)*100
        calc = MetricsCalculator(sched.processes)
        expected_util = (2.0 / 7.0) * 100.0
        self.assertAlmostEqual(calc.cpu_utilization(sched), expected_util, places=4)

    def test_throughput(self):
        # 3 processes completed in 12 ticks -> throughput = 3/12 = 0.25 proc/tick
        tp = self.calc.throughput(self.sched)
        self.assertEqual(tp, 0.25)

    def test_starvation_statistics_none_starved(self):
        # Max wait is 8 (< 20)
        self.assertEqual(self.calc.starved_process_count(), 0)
        self.assertEqual(self.calc.starvation_percentage(), 0.0)
        self.assertEqual(self.calc.starved_average_waiting_time(), 0.0)
        self.assertEqual(self.calc.starved_maximum_waiting_time(), 0)

    def test_starvation_statistics_with_starved_process(self):
        self.sched.processes[1].starvation_detected = True
        self.sched.processes[1].waiting_time = 25
        self.assertEqual(self.calc.starved_process_count(), 1)
        self.assertAlmostEqual(self.calc.starvation_percentage(), (1.0 / 3.0) * 100.0, places=4)
        self.assertEqual(self.calc.starved_average_waiting_time(), 25.0)
        self.assertEqual(self.calc.starved_maximum_waiting_time(), 25)

    def test_scheduling_overhead_tracking(self):
        overhead = self.calc.scheduling_overhead(self.sched)
        self.assertIn("total_decisions", overhead)
        self.assertIn("total_decision_time_sec", overhead)
        self.assertIn("avg_decision_time_us", overhead)
        self.assertGreater(overhead["total_decisions"], 0)
        self.assertGreaterEqual(overhead["total_decision_time_sec"], 0.0)


class TestSchedulingInvariants(unittest.TestCase):
    def test_valid_invariants_pass(self):
        workload = [("P1", 0, 4, 1), ("P2", 2, 6, 2)]
        comparator = SchedulerComparator(workload)
        for runner in [comparator.run_normal, comparator.run_starveguard, comparator.run_starveguard_conservative]:
            res = runner()
            self.assertTrue(validate_scheduling_invariants(res["processes"], res["scheduler"], workload))

    def test_invariant_fails_on_altered_burst(self):
        workload = [("P1", 0, 4, 1)]
        comparator = SchedulerComparator(workload)
        res = comparator.run_normal()
        res["processes"][0].burst_time = 99  # Tamper with burst
        with self.assertRaises(InvariantViolationError):
            validate_scheduling_invariants(res["processes"], res["scheduler"], workload)

    def test_invariant_fails_on_incomplete_execution(self):
        workload = [("P1", 0, 4, 1)]
        comparator = SchedulerComparator(workload)
        res = comparator.run_normal()
        res["processes"][0].remaining_time = 1  # Incomplete
        with self.assertRaises(InvariantViolationError):
            validate_scheduling_invariants(res["processes"], res["scheduler"], workload)

    def test_invariant_fails_on_negative_response_time(self):
        workload = [("P1", 0, 4, 1)]
        comparator = SchedulerComparator(workload)
        res = comparator.run_normal()
        res["processes"][0].response_time = -1  # Negative RT
        with self.assertRaises(InvariantViolationError):
            validate_scheduling_invariants(res["processes"], res["scheduler"], workload)


class TestWorkloadGenerator(unittest.TestCase):
    def test_deterministic_reproducibility(self):
        wl1 = generate_benchmark_workload("small", "A", seed=42)
        wl2 = generate_benchmark_workload("small", "A", seed=42)
        self.assertEqual(wl1, wl2)

    def test_distinct_seeds_produce_distinct_workloads(self):
        wl1 = generate_benchmark_workload("small", "A", seed=42)
        wl2 = generate_benchmark_workload("small", "A", seed=99)
        self.assertNotEqual(wl1, wl2)

    def test_all_scales_and_categories_valid(self):
        for scale, expected_n in SCALE_SIZES.items():
            for cat in WORKLOAD_CATEGORIES:
                wl = generate_benchmark_workload(scale, cat, seed=123)
                self.assertEqual(len(wl), expected_n)
                for pid, arr, burst, prio in wl:
                    self.assertGreaterEqual(arr, 0)
                    self.assertGreater(burst, 0)
                    self.assertGreaterEqual(prio, 1)


class TestStatisticalAnalysis(unittest.TestCase):
    def test_descriptive_statistics(self):
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        s = compute_summary_statistics(vals)
        self.assertEqual(s["mean"], 30.0)
        self.assertEqual(s["min"], 10.0)
        self.assertEqual(s["max"], 50.0)
        self.assertEqual(s["median"], 30.0)
        self.assertGreater(s["std"], 0.0)
        self.assertLess(s["ci95_lower"], 30.0)
        self.assertGreater(s["ci95_upper"], 30.0)

    def test_percentage_change_lower_is_better(self):
        # 100 -> 80 = -20% (Improvement)
        chg = compute_percentage_change(100.0, 80.0, lower_is_better=True)
        self.assertEqual(chg["percentage_change"], -20.0)
        self.assertTrue(chg["is_improvement"])
        self.assertFalse(chg["is_regression"])

        # 100 -> 120 = +20% (Regression)
        chg2 = compute_percentage_change(100.0, 120.0, lower_is_better=True)
        self.assertEqual(chg2["percentage_change"], 20.0)
        self.assertTrue(chg2["is_regression"])

    def test_percentage_change_higher_is_better(self):
        # Fairness 0.5 -> 0.8 = +60% (Improvement)
        chg = compute_percentage_change(0.5, 0.8, lower_is_better=False)
        self.assertAlmostEqual(chg["percentage_change"], 60.0)
        self.assertTrue(chg["is_improvement"])

    def test_zero_baseline_handling(self):
        chg = compute_percentage_change(0.0, 0.0)
        self.assertEqual(chg["percentage_change"], 0.0)
        self.assertTrue(chg["zero_baseline"])

        chg2 = compute_percentage_change(0.0, 10.0, lower_is_better=True)
        self.assertTrue(chg2["zero_baseline"])
        self.assertTrue(chg2["is_regression"])

    def test_paired_ttest_and_wilcoxon(self):
        base = [10, 12, 14, 15, 18] * 4
        test = [12, 14, 16, 17, 20] * 4  # Strictly +2 higher
        tt = compute_paired_ttest(base, test)
        self.assertAlmostEqual(tt["mean_diff"], 2.0)
        self.assertTrue(tt["significant"])

        wx = compute_wilcoxon_signed_rank(base, test)
        self.assertTrue(wx["significant"])


class TestBenchmarkEngineAndGraphs(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.abspath("results/test_unit_eval")
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_benchmark_execution_and_file_generation(self):
        engine = BenchmarkEngine(
            output_dir=self.test_dir,
            scales=["small"],
            categories=["A"],
            trials_per_combination=2
        )
        res = engine.run_benchmark()
        self.assertTrue(res["metadata"]["all_invariants_verified"])

        # Check required files
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "raw_trial_results.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "aggregate_summary.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "percentage_comparison.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "statistical_tests.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "workload_definitions.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "benchmark_metadata.json")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "performance_report.txt")))

        # Check metadata json fields
        with open(os.path.join(self.test_dir, "benchmark_metadata.json"), "r") as f:
            meta = json.load(f)
            self.assertEqual(meta["total_workloads"], 2)
            self.assertEqual(meta["total_simulations"], 8)

        # Check that 12 graphs were generated
        graphs_dir = os.path.join(self.test_dir, "graphs")
        graph_files = [f for f in os.listdir(graphs_dir) if f.endswith(".png")]
        self.assertEqual(len(graph_files), 12)


if __name__ == "__main__":
    unittest.main()

