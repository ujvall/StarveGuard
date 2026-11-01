"""
StarveGuard TTCA v2-B+ Publication-Quality Graph Generator.

Generates comparative charts across all evaluated scheduling variants:
    - Normal Priority
    - Original TTCA
    - Candidate B0 (SRTF Control)
    - Candidate B1 (Queue-Pressure-Aware Aging)
    - Candidate B2 (Starvation-Aware SRTF Arbitration)
    - Candidate B3 (Preemption-Efficient Candidate B)
    - Candidate B4 (Best Justified Hybrid)
"""

import csv
import os
from typing import Dict, List
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

POLICY_COLORS = {
    "normal": "#7f7f7f",             # Gray
    "ttca": "#2ca02c",               # Green
    "ttca_v2b_cand_b0": "#1f77b4",   # Blue (Control)
    "ttca_v2b_cand_b1": "#9467bd",   # Purple
    "ttca_v2b_cand_b2": "#00bcd4",   # Cyan / Teal
    "ttca_v2b_cand_b3": "#ff7f0e",   # Orange
    "ttca_v2b_cand_b4": "#e91e63",   # Deep Pink / Rose (Hybrid)
}

POLICY_LABELS = {
    "normal": "Normal Priority",
    "ttca": "Original TTCA",
    "ttca_v2b_cand_b0": "Cand B0 (SRTF Control)",
    "ttca_v2b_cand_b1": "Cand B1 (Queue-Pressure)",
    "ttca_v2b_cand_b2": "Cand B2 (Starvation-Aware)",
    "ttca_v2b_cand_b3": "Cand B3 (Preempt-Efficient)",
    "ttca_v2b_cand_b4": "Cand B4 (Best Hybrid)",
}

SCALES = ["small", "medium", "large", "very_large", "stress"]
SCALE_LABELS = ["Small (10)", "Medium (50)", "Large (100)", "Very Large (250)", "Stress (500)"]
POLICIES = ["normal", "ttca", "ttca_v2b_cand_b0", "ttca_v2b_cand_b1", "ttca_v2b_cand_b2", "ttca_v2b_cand_b3", "ttca_v2b_cand_b4"]


def load_aggregate_data(csv_path: str):
    std_data = {}
    val_data = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            s = r["scale"]
            c = r["category"]
            p = r["policy"]
            is_val = (r.get("is_validation", "False").lower() == "true" or c.startswith("VAL_"))
            row_dict = {k: float(v) for k, v in r.items() if k.endswith("_mean") or k == "trials"}
            if is_val:
                if c not in val_data:
                    val_data[c] = {}
                val_data[c][p] = row_dict
            else:
                if s not in std_data:
                    std_data[s] = {}
                if c not in std_data[s]:
                    std_data[s][c] = {}
                std_data[s][c][p] = row_dict
    return std_data, val_data


def compute_std_scale_means(std_data: Dict, metric: str) -> Dict[str, List[float]]:
    means = {p: [] for p in POLICIES}
    for s in SCALES:
        scale_dict = std_data.get(s, {})
        for p in POLICIES:
            cat_vals = [scale_dict[c][p][f"{metric}_mean"] for c in scale_dict if p in scale_dict[c]]
            means[p].append(sum(cat_vals) / len(cat_vals) if cat_vals else 0.0)
    return means


