"""
StarveGuard Automated Benchmark Graph Generation Module.

Generates 12 publication-quality Matplotlib figures:
    1. Average Waiting Time vs Process Count
    2. Average Turnaround Time vs Process Count
    3. Average Response Time vs Process Count
    4. Maximum Waiting Time vs Process Count
    5. Jain's Fairness Index vs Process Count
    6. Starvation Percentage vs Process Count
    7. CPU Utilization vs Process Count
    8. Throughput vs Process Count
    9. Scheduling Overhead vs Process Count
    10. Percentage Improvement/Regression Heatmap
    11. Policy Comparison Across Workload Categories
    12. Mean Performance with 95% Confidence Intervals
"""

import csv
import os
from typing import Dict, List, Optional, Tuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np

POLICY_PALETTE = {
    "normal": "#1D4ED8",         # Royal Blue
    "capped": "#D97706",         # Amber
    "continuous_k5": "#DC2626",  # Crimson Red
    "ttca": "#059669",           # Emerald Green
}

POLICY_LABELS = {
    "normal": "Normal Priority",
    "capped": "Capped Aging (+3)",
    "continuous_k5": "Continuous Aging (K=5)",
    "ttca": "TTCA (Apex Isolation)",
}

SCALE_ORDER = ["small", "medium", "large", "very_large", "stress"]
SCALE_LABELS = {
    "small": "Small\n(N=10)",
    "medium": "Medium\n(N=50)",
    "large": "Large\n(N=100)",
    "very_large": "Very Large\n(N=250)",
    "stress": "Stress\n(N=500)",
}


