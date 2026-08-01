import asyncio
from collections import defaultdict

from inim.prime.native.models.partitions import Partition
from inim.prime.native.models.zones import Zone
from inim.prime.native.operations.partitions.get_partition_labels import get_partition_labels
from inim.prime.native.operations.partitions.get_partition_statuses import get_partition_statuses
from inim.prime.native.wire.protocol import Protocol


async def initialize_partitions(
        protocol: Protocol,
        zone_ids_by_partition: dict[int, set[int]],
        pin: str | None = None,
) -> dict[int, Partition]:
    partitions: dict[int, Partition] = {}

    partition_statuses, partition_labels = await asyncio.gather(
        get_partition_statuses(protocol, pin),
        get_partition_labels(protocol),
    )

    for partition_id, partition_status in partition_statuses.items():
        partitions[partition_id] = Partition(
            _partition_id = partition_id,
            _label = partition_labels[partition_id],
            status = partition_status,
            _zones = zone_ids_by_partition.get(partition_id, set()),
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


def get_zone_ids_by_partition(
    zones: dict[int, Zone],
) -> dict[int, set[int]]:
    partitions: defaultdict[int, set[int]] = defaultdict(set)

    for zone in zones.values():
        for partition in zone.zone_setting.partitions:
            partitions[partition].add(zone.zone_id)

    return dict(partitions)