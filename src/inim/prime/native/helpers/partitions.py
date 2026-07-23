import asyncio

from inim.prime.native.models.partitions import Partition
from inim.prime.native.operations.partitions.get_partition_labels import get_partition_labels
from inim.prime.native.operations.partitions.get_partition_statuses import get_partition_statuses
from inim.prime.native.wire import Protocol


async def get_partitions(
        protocol: Protocol,
        pin: str | None = None,
) -> list[Partition]:
    partitions: list[Partition] = []

    partition_labels, partition_statuses = await asyncio.gather(
        get_partition_labels(protocol),
        get_partition_statuses(protocol, pin),
    )

    for idx, p_label in partition_labels.items():
        partitions.append(Partition(
            id = idx,
            label = p_label,
            status = partition_statuses.get(idx),
        ))

    return partitions


async def update_partition_statuses(
        protocol: Protocol,
        partitions: list[Partition],
        pin: str | None = None,
) -> list[Partition]:
    partition_statuses = await get_partition_statuses(protocol, pin)

    for p in partitions:
        p.status = partition_statuses.get(p.id)

    return partitions
