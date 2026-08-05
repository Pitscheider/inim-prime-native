from dataclasses import dataclass
from enum import IntEnum, Enum, auto
from typing import Self, ClassVar

class ArmingStatus(IntEnum):
    ARM_AWAY = 1
    ARM_STAY = 2
    ARM_INSTANT = 3
    DISARMED = 4



class PartitionState(Enum):
    OK = auto()
    ALARM = auto()
    TAMPER = auto()



@dataclass(frozen = True)
class PartitionStatus:
    ### Constants
    RAW_SIZE: ClassVar[int] = 3
    # CONFIGURED_MASK: ClassVar[int] = 0x10


    ### Attributes
    arming_status: ArmingStatus
    partition_state: PartitionState
    alarm_memory: bool
    raw: bytes


    ### Constructors
    @classmethod
    def decode(
            cls,
            raw: bytes
    ) -> Self | None:
        if raw == bytes(cls.RAW_SIZE): # If all bytes are 0s
            return None
        else:
            arming_status = cls.decode_arming_status_byte(raw[1])
            partition_state, alarm_memory = cls.decode_alarm_byte(raw[0], raw[2], arming_status)

            return cls(
                arming_status = arming_status,
                partition_state = partition_state,
                alarm_memory = alarm_memory,
                raw = raw,
            )


    ### Static methods
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
    ) -> tuple[PartitionState, bool]:
        # It is not clear why both values changes, so I chose a flexible approach with OR
        partition_state: PartitionState = PartitionState.OK
        alarm_memory: bool = False

        if byte_0 & 0x01 or byte_2 & 0x01:
            alarm_memory = True
            if arming_status != ArmingStatus.DISARMED:
                partition_state = PartitionState.ALARM

        return partition_state, alarm_memory



@dataclass
class Partition:
    ### Attributes
    _partition_id: int
    _label: str
    _zones: set[int]
    status: PartitionStatus | None


    ### Properties
    @property
    def partition_id(self) -> int:
        return self._partition_id

    @property
    def label(self) -> str:
        return self._label

    @property
    def zones(self) -> set[int]:
        return self._zones


    ### Special methods
    def __hash__(self) -> int:
        return hash(self.partition_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Partition):
            return NotImplemented

        return self.partition_id == other.partition_id

    def __str__(self) -> str:

        if self.status is not None:
            return (
                    f"ID={self.partition_id} - {self.label}"
                    f"\n\tZones: {self.zones}"
                    f"\n\tArming status: {self.status.arming_status.name}"
                    f"\n\tState: {self.status.partition_state.name}"
                    f"\n\tAlarm memory: {self.status.alarm_memory}"
                    f"\n\tRaw status: {self.status.raw.hex(" ")}"
            )
        else:
            return (
                f"ID={self.partition_id} - {self.label}"
                f"\n\tZones: {self.zones}"
                f"\n\tStatus: None"
            )

