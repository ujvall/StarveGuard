import csv
import os
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless environments
import matplotlib.pyplot as plt

filepath = os.path.join(os.path.dirname(__file__), "workload_results.csv")
results_dir = os.path.dirname(__file__)

workloads = []
normal_waiting = []
starveguard_waiting = []
normal_response = []
starveguard_response = []
normal_fairness = []
starveguard_fairness = []

with open(filepath, "r") as file:
    reader = csv.DictReader(file)
    for row in reader:
        # Abbreviate label for clean chart presentation
        raw_name = row["Workload"]
        if "(" in raw_name:
            short_name = raw_name.split("(")[0].strip()
        else:
            short_name = raw_name
        workloads.append(short_name)
        normal_waiting.append(float(row["Normal Avg Waiting"]))
        starveguard_waiting.append(float(row["StarveGuard Avg Waiting"]))
        normal_response.append(float(row["Normal Avg Response"]))
        starveguard_response.append(float(row["StarveGuard Avg Response"]))
        normal_fairness.append(float(row["Normal Fairness"]))
        starveguard_fairness.append(float(row["StarveGuard Fairness"]))

x = range(len(workloads))
width = 0.35

# 1. Average Waiting Time Comparison
plt.figure(figsize=(11, 6))
plt.bar([i - width / 2 for i in x], normal_waiting, width, label="Normal Priority", color="#2563EB")
plt.bar([i + width / 2 for i in x], starveguard_waiting, width, label="StarveGuard", color="#059669")
plt.xticks(list(x), workloads, rotation=15, ha="right")
plt.xlabel("Workload")
plt.ylabel("Average Waiting Time (ticks)")
plt.title("Average Waiting Time: Normal Priority vs. StarveGuard")
plt.legend()
plt.tight_layout()
waiting_path = os.path.join(results_dir, "average_waiting_comparison.png")
plt.savefig(waiting_path, dpi=150)
plt.close()
print(f"Generated: {waiting_path}")

# 2. Average Response Time Comparison
plt.figure(figsize=(11, 6))
plt.bar([i - width / 2 for i in x], normal_response, width, label="Normal Priority", color="#2563EB")
plt.bar([i + width / 2 for i in x], starveguard_response, width, label="StarveGuard", color="#059669")
plt.xticks(list(x), workloads, rotation=15, ha="right")
plt.xlabel("Workload")
plt.ylabel("Average Response Time (ticks)")
plt.title("Average Response Time: Normal Priority vs. StarveGuard")
plt.legend()
plt.tight_layout()
response_path = os.path.join(results_dir, "average_response_comparison.png")
plt.savefig(response_path, dpi=150)
plt.close()
print(f"Generated: {response_path}")

# 3. Fairness Comparison
plt.figure(figsize=(11, 6))
plt.bar([i - width / 2 for i in x], normal_fairness, width, label="Normal Priority", color="#2563EB")
plt.bar([i + width / 2 for i in x], starveguard_fairness, width, label="StarveGuard", color="#059669")
plt.xticks(list(x), workloads, rotation=15, ha="right")
plt.xlabel("Workload")
plt.ylabel("Jain's Fairness Index (0.0 - 1.0)")
plt.title("Jain's Fairness Index: Normal Priority vs. StarveGuard")
plt.legend()
plt.tight_layout()
fairness_path = os.path.join(results_dir, "fairness_comparison.png")
plt.savefig(fairness_path, dpi=150)
plt.close()
print(f"Generated: {fairness_path}")
