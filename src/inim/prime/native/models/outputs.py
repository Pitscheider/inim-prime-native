from dataclasses import dataclass
from typing import Self, ClassVar

from inim.prime.native.const import Encoding
from inim.prime.native.models.terminals import Terminal, TerminalStatus
from inim.prime.native.utils import decode_int


@dataclass(frozen = True)
class OutputStatus:
    STATUS_ENABLED: ClassVar[int] = 0x01

    state: bool

    @staticmethod
    def decode_state(
            raw_bytes: bytes,
    ) -> bool:
        status_int = decode_int(raw_bytes[1:2], Encoding.UINT8)
        if status_int == OutputStatus.STATUS_ENABLED:
            return True
        return False

@dataclass
class Output(Terminal):

    label: str
    output_status: OutputStatus | None

    @classmethod
    def decode(
            cls,
            terminal_id: int,
            terminal_status: TerminalStatus,
            label: str
    ) -> Self:
        output_state = OutputStatus.decode_state(terminal_status.raw)

        output_status = OutputStatus(
            state = output_state,
        )

        output = cls(
            terminal_id = terminal_id,
            terminal_status = terminal_status,
            label = label,
            output_status = output_status,
        )

        return output

    def update_status(self, status: TerminalStatus | None):
        super().update_status(status)

        if self.terminal_status is not None:
            self.output_status = OutputStatus(
                state = OutputStatus.decode_state(self.terminal_status.raw),
            )
        else:
            self.output_status = None

    def __str__(self) -> str:
        if self.output_status is not None:
            return (
                f"{super().__str__()}"
                f"\n\tOutput label: {self.label}"
                f"\n\tOutput state: {self.output_status.state}"
            )
        else:
            return (
                f"{super().__str__()}"
                f"\n\tOutput label: {self.label}"
                f"\n\tOutput state: None"
            )

