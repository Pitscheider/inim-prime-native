from inim.prime.native.const import Memory, Address
from inim.prime.native.operations.base import get_labels
from inim.prime.native.operations.partitions.const import PARTITION_IDS_INTERVAL
from inim.prime.native.utils import Interval
from inim.prime.native.wire.protocol import Protocol


async def get_partition_labels(
        protocol: Protocol,
        interval: Interval = PARTITION_IDS_INTERVAL,
) -> dict[int, str]:
    return await get_labels(protocol, interval, Address.PARTITION_LABELS)

