from dataclasses import dataclass
from enum import IntEnum
from typing import Self, ClassVar


class ArmingStatus(IntEnum):
    ARM_AWAY = 1
    ARM_STAY = 2
    ARM_INSTANT = 3
    DISARMED = 4

@dataclass(frozen = True)
class PartitionStatus:
    ### Constants
    RAW_SIZE: ClassVar[int] = 3
    # CONFIGURED_MASK: ClassVar[int] = 0x10
    ALARM_MASK: ClassVar[int] = 0x01

    arming_status: ArmingStatus
    alarm: bool
    alarm_memory: bool
    sabotage: bool | None
    sabotage_memory: bool | None
    raw: bytes

    @classmethod
    def decode(
            cls,
            raw: bytes
    ) -> Self | None:
        if raw == bytes(cls.RAW_SIZE): # If all bytes are 0s
            return None
        else:
            arming_status = cls.decode_arming_status_byte(raw[1])
            alarm = cls.decode_alarm_byte(raw[2])

            return cls(
                arming_status = arming_status,
                alarm = alarm,
                alarm_memory = alarm,
                sabotage = None,
                sabotage_memory = None,
                raw = raw,
            )

    @staticmethod
    def decode_arming_status_byte(
            byte: int
    ):
        return ArmingStatus(byte)

    @staticmethod
    def decode_alarm_byte(
            byte: int
    ):
        return bool(byte & PartitionStatus.ALARM_MASK)

@dataclass
class Partition:
    id: int
    label: str
    status: PartitionStatus | None

    def __str__(self) -> str:
        if self.status is not None:
            return (
                    f"ID={self.id} - {self.label}"
                    f"\n\tArming status: {self.status.arming_status.name}"
                    f"\n\tAlarm: {self.status.alarm}"
                    f"\n\tAlarm memory: {self.status.alarm_memory}"
                    f"\n\tSabotage: {self.status.sabotage}"
                    f"\n\tSabotage memory: {self.status.sabotage_memory}"
                    f"\n\tRaw status: {self.status.raw.hex(" ")}"
            )
        else:
            return (
                f"ID={self.id} - {self.label}"
                f"\n\tStatus: None"
            )