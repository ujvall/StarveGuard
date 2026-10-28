import csv
import os
from typing import Dict, List, Optional, Tuple
import matplotlib
matplotlib.use("Agg")  # Safe headless backend for script generation
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


CHART_CONFIGS = {
    "waiting": {
        "title": "Average Waiting Time: Normal Priority vs. StarveGuard",
        "ylabel": "Average Waiting Time (clock ticks)",
        "normal_key": "Normal Avg Waiting",
        "sg_key": "StarveGuard Avg Waiting",
        "fmt": "%.2f",
        "ylim": None,
        "filename": "average_waiting_comparison.png",
        "win_title": "Waiting Time Comparison",
    },
    "response": {
        "title": "Average Response Time: Normal Priority vs. StarveGuard",
        "ylabel": "Average Response Time (clock ticks)",
        "normal_key": "Normal Avg Response",
        "sg_key": "StarveGuard Avg Response",
        "fmt": "%.2f",
        "ylim": None,
        "filename": "average_response_comparison.png",
        "win_title": "Response Time Comparison",
    },
    "fairness": {
        "title": "Jain's Fairness Index: Normal Priority vs. StarveGuard",
        "ylabel": "Jain's Fairness Index (Execution Efficiency: burst / turnaround)",
        "normal_key": "Normal Fairness",
        "sg_key": "StarveGuard Fairness",
        "fmt": "%.3f",
        "ylim": (0.0, 1.18),
        "filename": "fairness_comparison.png",
        "win_title": "Fairness Comparison",
    },
}


def load_benchmark_data(csv_path: Optional[str] = None) -> Tuple[List[str], Dict[str, List[float]]]:
    """
    Loads benchmark comparison metrics from the validated workload_results.csv file.
    Returns clean multi-line display labels and parsed numeric columns.
    """
    if csv_path is None:
        csv_path = os.path.join(os.path.dirname(__file__), "workload_results.csv")

    display_labels = []
    data: Dict[str, List[float]] = {
        "Normal Avg Waiting": [],
        "StarveGuard Avg Waiting": [],
        "Normal Avg Response": [],
        "StarveGuard Avg Response": [],
        "Normal Fairness": [],
        "StarveGuard Fairness": [],
    }

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_name = row["Workload"].strip()
            # Split subtitle to second line for compact, collision-free x-axis rendering
            if "(" in raw_name and ")" in raw_name:
                base, paren = raw_name.split("(", 1)
                display_label = f"{base.strip()}\n({paren.strip()}"
            else:
                display_label = raw_name

            display_labels.append(display_label)
            for k in data:
                data[k].append(float(row[k]))

    return display_labels, data


def build_figure(chart_type: str, csv_path: Optional[str] = None, figsize: Tuple[float, float] = (9.5, 5.5)) -> Figure:
    """
    Constructs a responsive, professionally styled Matplotlib figure for a benchmark metric.
    Used both for PNG file generation and Tkinter FigureCanvasTkAgg embedding.
    """
    if chart_type not in CHART_CONFIGS:
        raise ValueError(f"Unknown chart_type '{chart_type}'. Choose from: {list(CHART_CONFIGS.keys())}")

    cfg = CHART_CONFIGS[chart_type]
    labels, data = load_benchmark_data(csv_path)

    normal_vals = data[cfg["normal_key"]]
    sg_vals = data[cfg["sg_key"]]

    fig = Figure(figsize=figsize, dpi=100, constrained_layout=True)
    ax = fig.add_subplot(111)

    x = range(len(labels))
    bar_width = 0.35

    # Professional muted palette: Normal = Royal Blue (#1D4ED8), StarveGuard = Emerald (#059669)
    rects_normal = ax.bar(
        [i - bar_width / 2 for i in x],
        normal_vals,
        bar_width,
        label="Normal Priority",
        color="#1D4ED8",
        zorder=3
    )
    rects_sg = ax.bar(
        [i + bar_width / 2 for i in x],
        sg_vals,
        bar_width,
        label="StarveGuard",
        color="#059669",
        zorder=3
    )

    # Bar value labels positioned neatly above each bar
    ax.bar_label(rects_normal, fmt=cfg["fmt"], padding=3, fontsize=8, color="#0F172A")
    ax.bar_label(rects_sg, fmt=cfg["fmt"], padding=3, fontsize=8, color="#0F172A")

    # Set appropriate headroom to ensure bar annotations never clip at the top
    if cfg["ylim"] is not None:
        ax.set_ylim(cfg["ylim"])
        ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    else:
        max_val = max(max(normal_vals), max(sg_vals))
        ax.set_ylim(0, max_val * 1.16 if max_val > 0 else 1.0)

    # X-axis configuration
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=8.5, color="#0F172A")

    # Labels and titles
    ax.set_ylabel(cfg["ylabel"], fontsize=9.5, fontweight="bold", color="#0F172A")
    ax.set_title(cfg["title"], fontsize=11, fontweight="bold", pad=12, color="#0F172A")

    # Clean axes styling
    ax.grid(axis="y", linestyle="--", alpha=0.5, color="#CBD5E1", zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#94A3B8")
    ax.spines["bottom"].set_color("#94A3B8")

    # Legend outside the bar clutter with clean border
    ax.legend(
        framealpha=0.95,
        edgecolor="#CBD5E1",
        facecolor="#FFFFFF",
        fontsize=9,
        loc="upper right" if chart_type != "fairness" else "upper left"
    )

    return fig


def generate_all_pngs():
    """
    Generates and saves standalone PNG benchmark charts to the results/ directory.
    """
    results_dir = os.path.dirname(__file__)

    for key, cfg in CHART_CONFIGS.items():
        fig = build_figure(key, figsize=(10.5, 6.0))
        out_path = os.path.join(results_dir, cfg["filename"])
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        print(f"Generated: {out_path}")


if __name__ == "__main__":
    generate_all_pngs()
