from typing import Final

from inim.prime.native.const import Encoding, CommandOperation
from inim.prime.native.firmware import FirmwareProfile
from inim.prime.native.operations.zones.utils import zone_to_terminal
from inim.prime.native.utils import encode_int
from inim.prime.native.wire.payload import CommandWithPinRequestPayload
from inim.prime.native.wire.protocol import Protocol

ENABLE_BYPASS_VALUE: Final[int] = 0
DISABLE_BYPASS_VALUE: Final[int] = 2

# Bit 0 of the value selects the terminal's second zone (half B).
HALF_B_FLAG: Final[int] = 1


def assemble_data(
        zone_id: int,
        bypass: bool,
        zone_1_id_offset: int,
) -> bytes:
    terminal, half = zone_to_terminal(zone_id, zone_1_id_offset)

    value = (ENABLE_BYPASS_VALUE if bypass else DISABLE_BYPASS_VALUE) | (HALF_B_FLAG if half else 0)

    return b"".join([
        encode_int(terminal, Encoding.UINT16_LE),
        encode_int(value, Encoding.UINT16_LE),
    ])


def assemble_payload(
        zone_id: int,
        bypass: bool,
        zone_1_id_offset: int,
        pin: str | None = None,
) -> bytes:
    return CommandWithPinRequestPayload.assemble(
        CommandOperation.SET_ZONE_BYPASS,
        pin,
        assemble_data(zone_id, bypass, zone_1_id_offset),
    )


async def set_zone_bypass(
        protocol: Protocol,
        profile: FirmwareProfile,
        zone_id: int,
        bypass: bool,
        pin: str | None = None,
) -> None:
    await protocol.execute_command_with_pin(
        operation = CommandOperation.SET_ZONE_BYPASS,
        data = assemble_data(zone_id, bypass, profile.zone_1_id_offset),
        pin = pin,
    )