"""
StarveGuard TTCA v2 Publication-Quality Graph Generator.

Generates comparative charts across all 7 evaluated scheduling policies:
    - Normal Priority
    - Capped Aging (+3)
    - Continuous Aging (K=5)
    - Original TTCA
    - TTCA v2 Candidate A (Adaptive Aging)
    - TTCA v2 Candidate B (SRTF Tie-Breaking)
    - TTCA v2 Candidate C (Dual-Tiered Hybrid TTCA)
"""

import csv
import os
from typing import Dict, List
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

POLICY_COLORS = {
    "normal": "#1f77b4",          # Classic blue
    "capped": "#ff7f0e",          # Orange
    "continuous_k5": "#d62728",   # Crimson red
    "ttca": "#2ca02c",            # Green
    "ttca_v2_cand_a": "#9467bd",  # Purple
    "ttca_v2_cand_b": "#00bcd4",  # Cyan / Teal
    "ttca_v2_cand_c": "#ff9800",  # Amber
}

POLICY_LABELS = {
    "normal": "Normal Priority",
    "capped": "Capped (+3)",
    "continuous_k5": "Continuous (K=5)",
    "ttca": "Original TTCA",
    "ttca_v2_cand_a": "Cand A (Adaptive)",
    "ttca_v2_cand_b": "Cand B (SRTF Tie-Break)",
    "ttca_v2_cand_c": "Cand C (Dual-Tier Hybrid)",
}

SCALES = ["small", "medium", "large", "very_large", "stress"]
SCALE_LABELS = ["Small (10)", "Medium (50)", "Large (100)", "Very Large (250)", "Stress (500)"]
POLICIES = ["normal", "capped", "continuous_k5", "ttca", "ttca_v2_cand_a", "ttca_v2_cand_b", "ttca_v2_cand_c"]


