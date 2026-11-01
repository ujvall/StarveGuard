from typing import Optional, Union


class BaseAgingPolicy:
    """Base interface for priority aging policies in StarveGuard."""

    def calculate_boost(self, metric_value: int) -> int:
        raise NotImplementedError

    def apply_aging(self, process, score: Optional[int] = None, **kwargs) -> bool:
        raise NotImplementedError


class CappedAgingPolicy(BaseAgingPolicy):
    """
    Original 3-tier capped aging policy:
        - Score < 10:  boost = 0 (effective priority = original_priority)
        - Score 10-19: boost = 1 (effective priority = max(1, original_priority - 1))
        - Score 20-29: boost = 2 (effective priority = max(1, original_priority - 2))
        - Score >= 30: boost = 3 (effective priority = max(1, original_priority - 3))

    Anchored to original_priority with a hard cap of max_boost (+3) and a floor of 1.
    """

    def __init__(self, max_boost: int = 3, floor: int = 1):
        self.max_boost = max_boost
        self.floor = floor

    def calculate_boost(self, starvation_score: int) -> int:
        if starvation_score >= 30:
            return min(3, self.max_boost)
        elif starvation_score >= 20:
            return min(2, self.max_boost)
        elif starvation_score >= 10:
            return min(1, self.max_boost)
        else:
            return 0

    def apply_aging(self, process, score: Optional[int] = None, **kwargs) -> bool:
        val = score if score is not None else process.waiting_time
        boost = self.calculate_boost(val)
        new_priority = max(self.floor, process.original_priority - boost)

        if new_priority != process.current_priority:
            process.current_priority = new_priority
            process.aging_adjustments += 1
            return True
        return False


class ContinuousAgingPolicy(BaseAgingPolicy):
    """
    Continuous waiting-time-based aging policy with a priority floor of 1:
        P_i^{eff}(t) = max(floor, P_i^{base} - floor(W_i(t) / K))

    Where:
        - P_i^{eff}(t): effective priority at scheduling decision.
        - P_i^{base}: process.original_priority (unmodified).
        - W_i(t): accumulated time spent ready but not executing (process.waiting_time).
        - K: waiting-time interval required for one priority improvement.
        - floor: 1 (minimum effective priority boundary).
    """

    def __init__(self, k: int = 5, floor: int = 1):
        if k <= 0:
            raise ValueError(f"Aging interval K must be a positive integer (> 0), got {k}.")
        self.k = k
        self.floor = floor

    def calculate_boost(self, waiting_time: int) -> int:
        if waiting_time < 0:
            return 0
        return waiting_time // self.k

    def apply_aging(self, process, score: Optional[int] = None, **kwargs) -> bool:
        # W_i(t) represents accumulated time spent ready but not executing
        w_i = process.waiting_time
        boost = self.calculate_boost(w_i)
        new_priority = max(self.floor, process.original_priority - boost)

        if new_priority != process.current_priority:
            process.current_priority = new_priority
            process.aging_adjustments += 1
            return True
        return False


class ConservativeAgingPolicy(BaseAgingPolicy):
    """
    Threshold-Triggered Conservative Aging (TTCA) Policy with Apex Isolation:
        - Starvation score < threshold (default 20): No boost (effective priority = original_priority)
        - Starvation score >= threshold:
            - Original Priority 1: Retains priority 1 (effective priority = 1)
            - Original Priority > 1:
                boost = min(max_boost, 1 + (starvation_score - threshold) // k_starve)
                effective_priority = max(floor, original_priority - boost)

    Where:
        - threshold: 20 (inactivity gate; healthy jobs are never aged)
        - k_starve: 10 (pace of subsequent boosts beyond threshold)
        - max_boost: 3 (bounded escalation ceiling)
        - floor: 2 for processes with original_priority > 1 (apex isolation)
    """

    def __init__(
        self,
        threshold: int = 20,
        k_starve: int = 10,
        max_boost: int = 3,
        floor: int = 2
    ):
        if threshold < 0:
            raise ValueError(f"Threshold must be non-negative, got {threshold}.")
        if k_starve <= 0:
            raise ValueError(f"Interval k_starve must be positive (> 0), got {k_starve}.")
        if max_boost < 0:
            raise ValueError(f"max_boost must be non-negative, got {max_boost}.")
        self.threshold = threshold
        self.k_starve = k_starve
        self.max_boost = max_boost
        self.floor = floor

    def calculate_boost(self, starvation_score: int) -> int:
        if starvation_score < self.threshold:
            return 0
        return min(
            self.max_boost,
            1 + (starvation_score - self.threshold) // self.k_starve
        )

    def apply_aging(self, process, score: Optional[int] = None, **kwargs) -> bool:
        val = score if score is not None else process.waiting_time
        if val < self.threshold:
            new_priority = process.original_priority
        elif process.original_priority == 1:
            new_priority = 1
        else:
            boost = self.calculate_boost(val)
            new_priority = max(self.floor, process.original_priority - boost)

        if new_priority != process.current_priority:
            process.current_priority = new_priority
            process.aging_adjustments += 1
            return True
        return False