def load_aggregate_data(csv_path: str) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Loads aggregate_summary.csv into a structured dict:
    data[scale][policy][metric_mean] -> float
    """
    data: Dict[str, Dict[str, Dict[str, float]]] = {}
    if not os.path.exists(csv_path):
        return data

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scale = row["scale"]
            policy = row["policy"]
            if scale not in data:
                data[scale] = {}
            if policy not in data[scale]:
                data[scale][policy] = {}

            # Average over categories for overall scale summary
            for col, val in row.items():
                if col.endswith("_mean") or col.endswith("_std") or col.endswith("_ci95_margin"):
                    try:
                        fval = float(val)
                        if col not in data[scale][policy]:
                            data[scale][policy][col] = []
                        data[scale][policy][col].append(fval)
                    except ValueError:
                        pass

    # Average metric values across categories for high-level scale trends
    summary: Dict[str, Dict[str, Dict[str, float]]] = {}
    for scale in data:
        summary[scale] = {}
        for policy in data[scale]:
            summary[scale][policy] = {}
            for col, val_list in data[scale][policy].items():
                summary[scale][policy][col] = float(np.mean(val_list))

    return summary


def plot_metric_vs_scale(
    agg_data: Dict[str, Dict[str, Dict[str, float]]],
    metric_name: str,
    title: str,
    ylabel: str,
    output_path: str,
    ylim: Optional[Tuple[float, float]] = None
) -> None:
    """Generates a line and point plot of a metric across workload scales."""
    fig = Figure(figsize=(10, 6), dpi=150, constrained_layout=True)
    ax = fig.add_subplot(111)

    scales = [s for s in SCALE_ORDER if s in agg_data]
    if not scales:
        return

    x = np.arange(len(scales))

    for policy in ["normal", "capped", "continuous_k5", "ttca"]:
        means = []
        for s in scales:
            p_data = agg_data[s].get(policy, {})
            means.append(p_data.get(f"{metric_name}_mean", 0.0))

        ax.plot(
            x,
            means,
            marker="o",
            linewidth=2.2,
            markersize=7,
            label=POLICY_LABELS[policy],
            color=POLICY_PALETTE[policy],
            zorder=4
        )

        for xi, yi in zip(x, means):
            fmt = "%.1f" if max(means) > 5 else "%.3f"
            ax.annotate(
                fmt % yi,
                (xi, yi),
                textcoords="offset points",
                xytext=(0, 7),
                ha="center",
                fontsize=8,
                color="#0F172A",
                fontweight="bold"
            )

    ax.set_xticks(x)
    ax.set_xticklabels([SCALE_LABELS.get(s, s) for s in scales], fontsize=9.5)
    ax.set_xlabel("Workload Scale (Process Count)", fontsize=10.5, fontweight="bold", labelpad=8)
    ax.set_ylabel(ylabel, fontsize=10.5, fontweight="bold", labelpad=8)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=12)

    if ylim:
        ax.set_ylim(ylim)
    ax.grid(axis="y", linestyle="--", alpha=0.6, color="#CBD5E1")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#94A3B8")
    ax.spines["bottom"].set_color("#94A3B8")
    ax.legend(framealpha=0.95, edgecolor="#CBD5E1", fontsize=9.5, loc="upper left")

    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_percentage_heatmap(pct_csv_path: str, output_path: str) -> None:
    """Generates a percentage improvement/regression heatmap across scales and policies."""
    if not os.path.exists(pct_csv_path):
        return

    metrics = ["average_waiting", "average_turnaround", "average_response", "maximum_waiting", "fairness", "starvation_percentage"]
    metric_labels = ["Avg Wait Time", "Avg Turnaround", "Avg Response", "Max Wait Time", "Jain Fairness", "Starvation %"]

    scales = [s for s in SCALE_ORDER]
    policies = ["capped", "continuous_k5", "ttca"]

    # Matrix: rows = (policy, scale), cols = metrics
    row_labels = []
    matrix = []

    scale_lookup = {}
    with open(pct_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            key = (r["scale"], r["policy"])
            if key not in scale_lookup:
                scale_lookup[key] = {m: [] for m in metrics}
            for m in metrics:
                try:
                    scale_lookup[key][m].append(float(r[f"{m}_delta_pct"]))
                except ValueError:
                    pass

    for pol in policies:
        for s in scales:
            key = (s, pol)
            if key in scale_lookup:
                row_labels.append(f"{POLICY_LABELS[pol][:10]} ({s[:3].upper()})")
                row_vals = []
                for m in metrics:
                    vals = scale_lookup[key][m]
                    row_vals.append(float(np.mean(vals)) if vals else 0.0)
                matrix.append(row_vals)

    if not matrix:
        return

    arr = np.array(matrix)
    # Clip extreme percentage values for clear color visualization [-50%, +50%]
    clipped = np.clip(arr, -50.0, 50.0)

    fig = Figure(figsize=(11, 7), dpi=150, constrained_layout=True)
    ax = fig.add_subplot(111)

    # Coolwarm colormap (blue = improvement/reduction, red = regression/inflation)
    try:
        cmap = matplotlib.colormaps["coolwarm_r"]
    except Exception:
        cmap = plt.cm.get_cmap("coolwarm_r")
    cax = ax.imshow(clipped, cmap=cmap, aspect="auto", vmin=-50, vmax=50)

    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(metric_labels, fontsize=9.5, fontweight="bold", rotation=20, ha="right")
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels, fontsize=8.5)

    for i in range(len(row_labels)):
        for j in range(len(metrics)):
            val = arr[i, j]
            text = f"{val:+.1f}%" if abs(val) < 1000 else ">+999%"
            color = "#000000" if abs(clipped[i, j]) < 35 else "#FFFFFF"
            ax.text(j, i, text, ha="center", va="center", color=color, fontsize=8, fontweight="bold")

    ax.set_title("Percentage Change vs. Normal Priority Scheduling (Mean across Categories)", fontsize=11.5, fontweight="bold", pad=12)
    cbar = fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Delta % (Negative = Improvement in Latency, Positive = Inflation)", fontsize=9)

    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_category_comparison(agg_csv_path: str, output_path: str) -> None:
    """Generates grouped bar chart comparing policies across categories for Large scale."""
    if not os.path.exists(agg_csv_path):
        return

    all_rows = []
    with open(agg_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            all_rows.append(r)

    if not all_rows:
        return

    scales_present = [r["scale"] for r in all_rows]
    target_scale = "large"
    if "large" not in scales_present:
        if "medium" in scales_present:
            target_scale = "medium"
        elif "stress" in scales_present:
            target_scale = "stress"
        elif "very_large" in scales_present:
            target_scale = "very_large"
        else:
            target_scale = scales_present[0]

    cat_data = {}
    for r in all_rows:
        if r["scale"] == target_scale:
            cat = r["category"]
            pol = r["policy"]
            if cat not in cat_data:
                cat_data[cat] = {}
            cat_data[cat][pol] = float(r["average_waiting_mean"])

    if not cat_data:
        return

    categories = sorted(cat_data.keys())
    fig = Figure(figsize=(11, 6), dpi=150, constrained_layout=True)
    ax = fig.add_subplot(111)

    x = np.arange(len(categories))
    width = 0.20

    for idx, pol in enumerate(["normal", "capped", "continuous_k5", "ttca"]):
        vals = [cat_data[c].get(pol, 0.0) for c in categories]
        rects = ax.bar(
            x + (idx - 1.5) * width,
            vals,
            width,
            label=POLICY_LABELS[pol],
            color=POLICY_PALETTE[pol],
            zorder=3
        )

    ax.set_xticks(x)
    cat_names = [f"Cat {c}\n({c_desc[:12]})" for c, c_desc in [
        ("A", "Balanced"), ("B", "PrioritySkew"), ("C", "BurstMix"),
        ("D", "Contention"), ("E", "Staggered"), ("F", "Starvation"), ("G", "Realistic")
    ] if c in categories]

    ax.set_xticklabels(cat_names, fontsize=9)
    ax.set_ylabel("Average Waiting Time (ticks)", fontsize=10, fontweight="bold")
    ax.set_title("Average Waiting Time Comparison Across Workload Categories (Large Scale)", fontsize=11.5, fontweight="bold", pad=12)
    ax.grid(axis="y", linestyle="--", alpha=0.6, color="#CBD5E1")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(framealpha=0.95, edgecolor="#CBD5E1", fontsize=9, loc="upper left")

    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_confidence_intervals(agg_data: Dict[str, Dict[str, Dict[str, float]]], output_path: str) -> None:
    """Generates an error-bar plot with 95% Confidence Intervals for Waiting and Response times."""
    scales = [s for s in SCALE_ORDER if s in agg_data]
    if not scales:
        return

    fig = Figure(figsize=(11, 6), dpi=150, constrained_layout=True)
    ax = fig.add_subplot(111)

    x = np.arange(len(scales))
    width = 0.20

    for idx, pol in enumerate(["normal", "capped", "continuous_k5", "ttca"]):
        means = [agg_data[s].get(pol, {}).get("average_waiting_mean", 0.0) for s in scales]
        margins = [agg_data[s].get(pol, {}).get("average_waiting_ci95_margin", 0.0) for s in scales]

        ax.errorbar(
            x + (idx - 1.5) * width,
            means,
            yerr=margins,
            fmt="o",
            capsize=4,
            capthick=1.5,
            linewidth=2,
            label=POLICY_LABELS[pol],
            color=POLICY_PALETTE[pol],
            zorder=4
        )

    ax.set_xticks(x)
    ax.set_xticklabels([SCALE_LABELS.get(s, s) for s in scales], fontsize=9.5)
    ax.set_ylabel("Average Waiting Time (clock ticks)", fontsize=10, fontweight="bold")
    ax.set_xlabel("Workload Scale", fontsize=10, fontweight="bold")
    ax.set_title("Mean Waiting Time with 95% Confidence Intervals across Scales", fontsize=11.5, fontweight="bold", pad=12)
    ax.grid(axis="y", linestyle="--", alpha=0.6, color="#CBD5E1")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(framealpha=0.95, edgecolor="#CBD5E1", fontsize=9, loc="upper left")

    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def generate_all_evaluation_graphs(
    evaluation_dir: str,
    output_graphs_dir: Optional[str] = None
) -> List[str]:
    """Generates all 12 required graphs and returns list of created image file paths."""
    if output_graphs_dir is None:
        output_graphs_dir = os.path.join(evaluation_dir, "graphs")
    os.makedirs(output_graphs_dir, exist_ok=True)

    agg_csv = os.path.join(evaluation_dir, "aggregate_summary.csv")
    pct_csv = os.path.join(evaluation_dir, "percentage_comparison.csv")

    if not os.path.exists(agg_csv):
        print(f"Warning: {agg_csv} not found. Cannot generate graphs.")
        return []

    agg_data = load_aggregate_data(agg_csv)
    created_graphs = []

    # 1. Average Waiting Time vs Process Count
    p1 = os.path.join(output_graphs_dir, "01_average_waiting_time_vs_scale.png")
    plot_metric_vs_scale(agg_data, "average_waiting", "Average Waiting Time vs. Process Count", "Average Waiting Time (ticks)", p1)
    created_graphs.append(p1)

    # 2. Average Turnaround Time vs Process Count
    p2 = os.path.join(output_graphs_dir, "02_average_turnaround_time_vs_scale.png")
    plot_metric_vs_scale(agg_data, "average_turnaround", "Average Turnaround Time vs. Process Count", "Average Turnaround Time (ticks)", p2)
    created_graphs.append(p2)

    # 3. Average Response Time vs Process Count
    p3 = os.path.join(output_graphs_dir, "03_average_response_time_vs_scale.png")
    plot_metric_vs_scale(agg_data, "average_response", "Average Response Time vs. Process Count", "Average Response Time (ticks)", p3)
    created_graphs.append(p3)

    # 4. Maximum Waiting Time vs Process Count
    p4 = os.path.join(output_graphs_dir, "04_maximum_waiting_time_vs_scale.png")
    plot_metric_vs_scale(agg_data, "maximum_waiting", "Maximum Waiting Time vs. Process Count", "Maximum Waiting Time (ticks)", p4)
    created_graphs.append(p4)

    # 5. Jain's Fairness Index vs Process Count
    p5 = os.path.join(output_graphs_dir, "05_jains_fairness_index_vs_scale.png")
    plot_metric_vs_scale(agg_data, "fairness", "Jain's Fairness Index (burst/turnaround) vs. Process Count", "Jain's Fairness Index (0 to 1)", p5, ylim=(0.0, 1.05))
    created_graphs.append(p5)

    # 6. Starvation Percentage vs Process Count
    p6 = os.path.join(output_graphs_dir, "06_starvation_percentage_vs_scale.png")
    plot_metric_vs_scale(agg_data, "starvation_percentage", "Starvation-Threshold Crossing Rate (Waiting >= 20) vs. Process Count", "Starvation-Threshold Crossings (%)", p6)
    created_graphs.append(p6)

    # 7. CPU Utilization vs Process Count
    p7 = os.path.join(output_graphs_dir, "07_cpu_utilization_vs_scale.png")
    plot_metric_vs_scale(agg_data, "cpu_utilization", "CPU Utilization vs. Process Count", "CPU Utilization (%)", p7, ylim=(0.0, 105.0))
    created_graphs.append(p7)

    # 8. Throughput vs Process Count
    p8 = os.path.join(output_graphs_dir, "08_throughput_vs_scale.png")
    plot_metric_vs_scale(agg_data, "throughput", "System Throughput vs. Process Count", "Throughput (completed processes / tick)", p8)
    created_graphs.append(p8)

    # 9. Scheduling Overhead vs Process Count
    p9 = os.path.join(output_graphs_dir, "09_scheduling_overhead_vs_scale.png")
    plot_metric_vs_scale(agg_data, "avg_decision_time_us", "Simulator Decision Logic Overhead vs. Process Count", "Decision Overhead (μs/decision)", p9)
    created_graphs.append(p9)

    # 10. Percentage improvement/regression heatmap
    p10 = os.path.join(output_graphs_dir, "10_percentage_comparison_heatmap.png")
    plot_percentage_heatmap(pct_csv, p10)
    created_graphs.append(p10)

    # 11. Policy comparison across workload categories
    p11 = os.path.join(output_graphs_dir, "11_workload_category_comparison.png")
    plot_category_comparison(agg_csv, p11)
    created_graphs.append(p11)

    # 12. Mean performance with confidence intervals
    p12 = os.path.join(output_graphs_dir, "12_mean_performance_confidence_intervals.png")
    plot_confidence_intervals(agg_data, p12)
    created_graphs.append(p12)

    return created_graphs
