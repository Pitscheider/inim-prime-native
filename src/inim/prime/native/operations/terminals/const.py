from enum import StrEnum, auto
from typing import Final

from inim.prime.native.utils import Interval


# class TerminalType(StrEnum):
#     PANEL = auto()
#     EXPANSION = auto()
#     KEYPAD = auto()
#     TEMPERATURE_PROBE = auto()
#     ROLLER_BLINDS = auto()
#     PROXIMITY_KEY_READER = auto()
#     BUS_SENSOR = auto()
#     VIDEO_SENSOR = auto()
#     POWER_STATION = auto()
#     FOG_MACHINE = auto()
#     VIRTUAL = auto()
#     OUTPUT = auto()
#
# TERMINALS_MAX_NUMBER: Final[dict[TerminalType, int]] = {
#     TerminalType.PANEL: 10,
#     TerminalType.EXPANSION: 100 * 5,
#     TerminalType.KEYPAD: 30 * 2,
#     TerminalType.TEMPERATURE_PROBE: 15,
#     TerminalType.ROLLER_BLINDS: 30 * 4,
#     TerminalType.PROXIMITY_KEY_READER: 60,
#     TerminalType.BUS_SENSOR: 180,
#     TerminalType.VIDEO_SENSOR: 10,
#     TerminalType.POWER_STATION: 10 * 2,
#     TerminalType.FOG_MACHINE: 10,
#     TerminalType.VIRTUAL: 20,
#     TerminalType.OUTPUT: 5,
# }
#
# def _build_terminal_layout() -> dict[TerminalType, slice]:
#     layout: dict[TerminalType, slice] = {}
#
#     previous: TerminalType | None = None
#     for t in TerminalType:
#         layout[t] = next_slice(
#             layout[previous] if previous is not None else 0,
#             TERMINALS_MAX_NUMBER[t],
#         )
#         previous = t
#     return layout
#
# LAST_TERMINAL_ID: Final[int] = sum(TERMINALS_MAX_NUMBER.values()) - 1
#
# TERMINAL_LAYOUT: Final[dict[TerminalType, slice]] = _build_terminal_layout()


TERMINAL_IDS_INTERVAL: Final[Interval] = Interval(0, 1009)