import unittest
from scheduler.process import Process
from scheduler.priority_scheduler import PriorityScheduler
from aging.aging_manager import (
    AdaptiveAgingPolicy,
    AgingManager,
    ConservativeAgingPolicy,
)
from starvation.detector import StarvationDetector
from comparison.comparator import SchedulerComparator
from results.invariants import validate_scheduling_invariants


class TestTTCAv2Algorithms(unittest.TestCase):
    """
    Comprehensive unit tests for TTCA v2 optimization candidates:
        - Candidate A: Adaptive Aging (Burst-paced intervals)
        - Candidate B: Shortest Remaining Time (SRTF) Tie-Breaking
        - Candidate C: Dual-Tiered Hybrid TTCA (Emergency Anti-Starvation SRTF)
    """

    def test_adaptive_aging_policy_burst_pacing(self):
        policy = AdaptiveAgingPolicy(threshold=20, k_base=10, burst_scale=10, max_boost=3, floor=2)
        # Score below threshold -> 0 boost
        self.assertEqual(policy.calculate_boost(15, remaining_time=10), 0)

        # Score at threshold (20) -> base boost of 1
        self.assertEqual(policy.calculate_boost(20, remaining_time=10), 1)

        # For remaining_time=5, k_eff = 10 + 0 = 10
        # Score 30 -> 1 + (30-20)//10 = 2
        self.assertEqual(policy.calculate_boost(30, remaining_time=5), 2)

        # For remaining_time=40, k_eff = 10 + 4 = 14
        # Score 30 -> 1 + (30-20)//14 = 1 (pacing slows down promotion of long tasks)
        self.assertEqual(policy.calculate_boost(30, remaining_time=40), 1)
        # Score 34 -> 1 + (34-20)//14 = 2
        self.assertEqual(policy.calculate_boost(34, remaining_time=40), 2)

    def test_adaptive_aging_apex_isolation(self):
        policy = AdaptiveAgingPolicy(threshold=20, k_base=10, max_boost=3, floor=2)
        
        # Priority 1 process is never promoted (stays 1)
        p1 = Process(pid="P1", arrival_time=0, burst_time=10, original_priority=1)
        p1.waiting_time = 50
        policy.apply_aging(p1, score=50)
        self.assertEqual(p1.current_priority, 1)

        # Priority 2 process is never promoted to 1 (floor=2)
        p2 = Process(pid="P2", arrival_time=0, burst_time=10, original_priority=2)
        p2.waiting_time = 50
        policy.apply_aging(p2, score=50)
        self.assertEqual(p2.current_priority, 2)

        # Priority 5 process is boosted up to max floor 2
        p5 = Process(pid="P5", arrival_time=0, burst_time=10, original_priority=5)
        p5.waiting_time = 100
        policy.apply_aging(p5, score=100)
        self.assertEqual(p5.current_priority, 2)  # 5 - 3 = 2

    def test_candidate_b_srtf_tie_breaking(self):
        # Two processes with same effective priority: shorter remaining burst wins
        p_long = Process(pid="P_LONG", arrival_time=0, burst_time=20, original_priority=2)
        p_short = Process(pid="P_SHORT", arrival_time=5, burst_time=3, original_priority=2)
        
        sched = PriorityScheduler([p_long, p_short], tie_breaker="srtf")
        sched.time = 5  # both are ready
        selected = sched.select_process()
        self.assertEqual(selected.pid, "P_SHORT")

    def test_candidate_b_priority_dominance(self):
        # A higher-priority process (lower value) always wins over a short process with lower priority
        p_high = Process(pid="P_HIGH", arrival_time=0, burst_time=20, original_priority=1)
        p_short = Process(pid="P_SHORT", arrival_time=0, burst_time=2, original_priority=2)
        
        sched = PriorityScheduler([p_high, p_short], tie_breaker="srtf")
        selected = sched.select_process()
        self.assertEqual(selected.pid, "P_HIGH")

    def test_candidate_c_dual_tier_emergency_escalation(self):
        # At equal priority, a process waiting >= emergency_threshold (40) preempts a shorter process
        p_starved_long = Process(pid="P_STARVED", arrival_time=0, burst_time=30, original_priority=2)
        p_starved_long.waiting_time = 45  # Exceeds emergency threshold 40
        
        p_fresh_short = Process(pid="P_FRESH", arrival_time=40, burst_time=2, original_priority=2)
        p_fresh_short.waiting_time = 5   # Normal wait
        
        sched = PriorityScheduler(
            [p_starved_long, p_fresh_short],
            tie_breaker="dual_tier",
            emergency_threshold=40
        )
        sched.time = 45
        selected = sched.select_process()
        # Even though P_FRESH has remaining burst 2 vs 30, P_STARVED has waited 45 ticks (>= 40)
        # and therefore wins arbitration in Urgency Tier 0!
        self.assertEqual(selected.pid, "P_STARVED")

    def test_comparator_candidate_runners_and_invariants(self):
        workload = [
            ("P1", 0, 15, 3),
            ("P2", 2, 2, 4),
            ("P3", 4, 30, 5),
            ("P4", 5, 1, 2),
            ("P5", 10, 4, 3),
        ]
        comp = SchedulerComparator(workload)
        
        res_a = comp.run_ttca_cand_a()
        res_b = comp.run_ttca_cand_b()
        res_c = comp.run_ttca_cand_c()

        self.assertEqual(res_a["policy"], "ttca_v2_cand_a")
        self.assertEqual(res_b["policy"], "ttca_v2_cand_b")
        self.assertEqual(res_c["policy"], "ttca_v2_cand_c")

        # Verify all 8 invariants on all 3 candidates
        validate_scheduling_invariants(res_a["processes"], res_a["scheduler"], workload)
        validate_scheduling_invariants(res_b["processes"], res_b["scheduler"], workload)
        validate_scheduling_invariants(res_c["processes"], res_c["scheduler"], workload)


if __name__ == "__main__":
    unittest.main()

