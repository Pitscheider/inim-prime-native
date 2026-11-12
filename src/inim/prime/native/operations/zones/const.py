from typing import Final

from inim.prime.native.utils import Interval

ZONE_TERMINAL_IDS_INTERVAL: Final[Interval] = Interval(0, 1504)
ZONE_IDS_INTERVAL: Final[Interval] = Interval(0, 3009)
ZONE_1_ID_OFFSET = ZONE_IDS_INTERVAL.end - ZONE_TERMINAL_IDS_INTERVAL.end