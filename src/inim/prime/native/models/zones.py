from dataclasses import dataclass, fields
from enum import IntEnum
from typing import Self

from inim.prime.native.models.partitions import Partition
from inim.prime.native.models.terminals import Terminal

class ZoneState(IntEnum):
    # Needs check
    FAULT = 0
    READY = 1
    ALARM = 2
    SHORT_CIRCUIT = 3

@dataclass
class Zone(Terminal):
    zone_status: ZoneStatus | None

    @classmethod
    def from_terminal(
            cls,
            terminal: Terminal,
            zone_status: ZoneStatus | None
    ) -> Self:
        return cls(
            id = terminal.id,
            label = terminal.label,
            terminal_status = terminal.terminal_status,
            setting = terminal.setting,
            zone_status = zone_status,
        )

    def __str__(self) -> str:
        return (
            f"ID={self.id} - {self.label}"
            f"\n\tState: {self.zone_status.state.name}"
            f"\n\tBypass: {self.zone_status.bypass}"
            f"\n\tPartition IDs: {sorted(self.setting.partitions)}"
            f"\n\tRaw status: {self.terminal_status.raw.hex(" ")}"
        )

    def to_string_partition_labels(
            self,
            partitions: dict[int, Partition],
    ) -> str:
        partition_labels = [
            partitions[i].label
            for i in sorted(self.setting.partitions)
            if i in partitions
        ]

        return (
            f"ID={self.id} - {self.label}"
            f"\n\tState: {self.zone_status.state.name}"
            f"\n\tBypass: {self.zone_status.bypass}"
            f"\n\tPartition IDs: {partition_labels}"
            f"\n\tRaw status: {self.terminal_status.raw.hex(" ")}"
        )

@dataclass(frozen = True)
class ZoneStatus:
    state: ZoneState | None
    bypass: bool