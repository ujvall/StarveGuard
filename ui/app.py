import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from comparison.comparator import SchedulerComparator


root = tk.Tk()
root.title("StarveGuard - Adaptive Process Scheduling & Starvation Prevention")
root.geometry("1260x880")
root.minsize(1050, 720)
root.configure(bg="#F0F0F0")

style = ttk.Style()
try:
    style.theme_use("default")
except Exception:
    pass

style.configure(
    "Treeview.Heading",
    font=("Segoe UI", 9, "bold"),
    relief="raised",
    background="#D9D9D9",
    foreground="#000000",
    borderwidth=1
)
style.map(
    "Treeview.Heading",
    relief=[("active", "sunken"), ("pressed", "sunken")]
)
style.configure(
    "Treeview",
    font=("Segoe UI", 9),
    rowheight=22,
    background="#FFFFFF",
    fieldbackground="#FFFFFF",
    foreground="#000000",
    relief="sunken",
    borderwidth=1
)

header_frame = tk.Frame(root, bg="#0B192C")
header_frame.pack(side="top", fill="x")

title_label = tk.Label(
    header_frame,
    text="STARVEGUARD",
    font=("Segoe UI", 18, "bold"),
    fg="#FFFFFF",
    bg="#0B192C"
)
title_label.pack(pady=(14, 2))

subtitle_label = tk.Label(
    header_frame,
    text="Adaptive Process Starvation Detection and Prevention System",
    font=("Segoe UI", 9),
    fg="#94A3B8",
    bg="#0B192C"
)
subtitle_label.pack(pady=(0, 14))

status_frame = tk.Frame(root, bg="#F0F0F0", bd=1, relief="sunken")
status_frame.pack(side="bottom", fill="x")

status_label = tk.Label(
    status_frame,
    text="Ready",
    anchor="w",
    font=("Segoe UI", 9),
    bg="#F0F0F0",
    fg="#475569",
    padx=14,
    pady=5
)
status_label.pack(fill="x")


def set_status(message, color="#475569"):
    status_label.config(text=message, fg=color)
    root.update_idletasks()


main_canvas = tk.Canvas(root, bg="#F0F0F0", highlightthickness=0)
scrollbar = ttk.Scrollbar(root, orient="vertical", command=main_canvas.yview)
scrollable_frame = tk.Frame(main_canvas, bg="#F0F0F0")

scrollable_frame.bind(
    "<Configure>",
    lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
)

canvas_window = main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")


def on_canvas_configure(event):
    main_canvas.itemconfig(canvas_window, width=event.width)


main_canvas.bind("<Configure>", on_canvas_configure)
main_canvas.configure(yscrollcommand=scrollbar.set)

scrollbar.pack(side="right", fill="y")
main_canvas.pack(side="left", fill="both", expand=True)


def on_mousewheel(event):
    main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


main_canvas.bind_all("<MouseWheel>", on_mousewheel)

input_card = tk.LabelFrame(
    scrollable_frame,
    text="  PROCESS INPUTS & EXECUTION CONTROLS  ",
    font=("Segoe UI", 9, "bold"),
    fg="#000000",
    bg="#F0F0F0",
    padx=20,
    pady=12,
    relief="groove",
    bd=2
)
input_card.pack(fill="x", padx=20, pady=(12, 6))

headers = ["Process", "Arrival Time", "Burst Time", "Priority"]
for col_idx, h in enumerate(headers):
    tk.Label(
        input_card,
        text=h,
        font=("Segoe UI", 9, "bold"),
        fg="#000000",
        bg="#F0F0F0"
    ).grid(row=0, column=col_idx, padx=15, pady=(0, 6))

entries = []
input_widgets = []

