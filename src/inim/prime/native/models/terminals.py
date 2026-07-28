from dataclasses import dataclass
from enum import Enum, auto, IntEnum


class TerminalType(IntEnum):
    SINGLE_ZONE = 0
    OUTPUT = 1
    DOUBLE_ZONE = 3
    DISABLED = 4
    UNKNOWN = auto()

@dataclass(frozen = True)
class TerminalStatus:
    raw: bytes
    type: TerminalType

    def __str__(self) -> str:
        return (
            f"TerminalStatus("
            f"active={self.type.name}, "
            f"raw={self.raw.hex(" ")}"
            f")"
        )

@dataclass
class Terminal:
    terminal_id: int
    terminal_status: TerminalStatus | None

    def __str__(self) -> str:
        if self.terminal_status is not None:
            return (
                f"Terminal ID={self.terminal_id}"
                f"\n\tTerminal type: {self.terminal_status.type.name}"
                f"\n\tRaw status: {self.terminal_status.raw.hex(" ")}"
            )
        else:
            return (
                f"ID={self.terminal_id}"
                f"\n\tTerminal status: {None}"
            )