from inim.prime.native.const import Memory, Address
from inim.prime.native.operations.base import get_labels
from inim.prime.native.operations.partitions.const import PARTITIONS_MAX_NUMBER, LAST_PARTITION_ID
from inim.prime.native.utils import Interval
from inim.prime.native.wire import Protocol


async def get_partition_labels(
        protocol: Protocol,
        interval: Interval = Interval(0, LAST_PARTITION_ID),
) -> dict[int, str]:
    return await get_labels(protocol, interval, Address.PARTITION_LABELS)