def load_aggregate_data(csv_path: str) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Loads aggregate_summary.csv into a nested structure: data[scale][category][policy] = row."""
    data = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            s = r["scale"]
            c = r["category"]
            p = r["policy"]
            if s not in data:
                data[s] = {}
            if c not in data[s]:
                data[s][c] = {}
            data[s][c][p] = {k: float(v) for k, v in r.items() if k.endswith("_mean") or k == "trials"}
    return data


def compute_scale_means(data: Dict, metric: str) -> Dict[str, List[float]]:
    """Computes overall mean of a metric across all categories for each scale."""
    means_by_policy = {p: [] for p in POLICIES}
    for s in SCALES:
        for p in POLICIES:
            cat_vals = [data[s][c][p][f"{metric}_mean"] for c in data[s] if p in data[s][c]]
            mean_v = sum(cat_vals) / len(cat_vals) if cat_vals else 0.0
            means_by_policy[p].append(mean_v)
    return means_by_policy


def generate_ttca_v2_graphs(data_dir: str, graphs_dir: str) -> List[str]:
    os.makedirs(graphs_dir, exist_ok=True)
    agg_csv = os.path.join(data_dir, "aggregate_summary.csv")
    if not os.path.exists(agg_csv):
        print(f"Cannot generate graphs: {agg_csv} not found.")
        return []

    data = load_aggregate_data(agg_csv)
    created_graphs = []

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "figure.titlesize": 14,
        "legend.fontsize": 9,
        "grid.alpha": 0.4,
    })

    # 1. Average Waiting Time across Scales
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    wt_means = compute_scale_means(data, "average_waiting")
    x = np.arange(len(SCALES))
    width = 0.12

    for i, p in enumerate(POLICIES):
        offset = (i - len(POLICIES) / 2 + 0.5) * width
        ax.bar(x + offset, wt_means[p], width, label=POLICY_LABELS[p], color=POLICY_COLORS[p], edgecolor="black", linewidth=0.5)

    ax.set_ylabel("Mean Average Waiting Time (ticks)")
    ax.set_title("Average Waiting Time Comparison Across Process Scales (All 7 Categories)")
    ax.set_xticks(x)
    ax.set_xticklabels(SCALE_LABELS)
    ax.grid(axis="y", linestyle="--")
    ax.legend(loc="upper left")
    plt.tight_layout()
    p1 = os.path.join(graphs_dir, "average_waiting_time_comparison.png")
    fig.savefig(p1)
    plt.close(fig)
    created_graphs.append(p1)

    # 2. Starvation Threshold-Crossing Percentage across Scales
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    starv_means = compute_scale_means(data, "starvation_percentage")

    for i, p in enumerate(POLICIES):
        offset = (i - len(POLICIES) / 2 + 0.5) * width
        ax.bar(x + offset, starv_means[p], width, label=POLICY_LABELS[p], color=POLICY_COLORS[p], edgecolor="black", linewidth=0.5)

    ax.set_ylabel("Starvation Threshold-Crossing (%)")
    ax.set_title("Starvation Threshold-Crossing Percentage Across Scales (Threshold = 20)")
    ax.set_xticks(x)
    ax.set_xticklabels(SCALE_LABELS)
    ax.grid(axis="y", linestyle="--")
    ax.legend(loc="upper left")
    plt.tight_layout()
    p2 = os.path.join(graphs_dir, "starvation_percentage_comparison.png")
    fig.savefig(p2)
    plt.close(fig)
    created_graphs.append(p2)

    # 3. Category C (Bimodal Bursts) Waiting Time Focus
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    cat_c_wt = {p: [data[s]["C"][p]["average_waiting_mean"] for s in SCALES] for p in POLICIES}

    for i, p in enumerate(POLICIES):
        offset = (i - len(POLICIES) / 2 + 0.5) * width
        ax.bar(x + offset, cat_c_wt[p], width, label=POLICY_LABELS[p], color=POLICY_COLORS[p], edgecolor="black", linewidth=0.5)

    ax.set_ylabel("Mean Waiting Time (ticks)")
    ax.set_title("Category C (Short/Long Burst Mixture): Waiting Time Under Burst Heterogeneity")
    ax.set_xticks(x)
    ax.set_xticklabels(SCALE_LABELS)
    ax.grid(axis="y", linestyle="--")
    ax.legend(loc="upper left")
    plt.tight_layout()
    p3 = os.path.join(graphs_dir, "category_c_burst_mixture_waiting.png")
    fig.savefig(p3)
    plt.close(fig)
    created_graphs.append(p3)

    # 4. Average Response Time across Scales
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    resp_means = compute_scale_means(data, "average_response")

    for i, p in enumerate(POLICIES):
        offset = (i - len(POLICIES) / 2 + 0.5) * width
        ax.bar(x + offset, resp_means[p], width, label=POLICY_LABELS[p], color=POLICY_COLORS[p], edgecolor="black", linewidth=0.5)

    ax.set_ylabel("Mean Average Response Time (ticks)")
    ax.set_title("Average Response Time Comparison Across Process Scales")
    ax.set_xticks(x)
    ax.set_xticklabels(SCALE_LABELS)
    ax.grid(axis="y", linestyle="--")
    ax.legend(loc="upper left")
    plt.tight_layout()
    p4 = os.path.join(graphs_dir, "average_response_time_comparison.png")
    fig.savefig(p4)
    plt.close(fig)
    created_graphs.append(p4)

    # 5. Jain's Fairness Index across Scales
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    fair_means = compute_scale_means(data, "fairness")

    for i, p in enumerate(POLICIES):
        offset = (i - len(POLICIES) / 2 + 0.5) * width
        ax.bar(x + offset, fair_means[p], width, label=POLICY_LABELS[p], color=POLICY_COLORS[p], edgecolor="black", linewidth=0.5)

    ax.set_ylabel("Jain's Fairness Index")
    ax.set_title("Jain's Fairness Index Across Process Scales")
    ax.set_xticks(x)
    ax.set_xticklabels(SCALE_LABELS)
    ax.grid(axis="y", linestyle="--")
    ax.legend(loc="upper right")
    plt.tight_layout()
    p5 = os.path.join(graphs_dir, "fairness_index_comparison.png")
    fig.savefig(p5)
    plt.close(fig)
    created_graphs.append(p5)

    # 6. Post-Threshold Waiting Time Comparison
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    post_wt_means = compute_scale_means(data, "post_threshold_average_waiting")

    for i, p in enumerate(POLICIES):
        offset = (i - len(POLICIES) / 2 + 0.5) * width
        ax.bar(x + offset, post_wt_means[p], width, label=POLICY_LABELS[p], color=POLICY_COLORS[p], edgecolor="black", linewidth=0.5)

    ax.set_ylabel("Post-Threshold Additional Waiting (ticks)")
    ax.set_title("Post-Threshold Waiting Time (Delay Accumulated After Crossing W >= 20)")
    ax.set_xticks(x)
    ax.set_xticklabels(SCALE_LABELS)
    ax.grid(axis="y", linestyle="--")
    ax.legend(loc="upper left")
    plt.tight_layout()
    p6 = os.path.join(graphs_dir, "post_threshold_waiting_comparison.png")
    fig.savefig(p6)
    plt.close(fig)
    created_graphs.append(p6)

    return created_graphs
