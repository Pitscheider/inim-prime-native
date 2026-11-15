from collections.abc import Mapping
from dataclasses import dataclass

from inim.prime.native.models.partitions import ArmingStatus, Partition

@dataclass(frozen = True)
class ArmingScenarioSetting:
    ### Attributes
    raw: bytes
    # Target arming status of every partition, indexed by partition ID.
    # None = unchanged ("-" in Prime/STUDIO).
    partitions: tuple[ArmingStatus | None, ...]


    ### Properties
    @property
    def targets(self) -> dict[int, ArmingStatus]:
        """:return: Partitions the scenario changes, mapped to their target arming status."""
        return {
            partition_id: arming_status
            for partition_id, arming_status in enumerate(self.partitions)
            if arming_status is not None
        }

    @property
    def is_defined(self) -> bool:
        """True if the scenario changes at least one partition."""
        return any(arming_status is not None for arming_status in self.partitions)


@dataclass
class ArmingScenario:
    ### Attributes
    _arming_scenario_id: int
    _label: str
    _arming_scenario_setting: ArmingScenarioSetting


    ### Properties
    @property
    def arming_scenario_id(self) -> int:
        return self._arming_scenario_id

    @property
    def label(self) -> str:
        return self._label

    @property
    def arming_scenario_setting(self) -> ArmingScenarioSetting:
        return self._arming_scenario_setting


    ### Special methods
    def __hash__(self) -> int:
        return hash(self.arming_scenario_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ArmingScenario):
            return NotImplemented

        return self.arming_scenario_id == other.arming_scenario_id

    def __str__(self) -> str:
        return self.to_string_partition_labels({})

    ### Methods
    def to_string_partition_labels(
            self,
            partition_labels: dict[int, str],
    ) -> str:
        targets = ", ".join(
            f"{partition_labels.get(partition_id, f'ID={partition_id}')}: {arming_status.name}"
            for partition_id, arming_status in self.arming_scenario_setting.targets.items()
        )
        return (
            f"ID={self.arming_scenario_id} - {self.label}"
            f"\n\tTargets: {targets}"
            f"\n\tRaw setting: {self.arming_scenario_setting.raw.hex(' ')}"
        )

    ### Methods
    def is_active(
            self,
            partitions: Mapping[int, Partition],
    ) -> bool:
        """True if every targeted partition is currently in its target arming status.
        Unchanged partitions are ignored, so several scenarios can be active at once
        (the keypad only shows the last applied one)."""
        targets = self.arming_scenario_setting.targets
        if not targets:
            return False

        for partition_id, target in targets.items():
            partition = partitions.get(partition_id)
            if partition is None or partition.status is None:
                return False
            if partition.status.arming_status is not target:
                return False

        return True