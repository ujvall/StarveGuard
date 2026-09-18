from scheduler.process import Process

p = Process("P1", 0, 8, 3)

print("PID:", p.pid)
print("Arrival Time:", p.arrival_time)
print("Burst Time:", p.burst_time)
print("Original Priority:", p.original_priority)
print("Current Priority:", p.current_priority)
print("Remaining Time:", p.remaining_time)
print("Waiting Time:", p.waiting_time)
print("Bypass Count:", p.bypass_count)