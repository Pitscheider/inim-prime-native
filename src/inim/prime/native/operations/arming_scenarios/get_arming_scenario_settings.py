from typing import Final

from inim.prime.native.firmware import FirmwareProfile
from inim.prime.native.models.arming_scenarios import ArmingScenarioSetting
from inim.prime.native.models.partitions import ArmingStatus
from inim.prime.native.operations.arming_scenarios.const import LAST_ARMING_SCENARIO_ID
from inim.prime.native.utils import Interval
from inim.prime.native.wire.protocol import Protocol
from operations.partitions.const import PARTITIONS_NUMBER

### Constants
ARMING_SCENARIO_SETTING_SIZE: Final[int] = 19
# One nibble per partition
ARMING_SCENARIO_TARGETS_SIZE: Final[int] = (PARTITIONS_NUMBER + 1) // 2
UNCHANGED_VALUE: Final[int] = 0

'''
It is possible to read Arming Scenario Settings from the panel's Memory from address
profile.memory.arming_scenario_settings.
Each arming scenario uses 19 bytes
[0:15]  Target arming status per partition, one nibble each:
        byte i -> partition 2i (low nibble), partition 2i+1 (high nibble)
        0 = unchanged ("-" in Prime/STUDIO): applying the scenario leaves the partition
            as it is, and the partition does not affect whether the scenario is active
        otherwise an ArmingStatus value (1 total, 2 partial, 3 instant, 4 disarmed)
[15:19] Unknown
'''

def _decode_partitions(raw_bytes: bytes) -> tuple[ArmingStatus | None, ...]:
    """
    :raises ValueError: If a nibble is not 0 or an ArmingStatus value,
                        which means the memory read is not an arming scenario table.
    """
    partitions: list[ArmingStatus | None] = []

    for byte in raw_bytes[:ARMING_SCENARIO_TARGETS_SIZE]:
        for nibble in (byte & 0x0F, byte >> 4):
            if nibble == UNCHANGED_VALUE:
                partitions.append(None)
                continue
            try:
                partitions.append(ArmingStatus(nibble))
            except ValueError:
                raise ValueError(
                    f"Invalid target value {nibble} for partition {len(partitions)}"
                ) from None

    return tuple(partitions[:PARTITIONS_NUMBER])

async def get_arming_scenario_settings(
        protocol: Protocol,
        profile: FirmwareProfile,
        interval: Interval = Interval(0, LAST_ARMING_SCENARIO_ID),
) -> dict[int, ArmingScenarioSetting]:
    arming_scenarios_number = interval.end - interval.start + 1

    size = ARMING_SCENARIO_SETTING_SIZE * arming_scenarios_number

    response = await protocol.read_memory(
        start_address = profile.memory.arming_scenario_settings + interval.start * ARMING_SCENARIO_SETTING_SIZE,
        bytes_to_read = size,
    )

    arming_scenarios: dict[int, ArmingScenarioSetting] = {}

    for idx, offset in enumerate(
            range(0, size, ARMING_SCENARIO_SETTING_SIZE),
            start = interval.start,
    ):
        raw_bytes = response[offset:offset + ARMING_SCENARIO_SETTING_SIZE]
        try:
            partitions = _decode_partitions(raw_bytes)
        except ValueError as err:
            raise ValueError(f"Arming scenario {idx}: {err} (raw: {raw_bytes.hex(' ')})") from err
        arming_scenarios[idx] = ArmingScenarioSetting(raw_bytes, partitions)
    return arming_scenarios