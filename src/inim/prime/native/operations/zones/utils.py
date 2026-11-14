def zone_to_terminal(zone_id: int, zone_1_id_offset: int) -> tuple[int, int]:
    """
    Returns the terminal holding a zone and its half.
    :return: (terminal, half), half 0 = A (zone_id), 1 = B (terminal + zone_1_id_offset).
    """
    if zone_id >= zone_1_id_offset:
        return zone_id - zone_1_id_offset, 1
    return zone_id, 0