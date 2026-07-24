from typing import Final

from inim.prime.native.const import Encoding, CommandOperation
from inim.prime.native.utils import encode_int
from inim.prime.native.wire import Protocol
from inim.prime.native.wire.payload import CommandWithPinRequestPayload

ENABLE_VALUE: Final[int] = 1
DISABLE_VALUE: Final[int] = 0

def assemble_data(
        idx: int,
        status: bool
) -> bytes:
    id_bytes = encode_int(idx, Encoding.UINT16_LE)

    if status:
        status_bytes = encode_int(ENABLE_VALUE, Encoding.UINT16_LE)
    else:
        status_bytes = encode_int(DISABLE_VALUE, Encoding.UINT16_LE)


    command_data = b"".join([id_bytes, status_bytes])

    return command_data


def assemble_payload(
        idx: int,
        status: bool,
        pin: str | None = None
) -> bytes:
    return CommandWithPinRequestPayload.assemble(
        CommandOperation.SET_OUTPUT_STATUS,
        pin,
        assemble_data(idx, status),
    )


async def set_output_status(
        protocol: Protocol,
        idx: int,
        status: bool,
        pin: str | None = None,
) -> None:
    await protocol.execute_command_with_pin(
        operation = CommandOperation.SET_OUTPUT_STATUS,
        data = assemble_data(idx, status),
        pin = pin,
    )
