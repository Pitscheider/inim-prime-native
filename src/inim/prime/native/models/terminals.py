from dataclasses import dataclass

@dataclass(frozen = True)
class TerminalStatus:
    raw: bytes
    active: bool

    def __str__(self) -> str:
        return (
            f"TerminalStatus("
            f"active={self.active}, "
            f"raw={self.raw.hex(" ")}"
            f")"
        )

@dataclass(frozen = True)
class TerminalSetting:
    raw: bytes
    partitions: frozenset[int]

@dataclass
class Terminal:
    id: int
    label: str
    terminal_status: TerminalStatus | None
    setting: TerminalSetting | None