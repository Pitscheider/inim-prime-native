from dataclasses import dataclass, fields
from enum import IntEnum
from typing import Self

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

@dataclass(frozen = True)
class ZoneStatus:
    state: ZoneState | None
    bypass: bool