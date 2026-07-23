from typing import Final

from inim.prime.native.const import Address, EncodingSizes, Encoding
from inim.prime.native.models.terminals import TerminalSetting
from inim.prime.native.operations.terminals.utils import validate_terminals_interval
from inim.prime.native.utils import Interval, decode_int
from inim.prime.native.wire import Protocol

### Constants
TERMINAL_SETTING_SIZE: Final[int] = 11

'''
It is possible to read Terminals Settings from the panel's Memory from address Address.GET_TERMINAL_SETTINGS.
Each terminal uses 11 bytes
[0:4] Bitmask to determine in which partitions the terminal is, UINT32_LE
[4:12] Unknown
'''

def _decode_partitions(raw_bytes: bytes) -> frozenset[int]:
    mask = decode_int(raw_bytes[0:4], Encoding.UINT32_LE)
    return frozenset(i for i in range(mask.bit_length()) if mask & (1 << i))

async def get_terminal_settings_by_interval(
        protocol: Protocol,
        interval: Interval,
) -> dict[int, TerminalSetting]:

    validate_terminals_interval(interval)
    terminals_number = interval.end - interval.start + 1


    size = TERMINAL_SETTING_SIZE * terminals_number

    response = await protocol.read_memory(
        start_address = Address.GET_TERMINAL_SETTINGS + interval.start * TERMINAL_SETTING_SIZE,
        bytes_to_read = size,
    )

    terminals: dict[int, TerminalSetting] = {}

    for idx, offset in enumerate(
            range(0, size, TERMINAL_SETTING_SIZE),
            start = interval.start,
    ):
        raw_bytes = response[offset:offset + TERMINAL_SETTING_SIZE]
        partitions = _decode_partitions(raw_bytes)
        terminals[idx] = TerminalSetting(raw_bytes, partitions)
    return terminals