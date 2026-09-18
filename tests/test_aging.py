from scheduler.process import Process
from aging.aging_manager import AgingManager

p = Process("P1", 0, 5, 8)

aging = AgingManager()

scores = [5, 12, 20, 35]

for score in scores:
    aging.apply_aging(p, score)

    print(
        "Score:", score,
        "Current Priority:", p.current_priority,
        "Aging Adjustments:", p.aging_adjustments
    )
