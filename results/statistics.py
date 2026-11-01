"""
StarveGuard Statistical Analysis Module.

Provides rigorous, independent statistical aggregation and hypothesis testing:
    - Descriptive Statistics: Mean, Sample Std Dev, Min, Max, Median, 95% Confidence Interval.
    - Percentage Comparison: Relative change against Normal Priority baseline with explicit zero-baseline handling.
    - Hypothesis Testing:
        * Paired t-test with Cohen's d_z effect size.
        * Wilcoxon signed-rank test with normal approximation for non-parametric evaluation.
"""

import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


def student_t_critical_value(df: int, alpha: float = 0.05) -> float:
    """
    Returns two-tailed critical value t_{alpha/2, df} for confidence intervals.
    Provides exact precomputed standard values for OS benchmark sample sizes and accurate approximation.
    """
    # Standard lookup for common OS experimental degrees of freedom
    t_table = {
        1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
        6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        14: 2.145, 19: 2.093, 24: 2.064, 29: 2.045, 30: 2.042,
        40: 2.021, 50: 2.009, 60: 2.000, 100: 1.984, 120: 1.980,
    }
    if df in t_table:
        return t_table[df]
    if df > 120:
        return 1.960  # Normal asymptotic limit

    # Find nearest table bounds or interpolate
    keys = sorted(t_table.keys())
    for k in keys:
        if df <= k:
            return t_table[k]
    return 1.960


def student_t_pvalue(t_stat: float, df: int) -> float:
    """Computes exact two-tailed p-value for Student's t distribution with df degrees of freedom."""
    t = abs(t_stat)
    if t == 0.0 or df <= 0:
        return 1.0

    log_c = math.lgamma((df + 1) / 2.0) - 0.5 * math.log(df * math.pi) - math.lgamma(df / 2.0)
    c = math.exp(log_c)

    # Numerical integration using substitute u in [0, 1) where x = t + u / (1 - u)
    u = np.linspace(0.0, 0.99999, 40000)
    x = t + u / (1.0 - u)
    dx_du = 1.0 / ((1.0 - u) ** 2)
    integrand = (1.0 + (x ** 2) / df) ** (-(df + 1) / 2.0) * dx_du
    tail_prob = c * float(np.sum((integrand[:-1] + integrand[1:]) * 0.5 * np.diff(u)))
    return min(1.0, max(0.0, 2.0 * tail_prob))