for i in range(4):
    tk.Label(
        input_card,
        text=f"P{i + 1}",
        font=("Segoe UI", 9, "bold"),
        fg="#1D4ED8",
        bg="#F0F0F0"
    ).grid(row=i + 1, column=0, padx=15, pady=3)

    arrival = tk.Entry(input_card, width=14, font=("Segoe UI", 9), justify="center", bg="#FFFFFF", fg="#000000", relief="sunken", bd=2)
    arrival.grid(row=i + 1, column=1, padx=15, pady=3)

    burst = tk.Entry(input_card, width=14, font=("Segoe UI", 9), justify="center", bg="#FFFFFF", fg="#000000", relief="sunken", bd=2)
    burst.grid(row=i + 1, column=2, padx=15, pady=3)

    priority = tk.Entry(input_card, width=14, font=("Segoe UI", 9), justify="center", bg="#FFFFFF", fg="#000000", relief="sunken", bd=2)
    priority.grid(row=i + 1, column=3, padx=15, pady=3)

    entries.append((arrival, burst, priority))
    input_widgets.extend([arrival, burst, priority])

btn_container = tk.Frame(input_card, bg="#F0F0F0")
btn_container.grid(row=5, column=0, columnspan=4, sticky="w", pady=(12, 4))

run_button = tk.Button(
    btn_container,
    text="▶  Run Simulation",
    font=("Segoe UI", 9, "bold"),
    bg="#1D4ED8",
    fg="#FFFFFF",
    activebackground="#1E40AF",
    activeforeground="#FFFFFF",
    relief="raised",
    bd=2,
    cursor="hand2",
    padx=14,
    pady=5
)
run_button.pack(side="left", padx=(0, 8))

demo_button = tk.Button(
    btn_container,
    text="⚡ Load Demo Workload",
    font=("Segoe UI", 9, "bold"),
    bg="#0D9488",
    fg="#FFFFFF",
    activebackground="#0F766E",
    activeforeground="#FFFFFF",
    relief="raised",
    bd=2,
    cursor="hand2",
    padx=14,
    pady=5
)
demo_button.pack(side="left", padx=8)

reset_button = tk.Button(
    btn_container,
    text="↺  Clear / Reset",
    font=("Segoe UI", 9),
    bg="#F0F0F0",
    fg="#000000",
    activebackground="#E0E0E0",
    activeforeground="#000000",
    relief="raised",
    bd=2,
    cursor="hand2",
    padx=14,
    pady=5
)
reset_button.pack(side="left", padx=8)

dashboard_frame = tk.Frame(scrollable_frame, bg="#F0F0F0")
dashboard_frame.pack(fill="x", padx=20, pady=6)

dashboard_frame.columnconfigure(0, weight=1)
dashboard_frame.columnconfigure(1, weight=1)
dashboard_frame.columnconfigure(2, weight=1)

normal_card = tk.LabelFrame(
    dashboard_frame,
    text="  NORMAL PRIORITY METRICS  ",
    font=("Segoe UI", 9, "bold"),
    fg="#000000",
    bg="#F0F0F0",
    padx=16,
    pady=10,
    relief="groove",
    bd=2
)
normal_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

normal_labels = {}
normal_metric_keys = [
    ("Average Waiting:", "average_waiting"),
    ("Average Turnaround:", "average_turnaround"),
    ("Average Response:", "average_response"),
    ("Maximum Waiting:", "maximum_waiting"),
    ("Fairness:", "fairness"),
]

for idx, (title_text, key) in enumerate(normal_metric_keys):
    tk.Label(
        normal_card,
        text=title_text,
        font=("Segoe UI", 9, "bold"),
        fg="#000000",
        bg="#F0F0F0",
        anchor="w"
    ).grid(row=idx, column=0, sticky="w", pady=4)

    val_lbl = tk.Label(
        normal_card,
        text="-",
        font=("Segoe UI", 9),
        fg="#000000",
        bg="#F0F0F0",
        anchor="e"
    )
    val_lbl.grid(row=idx, column=1, sticky="e", pady=4, padx=(16, 0))
    normal_labels[key] = val_lbl

starveguard_card = tk.LabelFrame(
    dashboard_frame,
    text="  STARVEGUARD ADAPTIVE METRICS  ",
    font=("Segoe UI", 9, "bold"),
    fg="#000000",
    bg="#F0F0F0",
    padx=16,
    pady=10,
    relief="groove",
    bd=2
)
starveguard_card.grid(row=0, column=1, sticky="nsew", padx=6)

