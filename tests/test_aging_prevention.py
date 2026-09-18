from scheduler.process import Process
from scheduler.priority_scheduler import PriorityScheduler
from scheduler.gantt import generate_gantt_chart

processes = [
    Process("P1", 0, 20, 6),
    Process("P2", 0, 5, 8),
    Process("P3", 0, 5, 9)
]

scheduler = PriorityScheduler(processes)
gantt = scheduler.run()

generate_gantt_chart(gantt)

print("\nAging Events:")

for event in scheduler.aging_events:
    print(
        "Time:", event[0],
        "Process:", event[1],
        "Priority:", event[2], "->", event[3],
        "Score:", event[4]
    )

print("\nFinal Results:")

for p in processes:
    print(
        p.pid,
        "Completion:", p.completion_time,
        "Waiting:", p.waiting_time,
        "Final Priority:", p.current_priority,
        "Aging Adjustments:", p.aging_adjustments
    )
