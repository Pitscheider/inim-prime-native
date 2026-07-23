from inim.prime.native.operations.partitions.const import PARTITIONS_MAX_NUMBER


def validate_partition_id(idx: int):
    if idx < 0 or idx >= PARTITIONS_MAX_NUMBER:
        raise IndexError(f'Partition {idx} out of range')