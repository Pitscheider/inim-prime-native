from __future__ import annotations

import struct
from dataclasses import dataclass
from functools import singledispatch

from inim.prime.native.const import CRC16_TABLE, Encoding


### Next Slice
@singledispatch
def next_slice(s: int | slice, size: int | None) -> slice:
    ...

@next_slice.register
def _(s: int, size: int | None) -> slice:
    start = s
    stop = start + size if size is not None else None
    return slice(start, stop)

@next_slice.register
def _(s: slice, size: int | None) -> slice:
    if s.stop is None:
        raise ValueError("s.stop must be an integer")
    start = s.stop
    stop = start + size if size is not None else None
    return slice(start, stop)

### Previous Slice
def previous_slice(s: slice | None, size: int | None) -> slice:
    stop: int | None
    if s is None:
        stop = None
    else:
        if s.start is None:
            raise ValueError("s.start must be an integer")
        stop = s.start
    if size is None:
        start = 0
    else:
        start = stop - size if stop is not None else -size
    return slice(start, stop)

def slice_size(s: slice) -> int:
    return s.stop - s.start

def decode_int(value: bytes, encoding: Encoding) -> int:
    return struct.unpack(encoding, value)[0]

def encode_int(value: int, encoding: Encoding) -> bytes:
    return struct.pack(encoding, value)

def round_up_to_block(
        n: int,
        block: int,
) -> int:
    """
    Rounds up a number to the nearest multiple of the specified block that is greater or equal than it.
    :param n:       The number to round up.
    :param block:   Value of the multiplier used to round up the number.
    :return:        The rounded up number.
    """
    return ((n + block - 1) // block) * block


def crc16_arc(
        data: bytes | bytearray,
) -> int:
    """
    Computes CRC-16/ARC checksum over data.
    :param data:   The data to compute CRC-16/ARC checksum over.
    :return:       The computed CRC-16/ARC checksum as a 16-bit integer (0–65535).
    """
    # Zero-initialised CRC value
    crc = 0

    for byte in data:
        # XOR the incoming byte with the low 8 bits of the running CRC
        # to produce a table index in range 0–255
        table_index = (crc ^ byte) & 0xFF

        # Retrieves the precomputed CRC value using the obtained table_index.
        table_value = CRC16_TABLE[table_index]

        # Takes the 8 most significant bits of CRC (the high byte)
        high_byte = (crc >> 8) & 0xFF

        # XOR the CRC high_byte with table_value
        crc = high_byte ^ table_value

    return crc & 0xFFFF

@dataclass(frozen=True, slots=True)
class Interval:
    start: int
    end: int  # inclusive

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Interval:
    start: int
    end: int  # inclusive

    @property
    def size(self) -> int:
        return self.end - self.start + 1

    @property
    def end_exclusive(self) -> int:
        return self.end + 1

def validate_interval(interval: Interval, bounds: Interval):
    if interval.start < bounds.start:
        raise ValueError(f"{interval.start} must be >= {bounds.start}")
    if interval.end < interval.start:
        raise ValueError(f"{interval.end} must be >= {interval.start}")
    if interval.end > bounds.end:
        raise ValueError(f"{interval.end} must be <= {bounds.end}")

def truncate_interval(
    interval: Interval,
    min_start: int,
    max_end: int,
) -> Interval | None:
    start = max(interval.start, min_start)
    end = min(interval.end, max_end)

    if start <= end:  # still contains at least one value
        return Interval(start, end)
    return None


def truncate_intervals(
    intervals: list[Interval],
    min_start: int,
    max_end: int,
) -> list[Interval]:
    result = []

    for interval in intervals:
        t_interval = truncate_interval(interval, min_start, max_end)

        if t_interval is not None:  # still contains at least one value
            result.append(t_interval)

    return result

def make_intervals(values: list[int]) -> list[Interval]:
    if not values:
        return []

    intervals = []
    start = end = values[0]

    for value in values[1:]:
        if value == end + 1:
            end = value
        else:
            intervals.append(Interval(start, end))
            start = end = value

    intervals.append(Interval(start, end))
    return intervals
