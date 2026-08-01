from inim.prime.native.const import Memory, Address
from inim.prime.native.operations.arming_scenarios.const import LAST_ARMING_SCENARIO_ID
from inim.prime.native.operations.base import get_labels
from inim.prime.native.utils import Interval
from inim.prime.native.wire.protocol import Protocol


async def get_arming_scenario_labels(
        protocol: Protocol,
        interval: Interval = Interval(0, LAST_ARMING_SCENARIO_ID),
) -> dict[int, str]:
    return await get_labels(protocol, interval, Address.ARMING_SCENARIO_LABELS)