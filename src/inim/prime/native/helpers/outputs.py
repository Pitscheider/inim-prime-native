from typing import Final

from inim.prime.native.const import Encoding
from inim.prime.native.helpers.terminals import get_terminals_by_intervals, update_terminal_statuses_by_intervals
from inim.prime.native.models import PartitionStatus
from inim.prime.native.models.outputs import Output, OutputStatus
from inim.prime.native.models.terminals import Terminal
from inim.prime.native.utils import Interval, decode_int
from inim.prime.native.wire import Protocol


### Constants
STATUS_ENABLED: Final[int] = 0x01

def _decode_output_status(
        raw_bytes: bytes,
) -> bool:
    status_int = decode_int(raw_bytes[1:2], Encoding.UINT8)
    if status_int == STATUS_ENABLED:
        return True
    return False


def terminals_to_outputs(
    terminals: dict[int, Terminal],
) -> dict[int, Output]:
    outputs: dict[int, Output] = {}

    for terminal_id, t in terminals.items():
        output_status = None

        if t.terminal_status is not None:
            status = _decode_output_status(t.terminal_status.raw)

            output_status = OutputStatus(
                status=status,
            )

        outputs[terminal_id] = Output.from_terminal(t, output_status)

    return outputs

async def get_outputs_by_intervals(
        protocol: Protocol,
        intervals: list[Interval],
        pin: str | None = None,
) -> dict[int, Output]:
    terminals = await get_terminals_by_intervals(protocol, intervals, pin)
    return terminals_to_outputs(terminals)


async def update_output_statuses_by_intervals(
        protocol: Protocol,
        outputs: dict[int, Output],
        intervals: list[Interval],
        pin: str | None = None,
) -> dict[int, Output]:
    outputs = await update_terminal_statuses_by_intervals(protocol, outputs, intervals, pin)

    for output in outputs.values():
        output_status = None

        if output.terminal_status is not None:
            status = _decode_output_status(output.terminal_status.raw)

            output_status = OutputStatus(
                status = status,
            )
        output.output_status = output_status

    return outputs