class AdaptiveAgingPolicy(BaseAgingPolicy):
    """
    Threshold-Triggered Adaptive Aging Policy with Burst Pacing and Apex Isolation:
        - Starvation score < threshold (default 20): No boost (effective priority = original_priority)
        - Starvation score >= threshold:
            - Original Priority 1: Retains priority 1 (effective priority = 1)
            - Original Priority > 1:
                Dynamic aging interval:
                k_eff = max(1, k_base + (process.remaining_time // burst_scale))
                boost = min(max_boost, 1 + (starvation_score - threshold) // k_eff)
                effective_priority = max(floor, original_priority - boost)

    Where:
        - threshold: 20 (inactivity gate; healthy jobs are never aged)
        - k_base: 10 (base interval)
        - burst_scale: 10 (scales interval by remaining burst so long batch jobs pace their aging)
        - max_boost: 3 (bounded escalation ceiling)
        - floor: 2 for processes with original_priority > 1 (apex isolation)
    """

    def __init__(
        self,
        threshold: int = 20,
        k_base: int = 10,
        burst_scale: int = 10,
        max_boost: int = 3,
        floor: int = 2
    ):
        if threshold < 0:
            raise ValueError(f"Threshold must be non-negative, got {threshold}.")
        if k_base <= 0:
            raise ValueError(f"Interval k_base must be positive (> 0), got {k_base}.")
        if burst_scale < 0:
            raise ValueError(f"burst_scale must be non-negative, got {burst_scale}.")
        if max_boost < 0:
            raise ValueError(f"max_boost must be non-negative, got {max_boost}.")
        self.threshold = threshold
        self.k_base = k_base
        self.burst_scale = burst_scale
        self.max_boost = max_boost
        self.floor = floor

    def calculate_boost(self, starvation_score: int, remaining_time: int = 0) -> int:
        if starvation_score < self.threshold:
            return 0
        k_eff = max(1, self.k_base + (remaining_time // self.burst_scale)) if self.burst_scale > 0 else self.k_base
        return min(
            self.max_boost,
            1 + (starvation_score - self.threshold) // k_eff
        )

    def apply_aging(self, process, score: Optional[int] = None, **kwargs) -> bool:
        val = score if score is not None else process.waiting_time
        if val < self.threshold:
            new_priority = process.original_priority
        elif process.original_priority == 1:
            new_priority = 1
        else:
            boost = self.calculate_boost(val, process.remaining_time)
            new_priority = max(self.floor, process.original_priority - boost)

        if new_priority != process.current_priority:
            process.current_priority = new_priority
            process.aging_adjustments += 1
            return True
        return False


class QueuePressureAgingPolicy(BaseAgingPolicy):
    """
    Queue-Pressure-Aware TTCA Policy with Apex Isolation (Candidate B1 & B4):
        - Starvation score < threshold (default 20): No boost
        - Starvation score >= threshold:
            - Original Priority 1: Retains priority 1
            - Original Priority > 1:
                Accelerates aging interval k_eff when multiple processes with strictly
                higher effective priority are blocking this process in the ready queue:
                k_eff = max(min_k, k_base - min(max_accel, higher_prio_count // pressure_scale))
                boost = min(max_boost, 1 + (starvation_score - threshold) // k_eff)
                effective_priority = max(floor, original_priority - boost)

    Where:
        - threshold: 20 (inactivity gate)
        - k_base: 10 (base interval)
        - min_k: 6 (maximum acceleration boundary)
        - max_boost: 3 (bounded escalation ceiling)
        - floor: 2 for processes with original_priority > 1 (apex isolation)
    """

    def __init__(
        self,
        threshold: int = 20,
        k_base: int = 10,
        min_k: int = 6,
        pressure_scale: int = 2,
        max_boost: int = 3,
        floor: int = 2
    ):
        if threshold < 0:
            raise ValueError(f"Threshold must be non-negative, got {threshold}.")
        if k_base <= 0:
            raise ValueError(f"Interval k_base must be positive (> 0), got {k_base}.")
        if max_boost < 0:
            raise ValueError(f"max_boost must be non-negative, got {max_boost}.")
        self.threshold = threshold
        self.k_base = k_base
        self.min_k = min_k
        self.pressure_scale = max(1, pressure_scale)
        self.max_boost = max_boost
        self.floor = floor

    def calculate_boost(self, starvation_score: int, higher_prio_count: int = 0) -> int:
        if starvation_score < self.threshold:
            return 0
        accel = min(self.k_base - self.min_k, higher_prio_count // self.pressure_scale)
        k_eff = max(self.min_k, self.k_base - accel)
        return min(
            self.max_boost,
            1 + (starvation_score - self.threshold) // k_eff
        )

    def apply_aging(self, process, score: Optional[int] = None, higher_prio_count: int = 0, **kwargs) -> bool:
        val = score if score is not None else process.waiting_time
        if val < self.threshold:
            new_priority = process.original_priority
        elif process.original_priority == 1:
            new_priority = 1
        else:
            boost = self.calculate_boost(val, higher_prio_count=higher_prio_count)
            new_priority = max(self.floor, process.original_priority - boost)

        if new_priority != process.current_priority:
            process.current_priority = new_priority
            process.aging_adjustments += 1
            return True
        return False


class AgingManager:
    """
    Aging manager providing a unified, configurable interface for process aging.

    Default configuration maintains 100% backward compatibility with StarveGuard's
    historical capped-aging implementation (policy='capped', max_boost=3).
    Supports:
      - 'capped': Historical 3-tier capped aging (+3 max boost)
      - 'continuous': Continuous waiting-time aging (floor=1, parameter K)
      - 'conservative' / 'ttca': Threshold-Triggered Conservative Aging with apex isolation
    """

    def __init__(
        self,
        policy: Union[str, BaseAgingPolicy] = "capped",
        k: int = 5,
        max_boost: int = 3,
        floor: Optional[int] = None,
        threshold: int = 20,
        k_starve: int = 10,
    ):
        self.k = k
        self.max_boost = max_boost
        self.threshold = threshold
        self.k_starve = k_starve

        if isinstance(policy, BaseAgingPolicy):
            self.policy = policy
            self.policy_name = policy.__class__.__name__
            self.floor = getattr(policy, "floor", 1)
        elif isinstance(policy, str):
            p_name = policy.strip().lower()
            if p_name in ("capped", "capped_aging", "tier", "tiered"):
                self.policy_name = "capped"
                self.floor = 1 if floor is None else floor
                self.policy = CappedAgingPolicy(max_boost=max_boost, floor=self.floor)
            elif p_name in ("continuous", "continuous_aging", "linear"):
                self.policy_name = "continuous"
                self.floor = 1 if floor is None else floor
                self.policy = ContinuousAgingPolicy(k=k, floor=self.floor)
            elif p_name in ("conservative", "ttca", "conservative_aging"):
                self.policy_name = "conservative"
                self.floor = 2 if floor is None else floor
                self.policy = ConservativeAgingPolicy(
                    threshold=threshold,
                    k_starve=k_starve,
                    max_boost=max_boost,
                    floor=self.floor
                )
            elif p_name in ("adaptive", "adaptive_aging", "ttca_cand_a", "ttca_a"):
                self.policy_name = "adaptive"
                self.floor = 2 if floor is None else floor
                self.policy = AdaptiveAgingPolicy(
                    threshold=threshold,
                    k_base=k_starve,
                    max_boost=max_boost,
                    floor=self.floor
                )
            elif p_name in ("queue_pressure", "pressure", "qp", "ttca_v2b_cand_b1"):
                self.policy_name = "queue_pressure"
                self.floor = 2 if floor is None else floor
                self.policy = QueuePressureAgingPolicy(
                    threshold=threshold,
                    k_base=k_starve,
                    max_boost=max_boost,
                    floor=self.floor
                )
            else:
                raise ValueError(
                    f"Unknown aging policy '{policy}'. Supported policies: 'capped', 'continuous', 'conservative', 'adaptive', 'queue_pressure'."
                )
        else:
            raise TypeError(f"Invalid policy type: {type(policy)}. Must be str or BaseAgingPolicy.")

    def calculate_boost(self, score_or_waiting: int, **kwargs) -> int:
        return self.policy.calculate_boost(score_or_waiting, **kwargs)

    def apply_aging(self, process, score: Optional[int] = None, **kwargs) -> bool:
        return self.policy.apply_aging(process, score, **kwargs)


class ContinuousAgingManager(AgingManager):
    """Convenience subclass for continuous waiting-time aging with parameter K."""

    def __init__(self, k: int = 5, floor: int = 1):
        super().__init__(policy="continuous", k=k, floor=floor)


class ConservativeAgingManager(AgingManager):
    """Convenience subclass for Threshold-Triggered Conservative Aging (TTCA)."""

    def __init__(
        self,
        threshold: int = 20,
        k_starve: int = 10,
        max_boost: int = 3,
        floor: int = 2
    ):
        super().__init__(
            policy="conservative",
            threshold=threshold,
            k_starve=k_starve,
            max_boost=max_boost,
            floor=floor
        )


class AdaptiveAgingManager(AgingManager):
    """Convenience subclass for Threshold-Triggered Adaptive Aging."""

    def __init__(
        self,
        threshold: int = 20,
        k_base: int = 10,
        burst_scale: int = 10,
        max_boost: int = 3,
        floor: int = 2
    ):
        super().__init__(
            policy="adaptive",
            threshold=threshold,
            k_starve=k_base,
            max_boost=max_boost,
            floor=floor
        )


class QueuePressureAgingManager(AgingManager):
    """Convenience subclass for Queue-Pressure-Aware TTCA (Candidate B1 & B4)."""

    def __init__(
        self,
        threshold: int = 20,
        k_base: int = 10,
        min_k: int = 6,
        pressure_scale: int = 2,
        max_boost: int = 3,
        floor: int = 2
    ):
        super().__init__(
            policy="queue_pressure",
            threshold=threshold,
            k_starve=k_base,
            max_boost=max_boost,
            floor=floor
        )
