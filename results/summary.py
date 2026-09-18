import csv


with open("results/workload_results.csv", "r") as file:
    reader = csv.DictReader(file)

    print("\nSTARVEGUARD EXPERIMENT SUMMARY")
    print("=" * 125)

    print(
        f"{'Workload':<12}"
        f"{'Normal Wait':<15}"
        f"{'StarveGuard Wait':<18}"
        f"{'Normal Response':<18}"
        f"{'StarveGuard Response':<22}"
        f"{'Normal Fairness':<18}"
        f"{'StarveGuard Fairness':<22}"
        f"{'Starved':<12}"
        f"{'Protected':<12}"
    )

    print("-" * 133)

    for row in reader:
        print(
            f"{row['Workload']:<12}"
            f"{float(row['Normal Avg Waiting']):<15.2f}"
            f"{float(row['StarveGuard Avg Waiting']):<18.2f}"
            f"{float(row['Normal Avg Response']):<18.2f}"
            f"{float(row['StarveGuard Avg Response']):<22.2f}"
            f"{float(row['Normal Fairness']):<18.3f}"
            f"{float(row['StarveGuard Fairness']):<20.3f}"
            f"{row['Starved Processes']:<10}"
            f"{row['Protected Processes']:<10}"
        )
