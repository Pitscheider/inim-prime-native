import asyncio
from collections import defaultdict

from inim.prime.native.models.partitions import Partition
from inim.prime.native.models.terminals import Terminal
from inim.prime.native.models.zones import Zone, ZoneTerminal
from inim.prime.native.operations.partitions.get_partition_labels import get_partition_labels
from inim.prime.native.operations.partitions.get_partition_statuses import get_partition_statuses
from inim.prime.native.wire import Protocol


async def initialize_partitions(
        protocol: Protocol,
        partition_zones: dict[int, set[Zone]],
        pin: str | None = None,
) -> dict[int, Partition]:
    partitions: dict[int, Partition] = {}

    partition_statuses, partition_labels = await asyncio.gather(
        get_partition_statuses(protocol, pin),
        get_partition_labels(protocol),
    )

    for partition_id, partition_status in partition_statuses.items():
        partitions[partition_id] = Partition(
            id = partition_id,
            label = partition_labels[partition_id],
            status = partition_status,
            zones = partition_zones.get(partition_id, set()),
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


def get_zones_by_partition(
    terminals: dict[int, Terminal],
) -> dict[int, set[Zone]]:
    partitions: defaultdict[int, set[Zone]] = defaultdict(set)

    for terminal in terminals.values():
        if not isinstance(terminal, ZoneTerminal):
            continue

        for zone in terminal.zones:
            for partition in zone.zone_setting.partitions:
                partitions[partition].add(zone)

    return dict(partitions)