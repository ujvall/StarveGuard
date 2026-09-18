import csv
import matplotlib.pyplot as plt


workloads = []
normal_waiting = []
starveguard_waiting = []

with open("results/workload_results.csv", "r") as file:
    reader = csv.DictReader(file)

    for row in reader:
        workloads.append(row["Workload"])
        normal_waiting.append(float(row["Normal Avg Waiting"]))
        starveguard_waiting.append(float(row["StarveGuard Avg Waiting"]))


x = range(len(workloads))
width = 0.35

plt.figure(figsize=(10, 6))

plt.bar(
    [i - width / 2 for i in x],
    normal_waiting,
    width,
    label="Normal Priority"
)

plt.bar(
    [i + width / 2 for i in x],
    starveguard_waiting,
    width,
    label="StarveGuard"
)

plt.xticks(list(x), workloads)
plt.xlabel("Workload")
plt.ylabel("Average Waiting Time")
plt.title("Average Waiting Time Comparison")
plt.legend()
plt.tight_layout()

plt.savefig("results/average_waiting_comparison.png")
plt.show()

normal_response = []
starveguard_response = []

with open("results/workload_results.csv", "r") as file:
    reader = csv.DictReader(file)

    for row in reader:
        normal_response.append(
            float(row["Normal Avg Response"])
        )
        starveguard_response.append(
            float(row["StarveGuard Avg Response"])
        )


plt.figure(figsize=(10, 6))

plt.bar(
    [i - width / 2 for i in x],
    normal_response,
    width,
    label="Normal Priority"
)

plt.bar(
    [i + width / 2 for i in x],
    starveguard_response,
    width,
    label="StarveGuard"
)

plt.xticks(list(x), workloads)
plt.xlabel("Workload")
plt.ylabel("Average Response Time")
plt.title("Average Response Time Comparison")
plt.legend()
plt.tight_layout()

plt.savefig("results/average_response_comparison.png")
plt.show()

normal_fairness = []
starveguard_fairness = []

with open("results/workload_results.csv", "r") as file:
    reader = csv.DictReader(file)

    for row in reader:
        normal_fairness.append(
            float(row["Normal Fairness"])
        )
        starveguard_fairness.append(
            float(row["StarveGuard Fairness"])
        )


plt.figure(figsize=(10, 6))

plt.bar(
    [i - width / 2 for i in x],
    normal_fairness,
    width,
    label="Normal Priority"
)

plt.bar(
    [i + width / 2 for i in x],
    starveguard_fairness,
    width,
    label="StarveGuard"
)

plt.xticks(list(x), workloads)
plt.xlabel("Workload")
plt.ylabel("Fairness Index")
plt.title("Fairness Comparison")
plt.legend()
plt.tight_layout()

plt.savefig("results/fairness_comparison.png")
plt.show()
