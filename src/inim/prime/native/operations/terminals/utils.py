from inim.prime.native.operations.terminals.const import LAST_TERMINAL_ID
from inim.prime.native.utils import Interval


def validate_terminals_interval(interval: Interval):
    if interval.start < 0:
        raise ValueError('interval.start must be >= 0')
    if interval.end < interval.start:
        raise ValueError('interval.end must be >= interval.start')
    if interval.end > LAST_TERMINAL_ID:
        raise ValueError('interval.end must be <= LAST_TERMINAL_ID')