starveguard_labels = {}
starveguard_metric_keys = [
    ("Average Waiting:", "average_waiting"),
    ("Average Turnaround:", "average_turnaround"),
    ("Average Response:", "average_response"),
    ("Maximum Waiting:", "maximum_waiting"),
    ("Fairness:", "fairness"),
    ("Starved Processes:", "starved_processes"),
    ("Protected Processes:", "protected_processes"),
    ("Aging Interventions:", "aging_interventions"),
]

for idx, (title_text, key) in enumerate(starveguard_metric_keys):
    tk.Label(
        starveguard_card,
        text=title_text,
        font=("Segoe UI", 9, "bold"),
        fg="#000000",
        bg="#F0F0F0",
        anchor="w"
    ).grid(row=idx, column=0, sticky="w", pady=4)

    val_lbl = tk.Label(
        starveguard_card,
        text="-",
        font=("Segoe UI", 9),
        fg="#000000",
        bg="#F0F0F0",
        anchor="e"
    )
    val_lbl.grid(row=idx, column=1, sticky="e", pady=4, padx=(16, 0))
    starveguard_labels[key] = val_lbl

comparison_card = tk.LabelFrame(
    dashboard_frame,
    text="  COMPARISON (STARVEGUARD - NORMAL)  ",
    font=("Segoe UI", 9, "bold"),
    fg="#000000",
    bg="#F0F0F0",
    padx=16,
    pady=10,
    relief="groove",
    bd=2
)
comparison_card.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

comparison_labels = {}
comparison_metric_keys = [
    ("Average Waiting Change:", "waiting_change"),
    ("Average Turnaround Change:", "turnaround_change"),
    ("Average Response Change:", "response_change"),
    ("Maximum Waiting Change:", "max_waiting_change"),
    ("Fairness Change:", "fairness_change"),
]

for idx, (title_text, key) in enumerate(comparison_metric_keys):
    tk.Label(
        comparison_card,
        text=title_text,
        font=("Segoe UI", 9, "bold"),
        fg="#000000",
        bg="#F0F0F0",
        anchor="w"
    ).grid(row=idx, column=0, sticky="w", pady=4)

    val_lbl = tk.Label(
        comparison_card,
        text="-",
        font=("Segoe UI", 9),
        fg="#000000",
        bg="#F0F0F0",
        anchor="e"
    )
    val_lbl.grid(row=idx, column=1, sticky="e", pady=4, padx=(16, 0))
    comparison_labels[key] = val_lbl

definitions_card = tk.LabelFrame(
    scrollable_frame,
    text="  METRIC DEFINITIONS  ",
    font=("Segoe UI", 9, "bold"),
    fg="#000000",
    bg="#F0F0F0",
    padx=16,
    pady=8,
    relief="groove",
    bd=2
)
definitions_card.pack(fill="x", padx=20, pady=6)

definitions_card.columnconfigure(0, weight=1)
definitions_card.columnconfigure(1, weight=1)

metric_definitions = [
    (
        "Starvation Detected",
        "A process whose starvation score reaches or exceeds the configured starvation threshold (20).",
        0, 0
    ),
    (
        "Protected Process",
        "A process whose priority was improved by the aging mechanism at least once.",
        0, 1
    ),
    (
        "Aging Intervention",
        "One actual priority adjustment performed by the aging mechanism.",
        1, 0
    ),
    (
        "Starvation Score",
        "Waiting Time + (Bypass Count × Bypass Weight), where the current bypass weight is 2.",
        1, 1
    ),
    (
        "Priority",
        "Lower numerical value means higher priority.",
        2, 0
    ),
]

