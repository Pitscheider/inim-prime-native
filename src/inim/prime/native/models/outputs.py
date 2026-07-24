from dataclasses import dataclass
from typing import Self

from inim.prime.native.models.terminals import Terminal

@dataclass(frozen = True)
class OutputStatus:
    status: bool

@dataclass
class Output(Terminal):
    output_status: OutputStatus | None

    @classmethod
    def from_terminal(
            cls,
            terminal: Terminal,
            output_status: OutputStatus | None
    ) -> Self:
        return cls(
            id = terminal.id,
            label = terminal.label,
            terminal_status = terminal.terminal_status,
            output_status = output_status,
        )

    def __str__(self) -> str:
        return (
            f"ID={self.id} - {self.label}"
            f"\n\tStatus: {self.output_status.status}"
            f"\n\tRaw status: {self.terminal_status.raw.hex(" ")}"
        )

