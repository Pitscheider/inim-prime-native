from inim.prime.native.const import Address
from inim.prime.native.operations.base import get_labels
from inim.prime.native.operations.zones.const import ZONE_IDS_INTERVAL
from inim.prime.native.utils import Interval
from inim.prime.native.wire import Protocol


async def get_zone_labels(
        protocol: Protocol,
        interval: Interval = ZONE_IDS_INTERVAL,
) -> dict[int, str]:
    return await get_labels(protocol, interval, Address.ZONE_LABELS)