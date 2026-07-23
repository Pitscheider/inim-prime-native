from inim.prime.native.const import Memory, Address
from inim.prime.native.operations.partitions.const import PARTITIONS_MAX_NUMBER
from inim.prime.native.wire import Protocol


async def get_partition_labels(protocol: Protocol) -> dict[int, str]:

    response = await protocol.read_memory(Address.GET_PARTITION_LABELS, PARTITIONS_MAX_NUMBER * Memory.LABEL_SIZE)

    partition_labels: dict[int, str] = {}

    for index in range(PARTITIONS_MAX_NUMBER):
        partition_labels_bytes = response[index * Memory.LABEL_SIZE:(index + 1) * Memory.LABEL_SIZE]

        if partition_labels_bytes != bytes(Memory.LABEL_SIZE):
            partition_label = partition_labels_bytes.decode("ascii").rstrip()
            partition_labels[index] = partition_label

    return partition_labels