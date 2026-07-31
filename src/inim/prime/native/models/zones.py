from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Self

from inim.prime.native.models.terminals import Terminal, TerminalStatus


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

    @staticmethod
    def decode_bypass_byte(
            byte: int,
    ) -> bool:
        return bool((byte >> 4) & 1)

    @staticmethod
    def decode_state_byte(
            byte: int,
    ) -> ZoneState:
        try:
            return ZoneState(byte)
        except ValueError:
            return ZoneState.UNKNOWN


@dataclass(frozen = True)
class ZoneSetting:
    raw: bytes
    partitions: frozenset[int]



@dataclass
class Zone:
    zone_id: int
    label: str
    zone_status: ZoneStatus | None
    zone_setting: ZoneSetting

    def __hash__(self) -> int:
        return hash(self.zone_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Zone):
            return NotImplemented

        return self.zone_id == other.zone_id

    def __str__(self) -> str:
        if self.zone_status is not None:
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
                f"\n\t\tState: None"
                f"\n\t\tBypass: None"
                f"\n\t\tPartition IDs: {sorted(self.zone_setting.partitions)}"
                f"\n\t\tRaw setting: {self.zone_setting.raw.hex(" ")}"
            )

    def to_string_partition_labels(
            self,
            partition_labels: dict[int, str],
    ) -> str:
        partition_labels = [
            partition_labels[i]
            for i in sorted(self.zone_setting.partitions)
            if i in partition_labels
        ]

        if self.zone_status is not None:
            return (
                f"\tZone ID={self.zone_id} - {self.label}"
                f"\n\t\tState: {self.zone_status.state.name}"
                f"\n\t\tBypass: {self.zone_status.bypass}"
                f"\n\t\tPartition IDs: {partition_labels}"
                f"\n\t\tRaw setting: {self.zone_setting.raw.hex(" ")}"
            )
        else:
            return (
                f"\tZone ID={self.zone_id} - {self.label}"
                f"\n\t\tState: None"
                f"\n\t\tBypass: None"
                f"\n\t\tPartition IDs: {partition_labels}"
                f"\n\t\tRaw setting: {self.zone_setting.raw.hex(" ")}"
            )

class ZoneTerminal(Terminal, ABC):
    @abstractmethod
    def to_string_partition_labels(
            self,
            partition_labels: dict[int, str],
    ) -> str:
        ...

    @property
    @abstractmethod
    def zones(self) -> tuple[Zone, ...]:
        ...

@dataclass
class SingleZone(ZoneTerminal):
    zone: Zone

    @classmethod
    def from_terminal(cls, terminal: Terminal, zone: Zone) -> Self:
        return cls(
            terminal_id = terminal.terminal_id,
            terminal_status = terminal.terminal_status,
            zone = zone,
        )

    @property
    def zones(self) -> tuple[Zone]:
        return self.zone,

    @classmethod
    def decode(
            cls,
            terminal_id: int,
            terminal_status: TerminalStatus,
            zone_id: int,
            zone_label: str,
            zone_setting: ZoneSetting,
    ) -> Self:
        state = cls.decode_state(terminal_status.raw)
        bypass = cls.decode_bypass(terminal_status.raw)

        zone_status = ZoneStatus(
            state = state,
            bypass = bypass,
        )

        zone = Zone(
            zone_id = zone_id,
            label = zone_label,
            zone_status = zone_status,
            zone_setting = zone_setting,
        )
        single_zone = cls(
            terminal_id = terminal_id,
            terminal_status = terminal_status,
            zone = zone,
        )
        return single_zone


    @staticmethod
    def decode_state(
            raw_bytes: bytes,
    ) -> ZoneState:
        return ZoneStatus.decode_state_byte(raw_bytes[4])

    @staticmethod
    def decode_bypass(
            raw_bytes: bytes,
    ) -> bool:
        return ZoneStatus.decode_bypass_byte(raw_bytes[2])



    def __str__(self) -> str:
        return (
            f"{super().__str__()}"
            f"\n{self.zone}"
        )

    def to_string_partition_labels(
            self,
            partition_labels: dict[int, str],
    ) -> str:
        return (
            f"{super().__str__()}"
            f"\n{self.zone.to_string_partition_labels(partition_labels)}"
        )

    def update_status(self, status: TerminalStatus | None):
        super().update_status(status)

        if self.terminal_status is not None:
            self.zone.zone_status = ZoneStatus(
                state = self.decode_state(self.terminal_status.raw),
                bypass = self.decode_bypass(self.terminal_status.raw),
            )
        else:
            self.zone.zone_status = None





