from typing import Final

from inim.prime.native.const import Encoding, CommandOperation
from inim.prime.native.utils import encode_int
from inim.prime.native.wire.payload import CommandWithPinRequestPayload
from inim.prime.native.wire.protocol import Protocol

### Constants
COMMAND_OPERATION: Final[CommandOperation] = CommandOperation.RESET_PARTITIONS


### Functions
def assemble_data(partition_ids: set[int]) -> bytes:
    partitions_to_reset_int = 0
    for idx in partition_ids:
        partitions_to_reset_int += 2 ** idx

    command_data = encode_int(partitions_to_reset_int, Encoding.UINT32_LE)

    return command_data


def assemble_payload(partition_ids: set[int], pin: str | None = None) -> bytes:
    return CommandWithPinRequestPayload.assemble(
        COMMAND_OPERATION,
        pin,
        assemble_data(partition_ids),
    )


async def reset_partition_memories(
        protocol: Protocol,
        partition_ids: set[int],
        pin: str | None = None,
) -> None:

    await protocol.execute_command_with_pin(
        operation = CommandOperation.RESET_PARTITIONS,
        data = assemble_data(partition_ids),
        pin = pin,
    )