def compute_summary_statistics(values: List[float]) -> Dict[str, float]:
    """
    Computes comprehensive descriptive statistics across experimental trials:
        - mean
        - std (sample standard deviation with n - 1 df)
        - min
        - max
        - median
        - ci95_margin (margin of error for 95% confidence interval)
        - ci95_lower (lower bound of 95% CI)
        - ci95_upper (upper bound of 95% CI)
    """
    if not values:
        return {
            "mean": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "median": 0.0,
            "ci95_margin": 0.0,
            "ci95_lower": 0.0,
            "ci95_upper": 0.0,
            "n": 0,
        }

    n = len(values)
    mean = float(sum(values) / n)

    if n == 1:
        return {
            "mean": mean,
            "std": 0.0,
            "min": values[0],
            "max": values[0],
            "median": values[0],
            "ci95_margin": 0.0,
            "ci95_lower": values[0],
            "ci95_upper": values[0],
            "n": 1,
        }

    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    std = math.sqrt(max(0.0, var))
    sorted_vals = sorted(values)
    if n % 2 == 1:
        median = float(sorted_vals[n // 2])
    else:
        median = float((sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0)

    t_crit = student_t_critical_value(n - 1)
    se = std / math.sqrt(n)
    ci95_margin = float(t_crit * se)

    return {
        "mean": mean,
        "std": std,
        "min": float(sorted_vals[0]),
        "max": float(sorted_vals[-1]),
        "median": median,
        "ci95_margin": ci95_margin,
        "ci95_lower": mean - ci95_margin,
        "ci95_upper": mean + ci95_margin,
        "n": n,
    }


def compute_percentage_change(
    baseline: float,
    test: float,
    lower_is_better: bool = True
) -> Dict[str, Any]:
    """
    Computes percentage change of a policy metric relative to baseline (Normal Priority):
        pct = ((test - baseline) / baseline) * 100

    Explicitly handles zero baselines to avoid division by zero or misleading claims.
    """
    if baseline == 0.0:
        if test == 0.0:
            return {
                "percentage_change": 0.0,
                "formatted": "0.00%",
                "status": "Identical",
                "is_improvement": False,
                "is_regression": False,
                "zero_baseline": True,
            }
        else:
            status = "Regression" if lower_is_better else "Improvement"
            return {
                "percentage_change": float("inf") if test > 0 else float("-inf"),
                "formatted": f"+{test:.2f} (from 0)",
                "status": status,
                "is_improvement": not lower_is_better,
                "is_regression": lower_is_better,
                "zero_baseline": True,
            }

    diff = test - baseline
    pct = (diff / baseline) * 100.0

    if lower_is_better:
        # Negative percentage means value decreased -> Improvement
        if pct < -0.01:
            status = "Improvement"
            is_imp = True
            is_reg = False
        elif pct > 0.01:
            status = "Regression"
            is_imp = False
            is_reg = True
        else:
            status = "Neutral"
            is_imp = False
            is_reg = False
    else:
        # Higher is better: Positive percentage means value increased -> Improvement
        if pct > 0.01:
            status = "Improvement"
            is_imp = True
            is_reg = False
        elif pct < -0.01:
            status = "Regression"
            is_imp = False
            is_reg = True
        else:
            status = "Neutral"
            is_imp = False
            is_reg = False

    sign = "+" if pct > 0 else ""
    return {
        "percentage_change": pct,
        "formatted": f"{sign}{pct:.2f}%",
        "status": status,
        "is_improvement": is_imp,
        "is_regression": is_reg,
        "zero_baseline": False,
    }


def compute_paired_ttest(
    baseline_values: List[float],
    test_values: List[float]
) -> Dict[str, Any]:
    """
    Performs a paired Student's t-test between identical paired trials:
        d_i = test_i - baseline_i
    Returns t_stat, p_value, mean_diff, std_diff, cohens_d, significant (alpha = 0.05).
    """
    if len(baseline_values) != len(test_values) or len(baseline_values) < 2:
        return {
            "test": "Paired t-test",
            "t_stat": 0.0,
            "p_value": 1.0,
            "mean_diff": 0.0,
            "cohens_d": 0.0,
            "significant": False,
        }

    n = len(baseline_values)
    diffs = [test - base for base, test in zip(baseline_values, test_values)]
    mean_d = sum(diffs) / n
    var_d = sum((d - mean_d) ** 2 for d in diffs) / (n - 1)
    std_d = math.sqrt(max(0.0, var_d))

    if std_d == 0.0:
        # Identical paired values across all trials
        p_val = 1.0 if mean_d == 0.0 else 0.0
        return {
            "test": "Paired t-test",
            "t_stat": 0.0,
            "p_value": p_val,
            "mean_diff": mean_d,
            "cohens_d": 0.0,
            "significant": (p_val < 0.05),
        }

    se_d = std_d / math.sqrt(n)
    t_stat = mean_d / se_d
    p_val = student_t_pvalue(t_stat, n - 1)
    cohens_d = mean_d / std_d

    return {
        "test": "Paired t-test",
        "t_stat": t_stat,
        "p_value": p_val,
        "mean_diff": mean_d,
        "std_diff": std_d,
        "cohens_d": cohens_d,
        "significant": (p_val < 0.05),
    }


def compute_wilcoxon_signed_rank(
    baseline_values: List[float],
    test_values: List[float]
) -> Dict[str, Any]:
    """
    Performs a non-parametric Wilcoxon signed-rank test between paired trials.
    Returns W_stat, z_stat, p_value, effect_size_r, significant (alpha = 0.05).
    """
    if len(baseline_values) != len(test_values) or len(baseline_values) < 2:
        return {
            "test": "Wilcoxon signed-rank",
            "w_stat": 0.0,
            "z_stat": 0.0,
            "p_value": 1.0,
            "effect_size_r": 0.0,
            "significant": False,
        }

    diffs = [b - a for a, b in zip(baseline_values, test_values)]
    nonzero = [d for d in diffs if d != 0.0]
    n = len(nonzero)

    if n == 0:
        return {
            "test": "Wilcoxon signed-rank",
            "w_stat": 0.0,
            "z_stat": 0.0,
            "p_value": 1.0,
            "effect_size_r": 0.0,
            "significant": False,
        }

    abs_diffs = [abs(d) for d in nonzero]
    sorted_indices = sorted(range(n), key=lambda i: abs_diffs[i])
    ranks = [0.0] * n

    i = 0
    while i < n:
        j = i
        while j < n - 1 and abs_diffs[sorted_indices[j]] == abs_diffs[sorted_indices[j + 1]]:
            j += 1
        avg_rank = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[sorted_indices[k]] = avg_rank
        i = j + 1

    pos_ranks = sum(ranks[k] for k in range(n) if nonzero[k] > 0.0)
    neg_ranks = sum(ranks[k] for k in range(n) if nonzero[k] < 0.0)
    w_stat = min(pos_ranks, neg_ranks)

    # Normal approximation with continuity correction for n >= 10
    mean_w = n * (n + 1) / 4.0
    var_w = n * (n + 1) * (2 * n + 1) / 24.0
    sigma_w = math.sqrt(var_w) if var_w > 0 else 1.0

    if w_stat < mean_w:
        z = (w_stat - mean_w + 0.5) / sigma_w
    else:
        z = (w_stat - mean_w - 0.5) / sigma_w

    # Two-tailed p-value from standard normal
    p_val = 2.0 * 0.5 * (1.0 + math.erf(-abs(z) / math.sqrt(2.0)))
    p_val = min(1.0, max(0.0, p_val))
    effect_size_r = abs(z) / math.sqrt(len(baseline_values))

    return {
        "test": "Wilcoxon signed-rank",
        "w_stat": float(w_stat),
        "z_stat": float(z),
        "p_value": float(p_val),
        "effect_size_r": float(effect_size_r),
        "significant": (p_val < 0.05),
    }

