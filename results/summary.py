import csv
import os

filepath = os.path.join(os.path.dirname(__file__), "workload_results.csv")

with open(filepath, "r") as file:
    reader = csv.DictReader(file)

    print("\nSTARVEGUARD EXPERIMENTAL BENCHMARK SUMMARY")
    print("=" * 145)

    print(
        f"{'Workload Scenario':<36}"
        f"{'N':<5}"
        f"{'Normal Wait':<13}"
        f"{'SG Wait':<13}"
        f"{'Normal Resp':<13}"
        f"{'SG Resp':<13}"
        f"{'Normal Fair':<13}"
        f"{'SG Fair':<13}"
        f"{'Starved':<9}"
        f"{'Protected':<11}"
        f"{'Aged Events':<12}"
    )

    print("-" * 145)

    for row in reader:
        procs = row.get("Processes", "-")
        print(
            f"{row['Workload']:<36}"
            f"{procs:<5}"
            f"{float(row['Normal Avg Waiting']):<13.2f}"
            f"{float(row['StarveGuard Avg Waiting']):<13.2f}"
            f"{float(row['Normal Avg Response']):<13.2f}"
            f"{float(row['StarveGuard Avg Response']):<13.2f}"
            f"{float(row['Normal Fairness']):<13.3f}"
            f"{float(row['StarveGuard Fairness']):<13.3f}"
            f"{row['Starved Processes']:<9}"
            f"{row['Protected Processes']:<11}"
            f"{row['Aging Interventions']:<12}"
        )
    print()
