from inim.prime.native.const import Address
from inim.prime.native.operations.base import get_labels
from inim.prime.native.operations.terminals.const import TerminalType, TERMINAL_LAYOUT
from inim.prime.native.utils import Interval, truncate_interval
from inim.prime.native.wire import Protocol

async def get_terminal_labels(
        protocol: Protocol,
        interval: Interval,
) -> dict[int, str]:
    standard_terminals_interval = truncate_interval(
        interval,
        TERMINAL_LAYOUT[TerminalType.PANEL].start,
        TERMINAL_LAYOUT[TerminalType.VIRTUAL].stop - 1,
    )
    output_terminals_interval = truncate_interval(
        interval,
        TERMINAL_LAYOUT[TerminalType.OUTPUT].start,
        TERMINAL_LAYOUT[TerminalType.OUTPUT].stop - 1,
    )

    labels = {}
    if standard_terminals_interval is not None:
        labels |= await get_labels(protocol, standard_terminals_interval, Address.TERMINAL_LABELS)
    if output_terminals_interval is not None:
        labels |= await get_labels(protocol, output_terminals_interval, Address.OUTPUT_LABELS, -TERMINAL_LAYOUT[TerminalType.OUTPUT].start)

    return labels