from typing import Final

from inim.prime.native.utils import Interval

PARTITION_IDS_INTERVAL: Final[Interval] = Interval(0, 29)
PARTITIONS_NUMBER: Final[int] = PARTITION_IDS_INTERVAL.size