for title, desc, r, c in metric_definitions:
    item_frame = tk.Frame(definitions_card, bg="#F0F0F0")
    item_frame.grid(row=r, column=c, sticky="w", padx=10, pady=2)

    tk.Label(
        item_frame,
        text=f"• {title}:",
        font=("Segoe UI", 8, "bold"),
        fg="#1D4ED8",
        bg="#F0F0F0"
    ).pack(side="left")

    tk.Label(
        item_frame,
        text=f" {desc}",
        font=("Segoe UI", 8),
        fg="#000000",
        bg="#F0F0F0"
    ).pack(side="left")

timeline_card = tk.LabelFrame(
    scrollable_frame,
    text="  SCHEDULING TIMELINE (GANTT CHARTS)  ",
    font=("Segoe UI", 9, "bold"),
    fg="#000000",
    bg="#F0F0F0",
    padx=18,
    pady=10,
    relief="groove",
    bd=2
)
timeline_card.pack(fill="x", padx=20, pady=6)

tk.Label(
    timeline_card,
    text="Normal Priority Timeline:",
    font=("Segoe UI", 9, "bold"),
    fg="#000000",
    bg="#F0F0F0"
).pack(anchor="w", pady=(0, 2))

normal_canvas = tk.Canvas(timeline_card, height=54, bg="#FFFFFF", relief="sunken", bd=2, highlightthickness=1, highlightbackground="#B0B0B0")
normal_canvas.pack(fill="x", pady=(0, 8))

tk.Label(
    timeline_card,
    text="StarveGuard Adaptive Timeline:",
    font=("Segoe UI", 9, "bold"),
    fg="#1D4ED8",
    bg="#F0F0F0"
).pack(anchor="w", pady=(2, 2))

starveguard_canvas = tk.Canvas(timeline_card, height=54, bg="#FFFFFF", relief="sunken", bd=2, highlightthickness=1, highlightbackground="#B0B0B0")
starveguard_canvas.pack(fill="x", pady=(0, 4))

legend_frame = tk.Frame(timeline_card, bg="#F0F0F0")
legend_frame.pack(anchor="w", pady=(6, 2))

tk.Label(
    legend_frame,
    text="Legend:",
    font=("Segoe UI", 9, "bold"),
    fg="#000000",
    bg="#F0F0F0"
).pack(side="left", padx=(0, 10))

legend_items = [
    ("P1", "#1D4ED8"),
    ("P2", "#059669"),
    ("P3", "#D97706"),
    ("P4", "#7C3AED"),
    ("IDLE", "#94A3B8")
]

for pid, color in legend_items:
    item_box = tk.Frame(legend_frame, bg="#F0F0F0")
    item_box.pack(side="left", padx=8)

    swatch = tk.Canvas(item_box, width=16, height=12, bg="#F0F0F0", highlightthickness=0)
    swatch.pack(side="left", padx=(0, 4))
    swatch.create_rectangle(0, 0, 16, 12, fill=color, outline="#334155")

    tk.Label(
        item_box,
        text=pid,
        font=("Segoe UI", 9),
        fg="#000000",
        bg="#F0F0F0"
    ).pack(side="left")

tables_container = tk.Frame(scrollable_frame, bg="#F0F0F0")
tables_container.pack(fill="x", padx=20, pady=6)

tables_container.columnconfigure(0, weight=3)
tables_container.columnconfigure(1, weight=2)

details_card = tk.LabelFrame(
    tables_container,
    text="  STARVEGUARD PROCESS-LEVEL METRICS  ",
    font=("Segoe UI", 9, "bold"),
    fg="#000000",
    bg="#F0F0F0",
    padx=12,
    pady=8,
    relief="groove",
    bd=2
)
details_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

process_columns = [
    ("pid", "PID", 45),
    ("arrival", "Arrival", 55),
    ("burst", "Burst", 50),
    ("orig_prio", "Orig Prio", 68),
    ("final_prio", "Final Prio", 68),
    ("completion", "Completion", 75),
    ("waiting", "Waiting", 60),
    ("turnaround", "Turnaround", 75),
    ("response", "Response", 65),
    ("bypass", "Bypass", 55),
    ("aging", "Aging Adj", 65),
    ("starved", "Starved?", 60)
]

