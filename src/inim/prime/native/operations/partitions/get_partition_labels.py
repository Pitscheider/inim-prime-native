from inim.prime.native.firmware import FirmwareProfile
from inim.prime.native.operations.base import get_labels
from inim.prime.native.operations.partitions.const import PARTITION_IDS_INTERVAL
from inim.prime.native.utils import Interval
from inim.prime.native.wire.protocol import Protocol


async def get_partition_labels(
        protocol: Protocol,
        profile: FirmwareProfile,
        interval: Interval = PARTITION_IDS_INTERVAL,
) -> dict[int, str]:
    return await get_labels(protocol, interval, profile.memory.partition_labels)