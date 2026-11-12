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

    # Byte 0: live state
    STATE_ALARM: ClassVar[int] = 1
    STATE_SABOTAGE: ClassVar[int] = 2

    # Byte 2: flags
    FLAG_ALARM_MEMORY: ClassVar[int] = 0x01
    FLAG_SABOTAGE_MEMORY: ClassVar[int] = 0x02
    FLAG_CONFIGURED: ClassVar[int] = 0x10


    ### Attributes
    arming_status: ArmingStatus
    partition_state: PartitionState
    alarm_memory: bool
    sabotage_memory: bool
    raw: bytes


    ### Constructors
    @classmethod
    def decode(
            cls,
            raw: bytes
    ) -> Self | None:
        """
        Decodes a 3-byte partition status record: [state][arming status][flags].
        :return: The status, or None if the partition is not configured
                 or its arming status byte is unknown.
        """
        state, mode, flags = raw

        if not flags & cls.FLAG_CONFIGURED:
            return None

        try:
            arming_status = ArmingStatus(mode)
        except ValueError:
            return None

        in_alarm = state == cls.STATE_ALARM

        if in_alarm and arming_status is not ArmingStatus.DISARMED:
            partition_state = PartitionState.ALARM
        elif state == cls.STATE_SABOTAGE:
            partition_state = PartitionState.TAMPER
        else:
            partition_state = PartitionState.OK

        return cls(
            arming_status = arming_status,
            partition_state = partition_state,
            alarm_memory = in_alarm or bool(flags & cls.FLAG_ALARM_MEMORY),
            sabotage_memory = bool(flags & cls.FLAG_SABOTAGE_MEMORY),
            raw = raw,
        )



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
                    f"\n\tSabotage memory: {self.status.sabotage_memory}"
                    f"\n\tRaw status: {self.status.raw.hex(" ")}"
            )
        else:
            return (
                f"ID={self.partition_id} - {self.label}"
                f"\n\tZones: {self.zones}"
                f"\n\tStatus: None"
            )

