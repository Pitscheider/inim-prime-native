from inim.prime.native.operations.zones.const import ZONE_1_ID_OFFSET


def zone_to_terminal(zone_id: int) -> tuple[int, int]:
    """
    Returns the terminal holding a zone and its half.
    :return: (terminal, half), half 0 = A (zone_id), 1 = B (terminal + ZONE_1_ID_OFFSET).
    """
    if zone_id >= ZONE_1_ID_OFFSET:
        return zone_id - ZONE_1_ID_OFFSET, 1
    return zone_id, 0