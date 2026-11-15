import asyncio

from inim.prime.native.firmware import FirmwareProfile
from inim.prime.native.models.arming_scenarios import ArmingScenario
from inim.prime.native.operations.arming_scenarios.get_arming_scenario_labels import get_arming_scenario_labels
from inim.prime.native.operations.arming_scenarios.get_arming_scenario_settings import get_arming_scenario_settings
from inim.prime.native.wire.protocol import Protocol


async def initialize_arming_scenarios(
        protocol: Protocol,
        profile: FirmwareProfile,
) -> dict[int, ArmingScenario]:
    """Returns the defined arming scenarios (at least one target), keyed by id."""
    arming_scenarios: dict[int, ArmingScenario] = {}

    arming_scenario_settings, arming_scenario_labels = await asyncio.gather(
        get_arming_scenario_settings(protocol, profile),
        get_arming_scenario_labels(protocol, profile),
    )

    for arming_scenario_id, arming_scenario_setting in arming_scenario_settings.items():
        if not arming_scenario_setting.is_defined:
            continue

        arming_scenarios[arming_scenario_id] = ArmingScenario(
            _arming_scenario_id = arming_scenario_id,
            _label = arming_scenario_labels[arming_scenario_id],
            _arming_scenario_setting = arming_scenario_setting,
        )

    return arming_scenarios