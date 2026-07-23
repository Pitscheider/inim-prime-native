from dataclasses import dataclass
from enum import IntEnum


class PartitionMode(IntEnum):
    TOTAL = 1
    PARTIAL = 2
    INSTANT = 3
    DISARMED = 4


@dataclass(frozen = True)
class PartitionStatus:
    partition_mode: PartitionMode
    alarm: bool = False
    alarm_memory: bool = False
    sabotage: bool = False
    sabotage_memory: bool = False

    def __str__(self) -> str:
        return (
            f"PartitionStatus("
            f"mode={self.partition_mode.name}, "
            f"alarm={self.alarm}, "
            f"alarm_memory={self.alarm_memory}, "
            f"sabotage={self.sabotage}, "
            f"sabotage_memory={self.sabotage_memory})"
        )


@dataclass
class Partition:
    id: int
    label: str
    status: PartitionStatus | None
