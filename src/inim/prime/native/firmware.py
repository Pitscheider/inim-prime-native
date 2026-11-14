from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from inim.prime.native.utils import Interval


class UnsupportedFirmwareError(RuntimeError):
    """Raised when no profile matches the firmware reported by the panel."""


@dataclass(frozen = True, slots = True)
class MemoryMap:
    partition_labels: int
    zone_labels: int
    zone_settings: int
    output_labels: int
    arming_scenario_labels: int
    output_scenario_labels: int | None  # None = not located yet on this firmware


@dataclass(frozen = True, slots = True)
class FirmwareProfile:
    name: str
    major_versions: frozenset[int]
    memory: MemoryMap
    terminal_ids: Interval
    zone_terminal_ids: Interval
    zone_ids: Interval
    output_terminal_ids: Interval

    @property
    def zone_1_id_offset(self) -> int:
        """Offset between a double-zone terminal ID and the ID of its second zone."""
        return self.zone_ids.end - self.zone_terminal_ids.end


FIRMWARE_4: Final[FirmwareProfile] = FirmwareProfile(
    name = "4.x",
    major_versions = frozenset({4}),
    memory = MemoryMap(
        partition_labels       = 0x14030D20,
        zone_labels            = 0x14030F00,
        zone_settings          = 0x14073414,
        output_labels          = 0x1403DEB0,
        arming_scenario_labels = 0x1403D8E0,
        output_scenario_labels = 0x1403F4C0,
    ),
    terminal_ids        = Interval(0, 1009),
    zone_terminal_ids   = Interval(0, 1004),
    zone_ids            = Interval(0, 2009),
    output_terminal_ids = Interval(1005, 1009),
)

FIRMWARE_5: Final[FirmwareProfile] = FirmwareProfile(
    name = "5.x",
    major_versions = frozenset({5}),
    memory = MemoryMap(
        partition_labels       = 0x14030D20,
        zone_labels            = 0x14030F00,
        zone_settings          = 0x1408B920,
        output_labels          = 0x14041D30,
        arming_scenario_labels = 0x14041760,
        output_scenario_labels = None,
    ),
    terminal_ids        = Interval(0, 1509),
    zone_terminal_ids   = Interval(0, 1504),
    zone_ids            = Interval(0, 3009),
    output_terminal_ids = Interval(1505, 1509),
)

PROFILES: Final[tuple[FirmwareProfile, ...]] = (FIRMWARE_4, FIRMWARE_5)
LATEST: Final[FirmwareProfile] = FIRMWARE_5


def parse_major(firmware: str) -> int:
    """'5.00' -> 5, '4.07' -> 4."""
    head = str(firmware).strip().split(".", 1)[0]
    digits = "".join(c for c in head if c.isdigit())
    if not digits:
        raise ValueError(f"Cannot parse firmware version: {firmware!r}")
    return int(digits)


def select_profile(firmware: str) -> FirmwareProfile:
    """Returns the profile matching a firmware string as reported by get_panel_info()."""
    major = parse_major(firmware)
    for profile in PROFILES:
        if major in profile.major_versions:
            return profile
    raise UnsupportedFirmwareError(
        f"Firmware {firmware!r} is not supported "
        f"(known: {', '.join(p.name for p in PROFILES)}). "
        "Pass a profile explicitly to Client(firmware=...) to force one."
    )