process_tree = ttk.Treeview(
    details_card,
    columns=[c[0] for c in process_columns],
    show="headings",
    height=4
)

for col_id, col_text, col_width in process_columns:
    process_tree.heading(col_id, text=col_text)
    process_tree.column(col_id, width=col_width, anchor="center")

process_tree.pack(fill="both", expand=True)

events_card = tk.LabelFrame(
    tables_container,
    text="  STARVEGUARD AGING INTERVENTION EVENTS  ",
    font=("Segoe UI", 9, "bold"),
    fg="#000000",
    bg="#F0F0F0",
    padx=12,
    pady=8,
    relief="groove",
    bd=2
)
events_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

event_columns = [
    ("time", "Time", 60),
    ("pid", "Process", 75),
    ("old_prio", "Old Priority", 85),
    ("new_prio", "New Priority", 85),
    ("score", "Starvation Score", 115)
]

events_tree_frame = tk.Frame(events_card, bg="#F0F0F0")
events_tree_frame.pack(fill="both", expand=True)

aging_scroll = ttk.Scrollbar(events_tree_frame, orient="vertical")
aging_tree = ttk.Treeview(
    events_tree_frame,
    columns=[c[0] for c in event_columns],
    show="headings",
    height=4,
    yscrollcommand=aging_scroll.set
)
aging_scroll.config(command=aging_tree.yview)

for col_id, col_text, col_width in event_columns:
    aging_tree.heading(col_id, text=col_text)
    aging_tree.column(col_id, width=col_width, anchor="center")

aging_tree.pack(side="left", fill="both", expand=True)
aging_scroll.pack(side="right", fill="y")

analysis_card = tk.LabelFrame(
    scrollable_frame,
    text="  EXPERIMENTAL ANALYSIS (PRE-GENERATED BENCHMARK GRAPHS)  ",
    font=("Segoe UI", 9, "bold"),
    fg="#000000",
    bg="#F0F0F0",
    padx=18,
    pady=12,
    relief="groove",
    bd=2
)
analysis_card.pack(fill="x", padx=20, pady=(6, 20))

tk.Label(
    analysis_card,
    text="View comparative benchmark charts generated across diverse OS workload suites:",
    font=("Segoe UI", 9),
    fg="#000000",
    bg="#F0F0F0"
).pack(anchor="w", pady=(0, 8))

analysis_btn_frame = tk.Frame(analysis_card, bg="#F0F0F0")
analysis_btn_frame.pack(anchor="w")

btn_graph_waiting = tk.Button(
    analysis_btn_frame,
    text="📈 Show Waiting Time Graph",
    font=("Segoe UI", 9),
    bg="#F0F0F0",
    fg="#000000",
    activebackground="#E0E0E0",
    relief="raised",
    bd=2,
    cursor="hand2",
    padx=12,
    pady=5,
    command=lambda: show_graph("waiting")
)
btn_graph_waiting.pack(side="left", padx=(0, 10))

btn_graph_response = tk.Button(
    analysis_btn_frame,
    text="📊 Show Response Time Graph",
    font=("Segoe UI", 9),
    bg="#F0F0F0",
    fg="#000000",
    activebackground="#E0E0E0",
    relief="raised",
    bd=2,
    cursor="hand2",
    padx=12,
    pady=5,
    command=lambda: show_graph("response")
)
btn_graph_response.pack(side="left", padx=10)

btn_graph_fairness = tk.Button(
    analysis_btn_frame,
    text="⚖️ Show Fairness Graph",
    font=("Segoe UI", 9),
    bg="#F0F0F0",
    fg="#000000",
    activebackground="#E0E0E0",
    relief="raised",
    bd=2,
    cursor="hand2",
    padx=12,
    pady=5,
    command=lambda: show_graph("fairness")
)
btn_graph_fairness.pack(side="left", padx=10)


