from typing import Final

from inim.prime.native.const import Address, Encoding
from inim.prime.native.models.zones import ZoneSetting
from inim.prime.native.operations.zones.const import ZONE_IDS_INTERVAL
from inim.prime.native.utils import Interval, decode_int
from inim.prime.native.wire.protocol import Protocol

### Constants
ZONE_SETTING_SIZE: Final[int] = 11

'''
It is possible to read Zones Settings from the panel's Memory from address Address.ZONE_SETTINGS.
Each zone uses 11 bytes
[0:4] Bitmask to determine in which partitions the zone is, UINT32_LE
[4:12] Unknown
'''

def _decode_partitions(raw_bytes: bytes) -> frozenset[int]:
    mask = decode_int(raw_bytes[0:4], Encoding.UINT32_LE)
    return frozenset(i for i in range(mask.bit_length()) if mask & (1 << i))

async def get_zone_settings(
        protocol: Protocol,
        interval: Interval = ZONE_IDS_INTERVAL,
) -> dict[int, ZoneSetting]:
    zones_number = interval.end - interval.start + 1


    size = ZONE_SETTING_SIZE * zones_number

    response = await protocol.read_memory(
        start_address = Address.ZONE_SETTINGS + interval.start * ZONE_SETTING_SIZE,
        bytes_to_read = size,
    )

    zones: dict[int, ZoneSetting] = {}

    for idx, offset in enumerate(
            range(0, size, ZONE_SETTING_SIZE),
            start = interval.start,
    ):
        raw_bytes = response[offset:offset + ZONE_SETTING_SIZE]
        partitions = _decode_partitions(raw_bytes)
        zones[idx] = ZoneSetting(raw_bytes, partitions)
    return zones