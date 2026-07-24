from dataclasses import dataclass
from enum import Enum, auto

class TerminalState(Enum):
    ZONE = auto()
    OUTPUT = auto()
    DISCONNECTED = auto()

@dataclass(frozen = True)
class TerminalStatus:
    raw: bytes
    state: TerminalState

    def __str__(self) -> str:
        return (
            f"TerminalStatus("
            f"active={self.state.name}, "
            f"raw={self.raw.hex(" ")}"
            f")"
        )

@dataclass
class Terminal:
    id: int
    label: str
    terminal_status: TerminalStatus | None

    def __str__(self) -> str:
        if self.terminal_status is not None:
            return (
                f"ID={self.id} - {self.label}"
                f"\n\tTerminal state: {self.terminal_status.state.name}"
                f"\n\tRaw status: {self.terminal_status.raw.hex(" ")}"
                f"\n\tSetting: {self.setting.raw.hex(" ")}"
            )
        else:
            return (
                f"ID={self.id} - {self.label}"
                f"\n\tTerminal status: {None}"
            )