def generate_gantt_chart(gantt_data):
    if not gantt_data:
        return

    segments = []
    start = gantt_data[0][1]
    current_pid = gantt_data[0][0]

    for i in range(1, len(gantt_data)):
        pid, time = gantt_data[i]

        if pid != current_pid:
            segments.append((current_pid, start, time))
            current_pid = pid
            start = time

    end = gantt_data[-1][1] + 1
    segments.append((current_pid, start, end))

    print("\nGantt Chart:")
    print(" ", end="")

    for pid, start, end in segments:
        print(f"| {pid} ", end="")

    print("|")

    print(segments[0][1], end="")

    for _, start, end in segments:
        print(f"    {end}", end="")

    print()
