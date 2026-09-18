from scheduler.process import Process
from scheduler.normal_priority_scheduler import NormalPriorityScheduler
from scheduler.gantt import generate_gantt_chart

processes = [
    Process("P1", 0, 20, 6),
    Process("P2", 0, 5, 8),
    Process("P3", 0, 5, 9)
]

scheduler = NormalPriorityScheduler(processes)
gantt = scheduler.run()

generate_gantt_chart(gantt)

print("\nFinal Results:")

for p in processes:
    print(
        p.pid,
        "Completion:", p.completion_time,
        "Waiting:", p.waiting_time,
        "Turnaround:", p.turnaround_time,
        "Response:", p.response_time
    )
