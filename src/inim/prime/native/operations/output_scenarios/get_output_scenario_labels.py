from inim.prime.native.const import Address
from inim.prime.native.operations.base import get_labels
from inim.prime.native.operations.output_scenarios.const import LAST_OUTPUT_SCENARIO_ID
from inim.prime.native.utils import Interval
from inim.prime.native.wire.protocol import Protocol


async def get_output_scenario_labels(
        protocol: Protocol,
        interval: Interval = Interval(0, LAST_OUTPUT_SCENARIO_ID),
) -> dict[int, str]:
    return await get_labels(protocol, interval, Address.OUTPUT_SCENARIO_LABELS)