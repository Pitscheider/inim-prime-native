from typing import Final

from inim.prime.native.const import Encoding, CommandOperation
from inim.prime.native.utils import encode_int
from inim.prime.native.wire.payload import CommandWithPinRequestPayload
from inim.prime.native.wire.protocol import Protocol

ENABLE_BYPASS_VALUE: Final[int] = 0
DISABLE_BYPASS_VALUE: Final[int] = 2

def assemble_data(
        zone_id: int,
        bypass: bool
) -> bytes:
    zone_id_bytes = encode_int(zone_id, Encoding.UINT16_LE)

    if bypass:
        bypass_bytes = encode_int(ENABLE_BYPASS_VALUE, Encoding.UINT16_LE)
    else:
        bypass_bytes = encode_int(DISABLE_BYPASS_VALUE, Encoding.UINT16_LE)


    command_data = b"".join([zone_id_bytes, bypass_bytes])

    return command_data


def assemble_payload(
        zone_id: int,
        bypass: bool,
        pin: str | None = None
) -> bytes:
    return CommandWithPinRequestPayload.assemble(
        CommandOperation.SET_ZONE_BYPASS,
        pin,
        assemble_data(zone_id, bypass),
    )


async def set_zone_bypass(
        protocol: Protocol,
        zone_id: int,
        bypass: bool,
        pin: str | None = None,
) -> None:
    await protocol.execute_command_with_pin(
        operation = CommandOperation.SET_ZONE_BYPASS,
        data = assemble_data(zone_id, bypass),
        pin = pin,
    )
