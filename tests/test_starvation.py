from scheduler.process import Process
from scheduler.priority_scheduler import PriorityScheduler
from starvation.detector import StarvationDetector

processes = [
    Process("P1", 0, 30, 1),
    Process("P2", 0, 5, 8),
    Process("P3", 0, 5, 9)
]

scheduler = PriorityScheduler(processes)
scheduler.run()

print("\nAging Events:")

for event in scheduler.aging_events:
    print(
        "Time:", event[0],
        "Process:", event[1],
        "Priority:", event[2], "->", event[3],
        "Score:", event[4]
    )

detector = StarvationDetector()

print("\nStarvation Analysis:")

for p in processes:
    score = detector.calculate_score(p)

    print(
        p.pid,
        "Waiting:", p.waiting_time,
        "Bypass:", p.bypass_count,
        "Score:", score,
        "Original Priority:", p.original_priority,
        "Final Priority:", p.current_priority,
        "Aging Adjustments:", p.aging_adjustments,
        "Starving:", detector.is_starving(p)
    )
