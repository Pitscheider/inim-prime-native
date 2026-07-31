from typing import Final

from inim.prime.native.const import CommandOperation
from inim.prime.native.models import ArmingStatus
from inim.prime.native.operations.partitions.const import PARTITION_IDS_INTERVAL
from inim.prime.native.wire import Protocol
from inim.prime.native.wire.payload import CommandWithPinRequestPayload

### Constants
COMMAND_OPERATION: Final[CommandOperation] = CommandOperation.SET_ARMING_STATUS


### Functions
def assemble_data(arming_statuses: dict[int, ArmingStatus]) -> bytes:
    command_data = bytearray(PARTITION_IDS_INTERVAL.size)

    for idx, arming_status in arming_statuses.items():
        command_data[idx] = arming_status

    return command_data


def assemble_payload(arming_statuses: dict[int, ArmingStatus], pin: str | None = None) -> bytes:
    return CommandWithPinRequestPayload.assemble(
        COMMAND_OPERATION,
        data = assemble_data(arming_statuses),
        pin = pin,
    )


async def set_partition_arming_statuses(
        protocol: Protocol,
        arming_status: dict[int, ArmingStatus],
        pin: str | None = None,
) -> None:

    await protocol.execute_command_with_pin(
        operation = COMMAND_OPERATION,
        data = assemble_data(arming_status),
        pin = pin,
    )