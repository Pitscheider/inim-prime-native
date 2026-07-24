import asyncio

from inim.prime.native.models.partitions import Partition
from inim.prime.native.operations.partitions.get_partition_labels import get_partition_labels
from inim.prime.native.operations.partitions.get_partition_statuses import get_partition_statuses
from inim.prime.native.wire import Protocol


async def get_partitions(
    protocol: Protocol,
    ids: set[int],
    pin: str | None = None,
) -> dict[int, Partition]:
    partition_labels, partition_statuses = await asyncio.gather(
        get_partition_labels(protocol),
        get_partition_statuses(protocol, pin),
    )

    partitions: dict[int, Partition] = {}

    for idx in ids:
        label = partition_labels.get(idx)
        if label is not None:
            partitions[idx] = Partition(
                id = idx,
                label = label,
                status = partition_statuses.get(idx),
            )
    return partitions

async def update_partition_statuses(
    protocol: Protocol,
    partitions: dict[int, Partition],
    pin: str | None = None,
) -> dict[int, Partition]:
    partition_statuses = await get_partition_statuses(protocol, pin)

    for partition_id, partition in partitions.items():
        partition.status = partition_statuses.get(partition_id)

    return partitions
