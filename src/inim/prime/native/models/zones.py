from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
from typing import Self

from inim.prime.native.models.terminals import Terminal, TerminalStatus


class ZoneState(IntEnum):
    TAMPER = 0
    STANDBY = 1
    ALARM = 2
    SHORT_CIRCUIT = 3



@dataclass(frozen = True)
class ZoneStatus:
    ### Attributes
    state: ZoneState
    bypass: bool
    alarm_memory: bool

    ### Static methods
    @staticmethod
    def decode_bypass_byte(
            byte: int,
    ) -> bool:
        return bool(byte & 0x10)

    @staticmethod
    def decode_alarm_memory_byte(
            byte: int
    ) -> bool:
        return bool(byte & 0x01)

    @staticmethod
    def decode_state_byte(
            byte: int,
    ) -> ZoneState:
        return ZoneState(byte)



@dataclass(frozen = True)
class ZoneSetting:
    ### Attributes
    raw: bytes
    partitions: frozenset[int]



@dataclass
class Zone:
    ### Attributes
    _zone_id: int
    _label: str
    _zone_setting: ZoneSetting
    zone_status: ZoneStatus | None


    ### Properties
    @property
    def zone_id(self) -> int:
        return self._zone_id

    @property
    def label(self) -> str:
        return self._label

    @property
    def zone_setting(self) -> ZoneSetting:
        return self._zone_setting


    ### Special methods
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
                f"\n\t\tAlarm memory: {self.zone_status.alarm_memory}"
                f"\n\t\tPartition IDs: {sorted(self.zone_setting.partitions)}"
                f"\n\t\tRaw setting: {self.zone_setting.raw.hex(" ")}"
            )
        else:
            return (
                f"\tZone ID={self.zone_id} - {self.label}"
                f"\n\t\tZone status: None"
                f"\n\t\tPartition IDs: {sorted(self.zone_setting.partitions)}"
                f"\n\t\tRaw setting: {self.zone_setting.raw.hex(" ")}"
            )


    ### Methods
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
                f"\n\t\tAlarm memory: {self.zone_status.alarm_memory}"
                f"\n\t\tPartition IDs: {partition_labels}"
                f"\n\t\tRaw setting: {self.zone_setting.raw.hex(" ")}"
            )
        else:
            return (
                f"\tZone ID={self.zone_id} - {self.label}"
                f"\n\t\tZone status: None"
                f"\n\t\tPartition IDs: {partition_labels}"
                f"\n\t\tRaw setting: {self.zone_setting.raw.hex(" ")}"
            )



class ZoneTerminal(Terminal, ABC):
    ### Properties
    @property
    @abstractmethod
    def zones(self) -> tuple[Zone, ...]:
        ...


    ### Methods
    @abstractmethod
    def to_string_partition_labels(
            self,
            partition_labels: dict[int, str],
    ) -> str:
        ...



@dataclass
class SingleZone(ZoneTerminal):
    ### Properties
    _zone: Zone


    ### Properties
    @property
    def zone(self) -> Zone:
        return self._zone

    @property
    def zones(self) -> tuple[Zone]:
        return self.zone,


    ### Constructors
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
        alarm_memory = cls.decode_alarm_memory(terminal_status.raw)

        zone_status = ZoneStatus(
            state = state,
            bypass = bypass,
            alarm_memory = alarm_memory,
        )

        zone = Zone(
            _zone_id = zone_id,
            _label = zone_label,
            zone_status = zone_status,
            _zone_setting = zone_setting,
        )
        single_zone = cls(
            _terminal_id = terminal_id,
            terminal_status = terminal_status,
            _zone = zone,
        )
        return single_zone


    ### Special methods
    def __str__(self) -> str:
        return (
            f"{super().__str__()}"
            f"\n{self.zone}"
        )


    ### Methods
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
                alarm_memory = self.decode_alarm_memory(self.terminal_status.raw),
            )
        else:
            self.zone.zone_status = None


    ### Static methods
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

    @staticmethod
    def decode_alarm_memory(
            raw_bytes: bytes,
    ) -> bool:
        return ZoneStatus.decode_alarm_memory_byte(raw_bytes[2])



@dataclass
class DoubleZone(ZoneTerminal):
    ### Attributes
    _zone_0: Zone
    _zone_1: Zone


    ### Property
    @property
    def zone_0(self) -> Zone:
        return self._zone_0

    @property
    def zone_1(self) -> Zone:
        return self._zone_1

    @property
    def zones(self) -> tuple[Zone, Zone]:
        return self.zone_0, self.zone_1


    ### Constructors
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
        zone_0_state, zone_1_state = cls.decode_state(terminal_status.raw)
        zone_0_bypass, zone_1_bypass = cls.decode_bypass(terminal_status.raw)
        zone_0_alarm_memory, zone_1_alarm_memory = cls.decode_alarm_memory(terminal_status.raw)

        # Zone 0
        zone_0_status = ZoneStatus(
            state = zone_0_state,
            bypass = zone_0_bypass,
            alarm_memory = zone_0_alarm_memory,
        )

        zone_0 = Zone(
            _zone_id = zone_0_id,
            _label = zone_0_label,
            zone_status = zone_0_status,
            _zone_setting = zone_0_setting,
        )

        # Zone 1
        zone_1_status = ZoneStatus(
            state = zone_1_state,
            bypass = zone_1_bypass,
            alarm_memory = zone_1_alarm_memory,
        )

        zone_1 = Zone(
            _zone_id = zone_1_id,
            _label = zone_1_label,
            zone_status = zone_1_status,
            _zone_setting = zone_1_setting,
        )

        double_zone = cls(
            _terminal_id = terminal_id,
            terminal_status = terminal_status,
            _zone_0 = zone_0,
            _zone_1 = zone_1,
        )

        return double_zone


    ### Special methods
    def __str__(self) -> str:
        return (
            f"{super().__str__()}"
            f"\n{self.zone_0}"
            f"\n{self.zone_1}"
        )


    ### Methods
    def to_string_partition_labels(
            self,
            partition_labels: dict[int, str],
    ) -> str:
        return (
            f"{super().__str__()}"
            f"\n{self.zone_0.to_string_partition_labels(partition_labels)}"
            f"\n{self.zone_1.to_string_partition_labels(partition_labels)}"
        )

    def update_status(self, status: TerminalStatus | None):
        super().update_status(status)

        if self.terminal_status is not None:
            zone_0_state, zone_1_state = self.decode_state(self.terminal_status.raw)
            zone_0_bypass, zone_1_bypass = self.decode_bypass(self.terminal_status.raw)
            zone_0_alarm_memory, zone_1_alarm_memory = self.decode_bypass(self.terminal_status.raw)

            self.zone_0.zone_status = ZoneStatus(
                state = zone_0_state,
                bypass = zone_0_bypass,
                alarm_memory = zone_0_alarm_memory,
            )

            self.zone_1.zone_status = ZoneStatus(
                state = zone_1_state,
                bypass = zone_1_bypass,
                alarm_memory = zone_1_alarm_memory,
            )
        else:
            self.zone_0.zone_status = None
            self.zone_1.zone_status = None


    ### Static methods
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

    @staticmethod
    def decode_alarm_memory(
            raw_bytes: bytes,
    ) -> tuple[bool, bool]:
        zone_0 = ZoneStatus.decode_alarm_memory_byte(raw_bytes[2])
        zone_1 = ZoneStatus.decode_alarm_memory_byte(raw_bytes[6])

        return zone_0, zone_1