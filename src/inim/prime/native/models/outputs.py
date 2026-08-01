from dataclasses import dataclass
from typing import Self, ClassVar

from inim.prime.native.const import Encoding
from inim.prime.native.models.terminals import Terminal, TerminalStatus
from inim.prime.native.utils import decode_int


@dataclass(frozen = True)
class OutputStatus:
    ### Constants
    STATUS_ENABLED: ClassVar[int] = 0x01


    ### Attributes
    state: bool


    ### Static methods
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
    ### Attributes
    _label: str
    output_status: OutputStatus | None


    ### Properties
    @property
    def label(self) -> str:
        return self._label


    ### Constructors
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
            _terminal_id = terminal_id,
            terminal_status = terminal_status,
            _label = label,
            output_status = output_status,
        )

        return output


    ### Special methods
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


    ### Methods
    def update_status(self, status: TerminalStatus | None):
        super().update_status(status)

        if self.terminal_status is not None:
            self.output_status = OutputStatus(
                state = OutputStatus.decode_state(self.terminal_status.raw),
            )
        else:
            self.output_status = None