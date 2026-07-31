from dataclasses import dataclass
from enum import IntEnum, Enum, auto
from typing import Self, ClassVar

from inim.prime.native.models.zones import Zone


class ArmingStatus(IntEnum):
    ARM_AWAY = 1
    ARM_STAY = 2
    ARM_INSTANT = 3
    DISARMED = 4

class PartitionAlarmStatus(Enum):
    NO_ALARM = auto()
    ACTIVE_ALARM = auto()
    ALARM_MEMORY = auto()


@dataclass(frozen = True)
class PartitionStatus:
    ### Constants
    RAW_SIZE: ClassVar[int] = 3
    # CONFIGURED_MASK: ClassVar[int] = 0x10

    arming_status: ArmingStatus
    alarm_status: PartitionAlarmStatus
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
            alarm_status = cls.decode_alarm_byte(raw[0], raw[2], arming_status)

            return cls(
                arming_status = arming_status,
                alarm_status = alarm_status,
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
            byte_0: int,
            byte_2: int,
            arming_status: ArmingStatus,
    ) -> PartitionAlarmStatus:
        # It is not clear why both values changes, so I chose a flexible approach with OR
        if byte_0 & 0x01 or byte_2 & 0x01:
            if arming_status == ArmingStatus.DISARMED:
                return PartitionAlarmStatus.ALARM_MEMORY
            else:
                return PartitionAlarmStatus.ACTIVE_ALARM
        return PartitionAlarmStatus.NO_ALARM

@dataclass
class Partition:
    id: int
    label: str
    status: PartitionStatus | None
    zones: set[Zone]

    def __str__(self) -> str:
        zone_labels = [zone.label for zone in self.zones]

        if self.status is not None:
            return (
                    f"ID={self.id} - {self.label}"
                    f"\n\tZones: {zone_labels}"
                    f"\n\tArming status: {self.status.arming_status.name}"
                    f"\n\tAlarm status: {self.status.alarm_status.name}"
                    f"\n\tSabotage: {self.status.sabotage}"
                    f"\n\tSabotage memory: {self.status.sabotage_memory}"
                    f"\n\tRaw status: {self.status.raw.hex(" ")}"
            )
        else:
            return (
                f"ID={self.id} - {self.label}"
                f"\n\tZones: {zone_labels}"
                f"\n\tStatus: None"
            )