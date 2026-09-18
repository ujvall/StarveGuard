from scheduler.process import Process


class NormalPriorityScheduler:

    def __init__(self, processes):
        self.processes = processes
        self.time = 0
        self.gantt_chart = []

    def get_ready_processes(self):
        return [
            p for p in self.processes
            if p.arrival_time <= self.time and p.remaining_time > 0
        ]

    def select_process(self):
        ready = self.get_ready_processes()

        if not ready:
            return None

        return min(
            ready,
            key=lambda p: (p.current_priority, p.arrival_time, p.pid)
        )

    def run(self):
        while any(p.remaining_time > 0 for p in self.processes):

            process = self.select_process()

            if process is None:
                self.time += 1
                continue

            if process.first_run_time == -1:
                process.first_run_time = self.time
                process.response_time = self.time - process.arrival_time

            self.gantt_chart.append((process.pid, self.time))

            process.remaining_time -= 1
            self.time += 1

            if process.remaining_time == 0:
                process.completion_time = self.time
                process.turnaround_time = (
                    process.completion_time - process.arrival_time
                )
                process.waiting_time = (
                    process.turnaround_time - process.burst_time
                )

        return self.gantt_chart
