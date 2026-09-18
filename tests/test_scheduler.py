from scheduler.process import Process
from scheduler.priority_scheduler import PriorityScheduler
from scheduler.gantt import generate_gantt_chart

processes = [
    Process("P1", 0, 5, 2),
    Process("P2", 0, 3, 1),
    Process("P3", 0, 4, 3)
]

scheduler = PriorityScheduler(processes)
gantt = scheduler.run()

generate_gantt_chart(gantt)

print("\nProcess Results:")
for p in processes:
    print(
        p.pid,
        "Completion:", p.completion_time,
        "Waiting:", p.waiting_time,
        "Turnaround:", p.turnaround_time,
        "Response:", p.response_time,
        "Bypass:", p.bypass_count
    )
