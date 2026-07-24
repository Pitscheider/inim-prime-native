from inim.prime.native.const import Encoding
from inim.prime.native.helpers.terminals import get_terminals_by_intervals, update_terminal_statuses_by_intervals
from inim.prime.native.models.terminals import Terminal
from inim.prime.native.models.zones import Zone, ZoneState, ZoneStatus, ZoneSetting
from inim.prime.native.operations.zones.get_zone_settings import get_zone_settings
from inim.prime.native.utils import Interval, decode_int
from inim.prime.native.wire import Protocol

'''
10 bytes
[4:5] Zone State (1 standby, 2 alarm)
[2:3] Exclusion Status (x08 not bypassed, x18 bypassed) (Not sure about other values) (maybe is a multiple flag value, so i consider only bit 4)
'''

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

def get_partition_ids_from_zones(
        zones: dict[int, Zone],
) -> set[int]:
    return set().union(
        *(zone.zone_setting.partitions for zone in zones.values()
          if zone.zone_setting is not None)
    )

def terminals_to_zones(
    terminals: dict[int, Terminal],
    zone_settings: dict[int, ZoneSetting],
) -> dict[int, Zone]:
    zones: dict[int, Zone] = {}

    for terminal_id, t in terminals.items():
        zone_status = None

        if t.terminal_status is not None:
            state = _decode_zone_state(t.terminal_status.raw)
            bypass = _decode_zone_bypass(t.terminal_status.raw)

            zone_status = ZoneStatus(
                state=state,
                bypass=bypass,
            )

        zones[terminal_id] = Zone.from_terminal(
            terminal = t,
            zone_status = zone_status,
            zone_setting = zone_settings.get(terminal_id),
        )

    return zones

async def get_zones_by_intervals(
        protocol: Protocol,
        intervals: list[Interval],
        pin: str | None = None,
) -> dict[int, Zone]:
    terminals = await get_terminals_by_intervals(protocol, intervals, pin)
    zone_settings = await get_zone_settings_by_intervals(protocol, intervals)
    return terminals_to_zones(terminals, zone_settings)



async def update_zone_statuses_by_intervals(
        protocol: Protocol,
        zones: dict[int, Zone],
        intervals: list[Interval],
        pin: str | None = None,
) -> dict[int, Zone]:
    zones = await update_terminal_statuses_by_intervals(protocol, zones, intervals, pin)
    for zone in zones.values():
        zone_status = None

        if zone.terminal_status is not None:
            state = _decode_zone_state(zone.terminal_status.raw)
            bypass = _decode_zone_bypass(zone.terminal_status.raw)

            zone_status = ZoneStatus(
                state = state,
                bypass = bypass,
            )
        zone.zone_status = zone_status
    return zones


async def get_zone_settings_by_intervals(
        protocol: Protocol,
        intervals: list[Interval],
) -> dict[int, ZoneSetting]:
    zone_settings: dict[int, ZoneSetting] = {}

    for interval in intervals:
        zone_settings |= await get_zone_settings(protocol, interval)

    return zone_settings