def generate_ttca_v2b_graphs(data_dir: str, graphs_dir: str) -> List[str]:
    os.makedirs(graphs_dir, exist_ok=True)
    agg_csv = os.path.join(data_dir, "aggregate_summary.csv")
    if not os.path.exists(agg_csv):
        return []

    std_data, val_data = load_aggregate_data(agg_csv)
    created_graphs = []

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "figure.titlesize": 14,
        "legend.fontsize": 8.5,
        "grid.alpha": 0.4,
    })

    # 1. Average Waiting Time across Scales
    fig, ax = plt.subplots(figsize=(13, 6), dpi=300)
    wt_means = compute_std_scale_means(std_data, "average_waiting")
    x = np.arange(len(SCALES))
    width = 0.12

    for i, p in enumerate(POLICIES):
        offset = (i - len(POLICIES) / 2 + 0.5) * width
        ax.bar(x + offset, wt_means[p], width, label=POLICY_LABELS[p], color=POLICY_COLORS[p], edgecolor="black", linewidth=0.5)

    ax.set_ylabel("Mean Average Waiting Time (ticks)")
    ax.set_title("Average Waiting Time Across Scales (Standard 7-Category Matrix)")
    ax.set_xticks(x)
    ax.set_xticklabels(SCALE_LABELS)
    ax.grid(axis="y", linestyle="--")
    ax.legend(loc="upper left")
    plt.tight_layout()
    p1 = os.path.join(graphs_dir, "awt_by_scale.png")
    fig.savefig(p1)
    plt.close(fig)
    created_graphs.append(p1)

    # 2. Maximum Waiting Time Across Scales
    fig, ax = plt.subplots(figsize=(13, 6), dpi=300)
    max_means = compute_std_scale_means(std_data, "maximum_waiting")

    for i, p in enumerate(POLICIES):
        offset = (i - len(POLICIES) / 2 + 0.5) * width
        ax.bar(x + offset, max_means[p], width, label=POLICY_LABELS[p], color=POLICY_COLORS[p], edgecolor="black", linewidth=0.5)

    ax.set_ylabel("Maximum Waiting Time (ticks)")
    ax.set_title("Maximum Waiting Time Comparison Across Scales")
    ax.set_xticks(x)
    ax.set_xticklabels(SCALE_LABELS)
    ax.grid(axis="y", linestyle="--")
    ax.legend(loc="upper left")
    plt.tight_layout()
    p2 = os.path.join(graphs_dir, "max_wait_by_scale.png")
    fig.savefig(p2)
    plt.close(fig)
    created_graphs.append(p2)

    # 3. 95th Percentile Tail Waiting Time Across Scales
    fig, ax = plt.subplots(figsize=(13, 6), dpi=300)
    p95_means = compute_std_scale_means(std_data, "waiting_p95")

    for i, p in enumerate(POLICIES):
        offset = (i - len(POLICIES) / 2 + 0.5) * width
        ax.bar(x + offset, p95_means[p], width, label=POLICY_LABELS[p], color=POLICY_COLORS[p], edgecolor="black", linewidth=0.5)

    ax.set_ylabel("95th Percentile Waiting Time (ticks)")
    ax.set_title("Tail Waiting Latency (p95) Comparison Across Scales")
    ax.set_xticks(x)
    ax.set_xticklabels(SCALE_LABELS)
    ax.grid(axis="y", linestyle="--")
    ax.legend(loc="upper left")
    plt.tight_layout()
    p3 = os.path.join(graphs_dir, "tail_waiting_p95_by_scale.png")
    fig.savefig(p3)
    plt.close(fig)
    created_graphs.append(p3)

    # 4. Longest Continuous Waiting Streak Across Scales
    fig, ax = plt.subplots(figsize=(13, 6), dpi=300)
    streak_means = compute_std_scale_means(std_data, "longest_continuous_wait")

    for i, p in enumerate(POLICIES):
        offset = (i - len(POLICIES) / 2 + 0.5) * width
        ax.bar(x + offset, streak_means[p], width, label=POLICY_LABELS[p], color=POLICY_COLORS[p], edgecolor="black", linewidth=0.5)

    ax.set_ylabel("Longest Continuous Wait Streak (ticks)")
    ax.set_title("Longest Continuous Uninterrupted Waiting Streak Without CPU Allocation")
    ax.set_xticks(x)
    ax.set_xticklabels(SCALE_LABELS)
    ax.grid(axis="y", linestyle="--")
    ax.legend(loc="upper left")
    plt.tight_layout()
    p4 = os.path.join(graphs_dir, "longest_continuous_wait_by_scale.png")
    fig.savefig(p4)
    plt.close(fig)
    created_graphs.append(p4)

    # 5. Independent Validation Scenarios Waiting Time Focus
    if val_data:
        val_scenarios = list(val_data.keys())
        fig, ax = plt.subplots(figsize=(14, 6), dpi=300)
        x_val = np.arange(len(val_scenarios))
        short_labels = [s.replace("VAL_", "") for s in val_scenarios]

        for i, p in enumerate(POLICIES):
            vals = [val_data[s][p]["average_waiting_mean"] if p in val_data[s] else 0.0 for s in val_scenarios]
            offset = (i - len(POLICIES) / 2 + 0.5) * width
            ax.bar(x_val + offset, vals, width, label=POLICY_LABELS[p], color=POLICY_COLORS[p], edgecolor="black", linewidth=0.5)

        ax.set_ylabel("Mean Average Waiting Time (ticks)")
        ax.set_title("Performance Under Out-of-Sample & Adversarial Validation Scenarios")
        ax.set_xticks(x_val)
        ax.set_xticklabels(short_labels, rotation=15, ha="right")
        ax.grid(axis="y", linestyle="--")
        ax.legend(loc="upper left")
        plt.tight_layout()
        p5 = os.path.join(graphs_dir, "validation_scenarios_awt.png")
        fig.savefig(p5)
        plt.close(fig)
        created_graphs.append(p5)

    # 6. Preemption Counts Across Scales
    fig, ax = plt.subplots(figsize=(13, 6), dpi=300)
    preempt_means = compute_std_scale_means(std_data, "preemption_count")

    for i, p in enumerate(POLICIES):
        offset = (i - len(POLICIES) / 2 + 0.5) * width
        ax.bar(x + offset, preempt_means[p], width, label=POLICY_LABELS[p], color=POLICY_COLORS[p], edgecolor="black", linewidth=0.5)

    ax.set_ylabel("Mean Preemption Count")
    ax.set_title("Preemption Count Comparison Across Process Scales")
    ax.set_xticks(x)
    ax.set_xticklabels(SCALE_LABELS)
    ax.grid(axis="y", linestyle="--")
    ax.legend(loc="upper left")
    plt.tight_layout()
    p6 = os.path.join(graphs_dir, "preemption_counts_by_scale.png")
    fig.savefig(p6)
    plt.close(fig)
    created_graphs.append(p6)

    return created_graphs
