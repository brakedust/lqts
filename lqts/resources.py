from enum import Enum
from multiprocessing import cpu_count
from typing import NamedTuple

SYSTEM_CPU_COUNT = cpu_count()
MAX_CPUS = SYSTEM_CPU_COUNT - 2


class CPUResponse(NamedTuple):
    success: bool
    processors: list


class ProcState(Enum):
    idle = 0
    busy = 1


class CPUResourceManager:
    """
    Manages CPU cores
    Tracks the state of each core and responds to request to allocate cores for a job
    """

    def __init__(self, cpu_count=max(MAX_CPUS, 1)) -> None:
        self.cpu_count = cpu_count

        self.processors = {i: ProcState.idle for i in range(0, self.cpu_count)}

        self._system_cpu_count = SYSTEM_CPU_COUNT

    def cpu_avalaible_count(self) -> int:
        """
        Gets the number of CPU cores available to run a job
        """
        available = [
            p for p, state in self.processors.items() if state == ProcState.idle
        ]
        return len(available)

    def get_processors(self, count=1) -> CPUResponse:
        """
        Gets the number of free processors for the next job
        """
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
        """
        Returns processors to the pool and marks them as idle
        """
        for p in processors:
            if p in self.processors:
                self.processors[p] = ProcState.idle
            else:
                # manager was likely resized and this processor
                # should no longer be considered available
                pass

    def resize(self, new_cpu_count):
        """
        Sets the number of availabe cpus in the pool
        """
        if new_cpu_count == self.cpu_count:
            # no change
            return

        elif new_cpu_count < 1:
            # invalid request
            return

        elif new_cpu_count > self.cpu_count:
            # increase the number of CPUs
            if new_cpu_count > MAX_CPUS:
                new_cpu_count = MAX_CPUS

            for i in range(self.cpu_count, new_cpu_count):
                self.processors[i] = ProcState.idle

        elif new_cpu_count < self.cpu_count:
            # decrease the number of CPUs
            for i in range(new_cpu_count, self.cpu_count):
                self.processors.pop(i)

        self.cpu_count = new_cpu_count
