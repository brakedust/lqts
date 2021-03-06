from multiprocessing import cpu_count
from typing import NamedTuple
from enum import Enum


class CPUResponse(NamedTuple):

    success: bool
    processors: list


class ProcState(Enum):

    idle = 0
    busy = 1


class CPUResourceManager:
    def __init__(self, cpu_count=max(cpu_count() - 2, 1)) -> None:

        self.cpu_count = cpu_count

        self.processors = {i: ProcState.idle for i in range(self.cpu_count)}

    def cpu_avalaible_count(self):
        available = [
            p for p, state in self.processors.items() if state == ProcState.idle
        ]
        return len(available)

    def get_processors(self, count=1):

        available = [
            p for p, state in self.processors.items() if state == ProcState.idle
        ]

        if len(available) >= count:
            cpus = available[:count]
            for p in cpus:
                self.processors[p] = ProcState.busy
            return CPUResponse(True, available[:count])
        else:
            return CPUResponse(False, [])

    def free_processors(self, processors: list):

        for p in processors:
            if p in self.processors:
                self.processors[p] = ProcState.idle
            else:
                # manager was likely resized and this processor
                # should no longer be considered available
                pass

    def resize(self, new_cpu_count):

        if new_cpu_count == self.cpu_count:
            return

        elif new_cpu_count > self.cpu_count:
            for i in range(self.cpu_count, new_cpu_count):
                self.processors[i] = ProcState.idle

        elif new_cpu_count < self.cpu_count:
            for i in range(new_cpu_count, self.cpu_count):
                self.processors.pop(i)

        self.cpu_count = new_cpu_count
