from typing import Final

from inim.prime.native.utils import Interval

ZONE_TERMINAL_IDS_INTERVAL: Final[Interval] = Interval(0, 1004)
ZONE_IDS_INTERVAL: Final[Interval] = Interval(0, 2009)
ZONE_1_ID_OFFSET = 1005 # 2009 - 1004