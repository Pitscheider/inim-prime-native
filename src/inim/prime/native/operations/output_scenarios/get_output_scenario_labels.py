from inim.prime.native.firmware import FirmwareProfile
from inim.prime.native.operations.base import get_labels
from inim.prime.native.operations.output_scenarios.const import LAST_OUTPUT_SCENARIO_ID
from inim.prime.native.utils import Interval
from inim.prime.native.wire.protocol import Protocol


async def get_output_scenario_labels(
        protocol: Protocol,
        profile: FirmwareProfile,
        interval: Interval = Interval(0, LAST_OUTPUT_SCENARIO_ID),
) -> dict[int, str]:
    address = profile.memory.output_scenario_labels
    if address is None:
        raise NotImplementedError(
            f"Output scenario labels address is unknown for firmware {profile.name}."
        )
    return await get_labels(protocol, interval, address)