from scheduler.process import Process
from starvation.detector import StarvationDetector

p1 = Process("P1", 0, 5, 2)
p1.waiting_time = 12
p1.bypass_count = 4

detector = StarvationDetector()

score = detector.calculate_score(p1)

print("PID:", p1.pid)
print("Waiting Time:", p1.waiting_time)
print("Bypass Count:", p1.bypass_count)
print("Starvation Score:", score)
print("Starving:", detector.is_starving(p1))
