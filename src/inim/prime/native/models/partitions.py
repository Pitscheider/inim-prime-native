from dataclasses import dataclass
from enum import IntEnum


class ArmingStatus(IntEnum):
    ARM_AWAY = 1
    ARM_STAY = 2
    ARM_INSTANT = 3
    DISARMED = 4


@dataclass(frozen = True)
class PartitionStatus:
    arming_status: ArmingStatus
    alarm: bool
    alarm_memory: bool
    sabotage: bool | None
    sabotage_memory: bool | None
    raw: bytes


@dataclass
class Partition:
    id: int
    label: str
    status: PartitionStatus | None

    def __str__(self) -> str:

        return (
                f"ID={self.id} - {self.label}"
                f"\n\tArming status: {self.status.arming_status.name}"
                f"\n\tAlarm: {self.status.alarm}"
                f"\n\tAlarm memory: {self.status.alarm_memory}"
                f"\n\tSabotage: {self.status.sabotage}"
                f"\n\tSabotage memory: {self.status.sabotage_memory}"
                f"\n\tRaw status: {self.status.raw.hex(" ")}"
        )