def extract_segments(gantt_data):
    if not gantt_data:
        return []

    segments = []
    first_time = gantt_data[0][1]
    if first_time > 0:
        segments.append(("IDLE", 0, first_time))

    start = gantt_data[0][1]
    current_pid = gantt_data[0][0]
    expected_next_time = start + 1

    for i in range(1, len(gantt_data)):
        pid, time = gantt_data[i]
        if time > expected_next_time:
            segments.append((current_pid, start, expected_next_time))
            segments.append(("IDLE", expected_next_time, time))
            current_pid = pid
            start = time
            expected_next_time = time + 1
        elif pid != current_pid:
            segments.append((current_pid, start, time))
            current_pid = pid
            start = time
            expected_next_time = time + 1
        else:
            expected_next_time = time + 1

    segments.append((current_pid, start, expected_next_time))
    return segments


def draw_gantt_chart(canvas, gantt_data, title):
    canvas.delete("all")
    canvas.update_idletasks()

    width = canvas.winfo_width()
    if width < 300:
        width = 1140

    segments = extract_segments(gantt_data)
    if not segments:
        canvas.create_text(
            width / 2,
            27,
            text="No timeline data",
            font=("Segoe UI", 9, "italic"),
            fill="#94A3B8"
        )
        return

    total_time = segments[-1][2]
    if total_time <= 0:
        total_time = 1

    pad_left = 28
    pad_right = 28
    usable_width = width - pad_left - pad_right
    y1 = 8
    y2 = 34

    color_map = {
        "P1": "#1D4ED8",
        "P2": "#059669",
        "P3": "#D97706",
        "P4": "#7C3AED",
        "IDLE": "#94A3B8"
    }

    drawn_time_points = set()

    for pid, start, end in segments:
        x1 = pad_left + (start / total_time) * usable_width
        x2 = pad_left + (end / total_time) * usable_width

        color = color_map.get(pid, "#6B7280")

        canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=color,
            outline="#334155",
            width=1
        )

        if x2 - x1 >= 18:
            text_color = "#000000" if pid == "IDLE" else "#FFFFFF"
            canvas.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                text=pid,
                font=("Segoe UI", 9, "bold"),
                fill=text_color
            )

        if start not in drawn_time_points:
            canvas.create_line(x1, y2, x1, y2 + 5, fill="#000000")
            canvas.create_text(x1, y2 + 13, text=str(start), font=("Segoe UI", 8), fill="#000000")
            drawn_time_points.add(start)

        if end not in drawn_time_points:
            canvas.create_line(x2, y2, x2, y2 + 5, fill="#000000")
            canvas.create_text(x2, y2 + 13, text=str(end), font=("Segoe UI", 8), fill="#000000")
            drawn_time_points.add(end)


