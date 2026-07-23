from typing import Final

from inim.prime.native.const import Memory, AddressTable, Address
from inim.prime.native.operations import resolve_address
from inim.prime.native.operations.terminals.utils import validate_terminals_interval
from inim.prime.native.utils import Interval
from inim.prime.native.wire import Protocol

async def get_terminal_labels_by_interval(
        protocol: Protocol,
        interval: Interval,
) -> dict[int, str]:

    validate_terminals_interval(interval)
    terminals_number = interval.end - interval.start + 1


    size = Memory.LABEL_SIZE * terminals_number

    response = await protocol.read_memory(
        start_address = Address.GET_TERMINAL_LABELS + interval.start * Memory.LABEL_SIZE,
        bytes_to_read = size
    )

    terminals = {}

    for idx, offset in enumerate(
            range(0, size, Memory.LABEL_SIZE),
            start = interval.start,
    ):
        label = response[offset:offset + Memory.LABEL_SIZE]
        terminals[idx] = label.decode("ascii").strip()
    return terminals