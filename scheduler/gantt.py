from typing import List, Tuple


def extract_gantt_segments(gantt_data: List[Tuple[str, int]]) -> List[Tuple[str, int, int]]:
    """
    Compresses a sequence of discrete (pid, timestamp) execution records
    into contiguous intervals of format (pid, start_time, end_time).

    Explicitly detects and preserves IDLE intervals.
    """
    if not gantt_data:
        return []

    segments: List[Tuple[str, int, int]] = []
    first_time = gantt_data[0][1]

    # Prepend IDLE if simulation start had leading idle time
    if first_time > 0:
        segments.append(("IDLE", 0, first_time))

    start = gantt_data[0][1]
    current_pid = gantt_data[0][0]
    expected_next = start + 1

    for i in range(1, len(gantt_data)):
        pid, time = gantt_data[i]

        if time > expected_next:
            # An implicit idle gap occurred in raw tick data
            segments.append((current_pid, start, expected_next))
            segments.append(("IDLE", expected_next, time))
            current_pid = pid
            start = time
            expected_next = time + 1
        elif pid != current_pid:
            segments.append((current_pid, start, time))
            current_pid = pid
            start = time
            expected_next = time + 1
        else:
            expected_next = time + 1

    segments.append((current_pid, start, expected_next))
    return segments


def generate_gantt_chart(gantt_data: List[Tuple[str, int]]) -> List[Tuple[str, int, int]]:
    """
    Prints an ASCII visualization of the Gantt chart and returns the list of segments.
    """
    segments = extract_gantt_segments(gantt_data)
    if not segments:
        print("\nGantt Chart:\n (empty)")
        return []

    print("\nGantt Chart:")
    print(" ", end="")

    for pid, _, _ in segments:
        label = f"| {pid} "
        print(label, end="")
    print("|")

    # Time markers
    first_start = segments[0][1]
    print(f"{first_start:<3}", end="")

    for pid, _, end in segments:
        cell_width = len(f"| {pid} ")
        print(f"{end:>{cell_width}}", end="")
    print()

    return segments
