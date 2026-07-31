from dataclasses import dataclass, fields
from enum import IntEnum, auto
from typing import Self

from inim.prime.native.models.partitions import Partition
from inim.prime.native.models.terminals import Terminal

class ZoneState(IntEnum):
    # Needs check
    TAMPER = 0
    STANDBY = 1
    ALARM = 2
    UNKNOWN = auto()

@dataclass(frozen = True)
class ZoneStatus:
    state: ZoneState
    bypass: bool

@dataclass(frozen = True)
class ZoneSetting:
    raw: bytes
    partitions: frozenset[int]

@dataclass
class Zone:
    zone_id: int
    label: str
    zone_status: ZoneStatus
    zone_setting: ZoneSetting | None


    def __str__(self) -> str:
        if self.zone_setting is not None:
            return (
                f"\tZone ID={self.zone_id} - {self.label}"
                f"\n\t\tState: {self.zone_status.state.name}"
                f"\n\t\tBypass: {self.zone_status.bypass}"
                f"\n\t\tPartition IDs: {sorted(self.zone_setting.partitions)}"
                f"\n\t\tRaw setting: {self.zone_setting.raw.hex(" ")}"
            )
        else:
            return (
                f"\tZone ID={self.zone_id} - {self.label}"
                f"\n\t\tState: {self.zone_status.state.name}"
                f"\n\t\tBypass: {self.zone_status.bypass}"
                f"\n\t\tPartition IDs: None"
            )

    # def to_string_partition_labels(
    #         self,
    #         partitions: dict[int, Partition],
    # ) -> str:
    #     partition_labels = [
    #         partitions[i].label
    #         for i in sorted(self.zone_setting.partitions)
    #         if i in partitions
    #     ]
    #
    #     return (
    #         f"ID={self.id} - {self.label}"
    #         f"\n\tState: {self.zone_status.state.name}"
    #         f"\n\tType: {self.zone_status.type.name}"
    #         f"\n\tBypass: {self.zone_status.bypass}"
    #         f"\n\tPartition IDs: {partition_labels}"
    #         f"\n\tRaw status: {self.zone_status.raw.hex(" ")}"
    #     )

@dataclass
class SingleZone(Terminal):
    zone: Zone

    @classmethod
    def from_terminal(cls, terminal: Terminal, zone: Zone) -> Self:
        return cls(
            terminal_id = terminal.terminal_id,
            terminal_status = terminal.terminal_status,
            zone = zone,
        )

    def __str__(self) -> str:
        return (
            f"{super().__str__()}"
            f"\n{self.zone}"
        )

@dataclass
class DoubleZone(Terminal):
    zone_0: Zone
    zone_1: Zone

    @classmethod
    def from_terminal(cls, terminal: Terminal, zone_0: Zone, zone_1: Zone) -> Self:
        return cls(
            terminal_id = terminal.terminal_id,
            terminal_status = terminal.terminal_status,
            zone_0 = zone_0,
            zone_1 = zone_1,
        )

    def __str__(self) -> str:
        return (
            f"{super().__str__()}"
            f"\n{self.zone_0}"
            f"\n{self.zone_1}"
        )