from typing import Final

from inim.prime.native.const import AddressTable, Encoding, CommandOperation, Memory
from inim.prime.native.utils import decode_int, Interval
from inim.prime.native.wire.protocol import Protocol


async def resolve_address(protocol: Protocol, index: int) -> int:
    """
    Resolves an address by performing an indirection lookup.

    The provided index is used to retrieve a 32-bit value from an
    address mapping table. That value represents the resolved address.

    :param protocol: Protocol object to perform the request.
    :param index: Index into the address table (not the final address).
    :return: Resolved 32-bit address stored at the given table entry.
    """
    response = await protocol.read_memory(index, AddressTable.ENTRY_SIZE)
    return decode_int(response, Encoding.UINT32_LE)

async def get_labels(
        protocol: Protocol,
        interval: Interval,
        address: int,
        start_offset: int = 0,
) -> dict[int, str]:
    labels_number = interval.end - interval.start + 1
    size = Memory.LABEL_SIZE * labels_number
    start = interval.start + start_offset


    response = await protocol.read_memory(
        start_address = address + start * Memory.LABEL_SIZE,
        bytes_to_read = size
    )
    labels = {}
    for idx, offset in enumerate(
            range(0, size, Memory.LABEL_SIZE),
            start = interval.start,
    ):
        label = response[offset:offset + Memory.LABEL_SIZE]
        labels[idx] = label.decode("ascii").strip()

    return labels