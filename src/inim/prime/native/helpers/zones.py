from inim.prime.native.const import Encoding
from inim.prime.native.helpers.terminals import get_terminals_by_intervals, update_terminal_statuses_by_intervals
from inim.prime.native.models.terminals import TerminalStatus, Terminal
from inim.prime.native.models.zones import Zone, ZoneState, ZoneStatus
from inim.prime.native.operations.terminals.const import TERMINAL_LAYOUT, TerminalType
from inim.prime.native.utils import Interval, truncate_intervals, decode_int
from inim.prime.native.wire import Protocol

'''
10 bytes
[4:5] Zone State (1 standby, 2 alarm)
[2:3] Exclusion Status (x08 not bypassed, x18 bypassed) (Not sure about other values) (maybe is a multiple flag value, so i consider only bit 4)
'''

def get_zones_intervals(
        intervals: list[Interval],
) -> list[Interval]:
    return truncate_intervals(
        intervals,
        min_start = TERMINAL_LAYOUT[TerminalType.PANEL].start,
        max_end = TERMINAL_LAYOUT[TerminalType.EXPANSION].stop - 1,
    )

def _decode_zone_bypass(
        raw_bytes: bytes,
) -> bool:
    byte = decode_int(raw_bytes[2:3], Encoding.UINT8)
    return bool((byte >> 4) & 1)

def _decode_zone_state(
        raw_bytes: bytes,
) -> ZoneState | None:
    state_int = decode_int(raw_bytes[4:5], Encoding.UINT8)
    try:
        return ZoneState(state_int)
    except ValueError:
        return None

def terminals_to_zones(
        terminals: list[Terminal],
) -> list[Zone]:
    zones: list[Zone] = []

    for t in terminals:
        status = None
        if t.terminal_status is not None:
            state = _decode_zone_state(t.terminal_status.raw)
            bypass = _decode_zone_bypass(t.terminal_status.raw)

            status = ZoneStatus(
                state = state,
                bypass = bypass,
            )

        zones.append(Zone.from_terminal(t, status))

    return zones

async def get_zones_by_intervals(
        protocol: Protocol,
        intervals: list[Interval],
        pin: str | None = None,
) -> list[Zone]:
    terminals = await get_terminals_by_intervals(protocol, intervals, pin)
    return terminals_to_zones(terminals)


async def update_zone_statuses_by_intervals(
        protocol: Protocol,
        zones: list[Zone],
        intervals: list[Interval],
        pin: str | None = None,
) -> list[Zone]:
    updated_terminals = await update_terminal_statuses_by_intervals(protocol, zones, intervals, pin)
    updated_zones = terminals_to_zones(updated_terminals)
    return updated_zones