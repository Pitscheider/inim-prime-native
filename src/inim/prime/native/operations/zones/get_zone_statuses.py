from inim.prime.native.models.zones import ZoneStatus
from inim.prime.native.operations.terminals.get_terminal_statuses import get_terminal_statuses
from inim.prime.native.operations.zones.const import ZONE_IDS_INTERVAL
from inim.prime.native.utils import Interval
from inim.prime.native.wire import Protocol


async def get_zone_statuses(
        protocol: Protocol,
        interval: Interval = ZONE_IDS_INTERVAL,
        pin: str | None = None,
) -> dict[int, ZoneStatus]:

    assert interval.end <= ZONE_IDS_INTERVAL.end

    get_terminal_statuses(protocol, interval, pin)

