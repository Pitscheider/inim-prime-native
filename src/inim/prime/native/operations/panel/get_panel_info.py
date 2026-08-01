from typing import Final

from inim.prime.native.const import CommandOperation
from inim.prime.native.utils import next_slice
from inim.prime.native.wire.payload import CommandRequestPayload
from inim.prime.native.wire.protocol import Protocol


### Constants
class Layout:
    serial_number_size: Final[int] = 16
    description_size: Final[int] = 16

    serial_number: Final[slice] = next_slice(0, serial_number_size)
    description: Final[slice] = next_slice(serial_number, description_size)

RESPONSE_PAYLOAD_DATA_LENGTH: Final[int] = 34
COMMAND_OPERATION: Final[CommandOperation] = CommandOperation.GET_PANEL_INFO


### Functions
def assemble_payload() -> bytes:
    return CommandRequestPayload.assemble(
        COMMAND_OPERATION,
    )


def disassemble_data(response_data: bytes) -> tuple[str, str]:
    serial_number = response_data[Layout.serial_number].decode("ascii").rstrip()
    description = response_data[Layout.description].decode("ascii").rstrip()

    return serial_number, description


async def get_panel_info(
        protocol: Protocol,
) -> tuple[str, str, str]:


    response_data = await protocol.execute_command(
        operation = CommandOperation.GET_PANEL_INFO,
        response_payload_data_length = RESPONSE_PAYLOAD_DATA_LENGTH,
    )

    serial_number, description = disassemble_data(response_data)
    firmware, model = description.split(" ", maxsplit = 1)

    return serial_number, firmware, model