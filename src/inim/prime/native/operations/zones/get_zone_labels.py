from inim.prime.native.firmware import FirmwareProfile
from inim.prime.native.operations.base import get_labels
from inim.prime.native.utils import Interval
from inim.prime.native.wire.protocol import Protocol


async def get_zone_labels(
        protocol: Protocol,
        profile: FirmwareProfile,
        interval: Interval | None = None,
) -> dict[int, str]:
    return await get_labels(protocol, interval or profile.zone_ids, profile.memory.zone_labels)