def display_results(normal, starveguard):
    normal_labels["average_waiting"].config(text=f"{normal['average_waiting']:.2f}")
    normal_labels["average_turnaround"].config(text=f"{normal['average_turnaround']:.2f}")
    normal_labels["average_response"].config(text=f"{normal['average_response']:.2f}")
    normal_labels["maximum_waiting"].config(text=str(normal['maximum_waiting']))
    normal_labels["fairness"].config(text=f"{normal['fairness']:.3f}")

    starveguard_labels["average_waiting"].config(text=f"{starveguard['average_waiting']:.2f}")
    starveguard_labels["average_turnaround"].config(text=f"{starveguard['average_turnaround']:.2f}")
    starveguard_labels["average_response"].config(text=f"{starveguard['average_response']:.2f}")
    starveguard_labels["maximum_waiting"].config(text=str(starveguard['maximum_waiting']))
    starveguard_labels["fairness"].config(text=f"{starveguard['fairness']:.3f}")
    starveguard_labels["starved_processes"].config(text=str(starveguard['starved_processes']))
    starveguard_labels["protected_processes"].config(text=str(starveguard['protected_processes']))
    starveguard_labels["aging_interventions"].config(text=str(starveguard['aging_interventions']))

    w_change = starveguard["average_waiting"] - normal["average_waiting"]
    t_change = starveguard["average_turnaround"] - normal["average_turnaround"]
    r_change = starveguard["average_response"] - normal["average_response"]
    m_change = starveguard["maximum_waiting"] - normal["maximum_waiting"]
    f_change = starveguard["fairness"] - normal["fairness"]

    w_txt = "0" if abs(w_change) < 1e-6 else f"{w_change:+.2f}"
    t_txt = "0" if abs(t_change) < 1e-6 else f"{t_change:+.2f}"
    r_txt = "0" if abs(r_change) < 1e-6 else f"{r_change:+.2f}"
    m_txt = "0" if abs(m_change) < 1e-6 else f"{m_change:+}"
    f_txt = "0" if abs(f_change) < 1e-6 else f"{f_change:+.3f}"

    comparison_labels["waiting_change"].config(text=w_txt, fg="#000000")
    comparison_labels["turnaround_change"].config(text=t_txt, fg="#000000")

    if r_change < -1e-6:
        comparison_labels["response_change"].config(text=r_txt, fg="#16A34A")
    elif r_change > 1e-6:
        comparison_labels["response_change"].config(text=r_txt, fg="#DC2626")
    else:
        comparison_labels["response_change"].config(text=r_txt, fg="#000000")

    comparison_labels["max_waiting_change"].config(text=m_txt, fg="#000000")

    if f_change > 1e-6:
        comparison_labels["fairness_change"].config(text=f_txt, fg="#16A34A")
    elif f_change < -1e-6:
        comparison_labels["fairness_change"].config(text=f_txt, fg="#DC2626")
    else:
        comparison_labels["fairness_change"].config(text=f_txt, fg="#000000")


def display_process_details(processes):
    for item in process_tree.get_children():
        process_tree.delete(item)

    for p in processes:
        process_tree.insert(
            "",
            "end",
            values=(
                p.pid,
                p.arrival_time,
                p.burst_time,
                p.original_priority,
                p.current_priority,
                p.completion_time,
                p.waiting_time,
                p.turnaround_time,
                p.response_time,
                p.bypass_count,
                p.aging_adjustments,
                "Yes" if p.starvation_detected else "No"
            )
        )


def display_aging_events(events):
    for item in aging_tree.get_children():
        aging_tree.delete(item)

    if not events:
        aging_tree.insert(
            "",
            "end",
            values=("-", "No aging interventions required.", "-", "-", "-")
        )
    else:
        for event in events:
            aging_tree.insert("", "end", values=event)


def show_graph(graph_name):
    graph_map = {
        "waiting": ("average_waiting_comparison.png", "Average Waiting Time Comparison"),
        "response": ("average_response_comparison.png", "Average Response Time Comparison"),
        "fairness": ("fairness_comparison.png", "Fairness Comparison"),
    }

    if graph_name not in graph_map:
        return

    filename, win_title = graph_map[graph_name]
    filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results", filename))

    if not os.path.exists(filepath):
        messagebox.showwarning(
            "Graph File Not Found",
            f"Could not locate image file:\n{filepath}\n\nPlease run results/generate_graphs.py first."
        )
        return

    top = tk.Toplevel(root)
    top.title(win_title)
    top.geometry("1040x670")
    top.configure(bg="#F0F0F0")

    photo = tk.PhotoImage(file=filepath)
    lbl = tk.Label(top, image=photo, bg="#F0F0F0")
    lbl.image = photo
    lbl.pack(padx=15, pady=12)

    close_btn = tk.Button(
        top,
        text="Close",
        font=("Segoe UI", 9, "bold"),
        bg="#F0F0F0",
        fg="#000000",
        relief="raised",
        bd=2,
        cursor="hand2",
        padx=14,
        pady=4,
        command=top.destroy
    )
    close_btn.pack(pady=(0, 10))


def load_demo():
    clear_results()

    demo_data = [
        (0, 15, 6),
        (0, 5, 3),
        (5, 5, 3),
        (10, 5, 3)
    ]

    for (arrival_val, burst_val, priority_val), (arr_ent, bst_ent, prio_ent) in zip(demo_data, entries):
        arr_ent.insert(0, str(arrival_val))
        bst_ent.insert(0, str(burst_val))
        prio_ent.insert(0, str(priority_val))

    set_status("Demo workload loaded. Press 'Run Simulation' to execute.", "#0D9488")
    run_button.focus_set()


