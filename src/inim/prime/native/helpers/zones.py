import asyncio

from inim.prime.native.const import Encoding
from inim.prime.native.helpers.terminals import update_terminal_statuses_by_intervals, initialize_terminals
from inim.prime.native.models.terminals import Terminal, TerminalType
from inim.prime.native.models.zones import Zone, ZoneState, ZoneStatus, ZoneSetting, SingleZone, DoubleZone
from inim.prime.native.operations.zones.const import ZONE_TERMINAL_IDS_INTERVAL, ZONE_IDS_INTERVAL, ZONE_1_ID_OFFSET
from inim.prime.native.operations.zones.get_zone_labels import get_zone_labels
from inim.prime.native.operations.zones.get_zone_settings import get_zone_settings
from inim.prime.native.utils import Interval, decode_int
from inim.prime.native.wire import Protocol

'''
10 bytes
[4:5] Zone State (1 standby, 2 alarm)
[2:3] Exclusion Status (x08 not bypassed, x18 bypassed) (Not sure about other values) (maybe is a multiple flag value, so i consider only bit 4)
'''

#
#   Zone bypass decode
#
def _decode_zone_bypass_byte(
        byte: int,
) -> bool:
    return bool((byte >> 4) & 1)

def _decode_double_zone_bypass(
        raw_bytes: bytes,
) -> tuple[bool, bool]:
    zone_0 = _decode_zone_bypass_byte(raw_bytes[2])
    zone_1 = _decode_zone_bypass_byte(raw_bytes[6])
    return zone_0, zone_1

def _decode_single_zone_bypass(
        raw_bytes: bytes,
) -> bool:
    return _decode_zone_bypass_byte(raw_bytes[2])


#
#   Zone state decode
#
def _decode_zone_state(
        byte: int,
) -> ZoneState:
    try:
        return ZoneState(byte)
    except ValueError:
        return ZoneState.UNKNOWN

def _decode_double_zone_state(
        raw_bytes: bytes,
) -> tuple[ZoneState, ZoneState]:
    zone_0 = _decode_zone_state(raw_bytes[4])
    zone_1 = _decode_zone_state(raw_bytes[8])
    return zone_0, zone_1

def _decode_single_zone_state(
        raw_bytes: bytes,
) -> ZoneState:
    return _decode_zone_state(raw_bytes[4])




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
            state = _decode_single_zone_state(t.terminal_status.raw)
            bypass = _decode_single_zone_bypass(t.terminal_status.raw)

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

async def initialize_zones(
        protocol: Protocol,
        pin: str | None = None,
):
    zones: dict[int, Terminal] = {}

    terminals, zone_labels, zone_settings = await asyncio.gather(
        initialize_terminals(protocol, ZONE_TERMINAL_IDS_INTERVAL, pin),
        get_zone_labels(protocol, ZONE_IDS_INTERVAL),
        get_zone_settings(protocol, ZONE_IDS_INTERVAL),
    )

    for idx, terminal in terminals.items():
        if terminal.terminal_status is not None:
            if terminal.terminal_status.type == TerminalType.SINGLE_ZONE:
                zone_id = terminal.terminal_id

                state = _decode_single_zone_state(terminal.terminal_status.raw)
                bypass = _decode_single_zone_bypass(terminal.terminal_status.raw)
                zone_status = ZoneStatus(
                    state = state,
                    bypass=bypass,
                )

                zone = Zone(
                    zone_id = zone_id,
                    label = zone_labels[zone_id],
                    zone_status = zone_status,
                    zone_setting = zone_settings.get(zone_id),
                )
                single_zone = SingleZone.from_terminal(
                    terminal = terminal,
                    zone = zone,
                )
                zones[idx] = single_zone

            elif terminal.terminal_status.type == TerminalType.DOUBLE_ZONE:
                state = _decode_double_zone_state(terminal.terminal_status.raw)
                bypass = _decode_double_zone_bypass(terminal.terminal_status.raw)

                # Zone 0
                zone_0_id = terminal.terminal_id

                zone_0_status = ZoneStatus(
                    state = state[0],
                    bypass = bypass[0],
                )

                zone_0 = Zone(
                    zone_id = zone_0_id,
                    label = zone_labels[zone_0_id],
                    zone_status = zone_0_status,
                    zone_setting = zone_settings.get(zone_0_id),
                )


                # Zone 1
                zone_1_id = zone_0_id + ZONE_1_ID_OFFSET

                zone_1_status = ZoneStatus(
                    state = state[1],
                    bypass = bypass[1],
                )

                zone_1 = Zone(
                    zone_id = zone_1_id,
                    label = zone_labels[zone_1_id],
                    zone_status = zone_1_status,
                    zone_setting = zone_settings.get(zone_1_id),
                )

                double_zone = DoubleZone.from_terminal(
                    terminal = terminal,
                    zone_0 = zone_0,
                    zone_1 = zone_1,
                )
                zones[idx] = double_zone

    return zones


# async def get_zones_by_intervals(
#         protocol: Protocol,
#         terminal_intervals: list[Interval],
#         pin: str | None = None,
# ) -> dict[int, Zone]:
#     terminals = await get_terminals_by_intervals(protocol, terminal_intervals, pin)
#     zone_settings = await get_zone_settings_by_intervals(protocol, terminal_intervals)
#     return terminals_to_zones(terminals, zone_settings)



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
            state = _decode_single_zone_state(zone.terminal_status.raw)
            bypass = _decode_single_zone_bypass(zone.terminal_status.raw)

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