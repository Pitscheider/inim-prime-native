from typing import Final

from inim.prime.native.const import CommandOperation
from inim.prime.native.models.partitions import PartitionStatus
from inim.prime.native.operations.partitions.const import PARTITIONS_NUMBER
from inim.prime.native.wire.payload import CommandWithPinRequestPayload
from inim.prime.native.wire.protocol import Protocol

### Constants

COMMAND_OPERATION: Final[CommandOperation] = CommandOperation.GET_PARTITION_STATUSES
RESPONSE_PAYLOAD_DATA_LENGTH: Final[int] = PartitionStatus.RAW_SIZE * PARTITIONS_NUMBER


### Functions
def assemble_payload(pin: str | None = None) -> bytes:
    return CommandWithPinRequestPayload.assemble(
        operation = COMMAND_OPERATION,
        pin = pin,
    )

def disassemble_data(response_data: bytes) -> dict[int, PartitionStatus]:
    partitions: dict[int, PartitionStatus] = {}

    for idx, offset in enumerate(
            range(0, RESPONSE_PAYLOAD_DATA_LENGTH, PartitionStatus.RAW_SIZE),
            start = 0,
    ):
        chunk = response_data[offset:offset + PartitionStatus.RAW_SIZE]
        partition = PartitionStatus.decode(chunk)
        if partition is not None:
            partitions[idx] = partition

    return partitions


async def get_partition_statuses(
        protocol: Protocol,
        pin: str | None = None,
) -> dict[int, PartitionStatus]:

    response = await protocol.execute_command_with_pin(
        operation = CommandOperation.GET_PARTITION_STATUSES,
        pin = pin,
        response_payload_data_length = RESPONSE_PAYLOAD_DATA_LENGTH,
    )

    return disassemble_data(response)