def clear_results():
    for arr, bst, prio in entries:
        arr.delete(0, tk.END)
        bst.delete(0, tk.END)
        prio.delete(0, tk.END)

    for key in normal_labels:
        normal_labels[key].config(text="-")

    for key in starveguard_labels:
        starveguard_labels[key].config(text="-")

    for key in comparison_labels:
        comparison_labels[key].config(text="-", fg="#000000")

    normal_canvas.delete("all")
    starveguard_canvas.delete("all")

    for item in process_tree.get_children():
        process_tree.delete(item)

    for item in aging_tree.get_children():
        aging_tree.delete(item)

    set_status("Ready", "#475569")
    input_widgets[0].focus_set()


def run_simulation():
    process_data = []

    for i, (arrival_entry, burst_entry, priority_entry) in enumerate(entries):
        arr_val = arrival_entry.get().strip()
        burst_val = burst_entry.get().strip()
        prio_val = priority_entry.get().strip()

        if not arr_val or not burst_val or not prio_val:
            set_status(f"Validation Error: Process P{i + 1} has blank fields.", "#DC2626")
            messagebox.showerror(
                "Input Error",
                f"Please fill all fields for process P{i + 1}."
            )
            return

        try:
            arrival = int(arr_val)
            burst = int(burst_val)
            priority = int(prio_val)
        except ValueError:
            set_status(f"Validation Error: Process P{i + 1} fields must be integers.", "#DC2626")
            messagebox.showerror(
                "Input Error",
                f"Process P{i + 1} inputs must be integers."
            )
            return

        if arrival < 0:
            set_status(f"Validation Error: P{i + 1} Arrival Time must be non-negative.", "#DC2626")
            messagebox.showerror(
                "Input Error",
                f"Arrival Time for P{i + 1} must be a non-negative integer (>= 0)."
            )
            return

        if burst <= 0:
            set_status(f"Validation Error: P{i + 1} Burst Time must be positive.", "#DC2626")
            messagebox.showerror(
                "Input Error",
                f"Burst Time for P{i + 1} must be a positive integer (> 0)."
            )
            return

        if priority <= 0:
            set_status(f"Validation Error: P{i + 1} Priority must be positive.", "#DC2626")
            messagebox.showerror(
                "Input Error",
                f"Priority for P{i + 1} must be a positive integer (> 0)."
            )
            return

        process_data.append((f"P{i + 1}", arrival, burst, priority))

    try:
        comparator = SchedulerComparator(process_data)
        normal = comparator.run_normal()
        starveguard = comparator.run_starveguard()
    except Exception as exc:
        set_status(f"Simulation error: {exc}", "#DC2626")
        messagebox.showerror(
            "Simulation Error",
            f"An error occurred during simulation:\n{exc}"
        )
        return

    display_results(normal, starveguard)
    draw_gantt_chart(normal_canvas, normal["scheduler"].gantt_chart, "Normal Priority")
    draw_gantt_chart(starveguard_canvas, starveguard["scheduler"].gantt_chart, "StarveGuard")
    display_process_details(starveguard["processes"])
    display_aging_events(starveguard["scheduler"].aging_events)

    set_status("Simulation completed successfully. Visual dashboard updated.", "#059669")


run_button.config(command=run_simulation)
demo_button.config(command=load_demo)
reset_button.config(command=clear_results)


def make_focus_handler(target_widget):
    def handler(event):
        target_widget.focus_set()
        return "break"
    return handler


for i in range(len(input_widgets) - 1):
    input_widgets[i].bind("<Return>", make_focus_handler(input_widgets[i + 1]))

input_widgets[-1].bind("<Return>", make_focus_handler(run_button))
run_button.bind("<Return>", lambda event: run_simulation())

input_widgets[0].focus_set()

root.mainloop()