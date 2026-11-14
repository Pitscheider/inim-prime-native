from inim.prime.native.firmware import FirmwareProfile
from inim.prime.native.operations.arming_scenarios.const import LAST_ARMING_SCENARIO_ID
from inim.prime.native.operations.base import get_labels
from inim.prime.native.utils import Interval
from inim.prime.native.wire.protocol import Protocol


async def get_arming_scenario_labels(
        protocol: Protocol,
        profile: FirmwareProfile,
        interval: Interval = Interval(0, LAST_ARMING_SCENARIO_ID),
) -> dict[int, str]:
    return await get_labels(protocol, interval, profile.memory.arming_scenario_labels)