@dataclass
class DoubleZone(ZoneTerminal):
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

    @property
    def zones(self) -> tuple[Zone, Zone]:
        return self.zone_0, self.zone_1

    @classmethod
    def decode(
            cls,
            terminal_id: int,
            terminal_status: TerminalStatus,
            zone_0_id: int,
            zone_0_label: str,
            zone_0_setting: ZoneSetting,
            zone_1_id: int,
            zone_1_label: str,
            zone_1_setting: ZoneSetting,
    ) -> Self:
        state = cls.decode_state(terminal_status.raw)
        bypass = cls.decode_bypass(terminal_status.raw)

        # Zone 0
        zone_0_status = ZoneStatus(
            state = state[0],
            bypass = bypass[0],
        )

        zone_0 = Zone(
            zone_id = zone_0_id,
            label = zone_0_label,
            zone_status = zone_0_status,
            zone_setting = zone_0_setting,
        )

        # Zone 1
        zone_1_status = ZoneStatus(
            state = state[1],
            bypass = bypass[1],
        )

        zone_1 = Zone(
            zone_id = zone_1_id,
            label = zone_1_label,
            zone_status = zone_1_status,
            zone_setting = zone_1_setting,
        )

        double_zone = cls(
            terminal_id = terminal_id,
            terminal_status = terminal_status,
            zone_0 = zone_0,
            zone_1 = zone_1,
        )

        return double_zone

    @staticmethod
    def decode_bypass(
            raw_bytes: bytes,
    ) -> tuple[bool, bool]:
        zone_0 = ZoneStatus.decode_bypass_byte(raw_bytes[2])
        zone_1 = ZoneStatus.decode_bypass_byte(raw_bytes[6])
        return zone_0, zone_1

    @staticmethod
    def decode_state(
            raw_bytes: bytes,
    ) -> tuple[ZoneState, ZoneState]:
        zone_0 = ZoneStatus.decode_state_byte(raw_bytes[4])
        zone_1 = ZoneStatus.decode_state_byte(raw_bytes[8])
        return zone_0, zone_1

    def update_status(self, status: TerminalStatus | None):
        super().update_status(status)

        if self.terminal_status is not None:
            zone_0_state, zone_1_state = self.decode_state(self.terminal_status.raw)
            zone_0_bypass, zone_1_bypass = self.decode_bypass(self.terminal_status.raw)

            self.zone_0.zone_status = ZoneStatus(
                state = zone_0_state,
                bypass = zone_0_bypass,
            )

            self.zone_1.zone_status = ZoneStatus(
                state = zone_1_state,
                bypass = zone_1_bypass,
            )
        else:
            self.zone_0.zone_status = None
            self.zone_1.zone_status = None

    def __str__(self) -> str:
        return (
            f"{super().__str__()}"
            f"\n{self.zone_0}"
            f"\n{self.zone_1}"
        )

    def to_string_partition_labels(
            self,
            partition_labels: dict[int, str],
    ) -> str:
        return (
            f"{super().__str__()}"
            f"\n{self.zone_0.to_string_partition_labels(partition_labels)}"
            f"\n{self.zone_1.to_string_partition_labels(partition_labels)}"
        )