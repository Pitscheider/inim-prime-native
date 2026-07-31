from dataclasses import dataclass
from enum import auto, IntEnum


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

    @staticmethod
    def decode_type(
            raw_bytes: bytes
    ) -> TerminalType:
        # Check the first byte to determine terminal type
        try:
            return TerminalType(raw_bytes[0])
        except ValueError:
            return TerminalType.UNKNOWN

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
                f"\n\tTerminal status: None"
            )

    def update_status(self, status: TerminalStatus | None):
        self.terminal_status = status