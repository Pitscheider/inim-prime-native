from typing import Final

from inim.prime.native.const import CommandOperation
from inim.prime.native.models import PartitionStatus
from inim.prime.native.operations.partitions.const import ARMING_STATUS_MAP, PARTITIONS_MAX_NUMBER
from inim.prime.native.wire import Protocol
from inim.prime.native.wire.payload import CommandWithPinRequestPayload


### Constants

class Layout:
    partition_size: Final[int] = 3
    size: Final[int] = partition_size * PARTITIONS_MAX_NUMBER

COMMAND_OPERATION: Final[CommandOperation] = CommandOperation.GET_PARTITION_STATUSES
CONFIGURED_MASK: Final[int] = 0x10
ALARM_MASK: Final[int] = 0x01
RESPONSE_PAYLOAD_DATA_LENGTH: Final[int] = Layout.size


### Functions
def assemble_payload(pin: str | None = None) -> bytes:
    return CommandWithPinRequestPayload.assemble(
        operation = COMMAND_OPERATION,
        pin = pin,
    )

def disassemble_data(response_data: bytes) -> dict[int, PartitionStatus]:
    partitions: dict[int, PartitionStatus] = {}

    for idx, offset in enumerate(
            range(0, Layout.size, Layout.partition_size),
            start = 0,
    ):
        chunk = response_data[offset:offset + Layout.partition_size]
        partition = decode_partition_status(chunk)
        if partition is not None:
            partitions[idx] = partition

    return partitions

def decode_partition_status(p: bytes) -> PartitionStatus | None:
    ### Byte 1
    mode = ARMING_STATUS_MAP.get(p[1])

    if mode is None:
        return None

    ### Byte 2
    # is_configured = bool(p[2] & CONFIGURED_MASK)
    has_alarm = bool(p[2] & ALARM_MASK)

    return PartitionStatus(
        arming_status = mode,
        alarm = has_alarm,
        alarm_memory = has_alarm,
        sabotage = None,
        sabotage_memory = None,
        raw = p,
    )


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