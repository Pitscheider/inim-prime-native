import asyncio

from inim.prime.native.models.outputs import Output
from inim.prime.native.models.terminals import Terminal, TerminalStatus, TerminalType
from inim.prime.native.models.zones import SingleZone, DoubleZone
from inim.prime.native.operations.outputs.get_output_labels import get_output_labels
from inim.prime.native.operations.terminals.get_terminal_statuses import get_terminal_statuses
from inim.prime.native.operations.zones.const import ZONE_1_ID_OFFSET
from inim.prime.native.operations.zones.get_zone_labels import get_zone_labels
from inim.prime.native.operations.zones.get_zone_settings import get_zone_settings
from inim.prime.native.utils import Interval
from inim.prime.native.wire.protocol import Protocol


async def get_terminal_statuses_by_intervals(
    protocol: Protocol,
    intervals: list[Interval],
    pin: str | None = None,
) -> dict[int, TerminalStatus]:
    terminal_statuses: dict[int, TerminalStatus] = {}

    results = await asyncio.gather(
        *(get_terminal_statuses(protocol, interval, pin) for interval in intervals)
    )

    for result in results:
        terminal_statuses |= result

    return terminal_statuses


async def initialize_terminals(
        protocol: Protocol,
        pin: str | None = None,
) -> dict[int, Terminal]:
    terminals: dict[int, Terminal] = {}

    terminal_statuses, zone_labels, zone_settings, output_labels = await asyncio.gather(
        get_terminal_statuses(protocol, pin = pin),
        get_zone_labels(protocol),
        get_zone_settings(protocol),
        get_output_labels(protocol)
    )

    for terminal_id, terminal_status in terminal_statuses.items():
        if terminal_status.type == TerminalType.SINGLE_ZONE:
            zone_id = terminal_id

            terminals[terminal_id] = SingleZone.decode(
                terminal_id = terminal_id,
                terminal_status = terminal_status,
                zone_id = zone_id,
                zone_label = zone_labels[zone_id],
                zone_setting = zone_settings[zone_id],
            )

        elif terminal_status.type == TerminalType.DOUBLE_ZONE:
            zone_0_id = terminal_id
            zone_1_id = terminal_id + ZONE_1_ID_OFFSET

            terminals[terminal_id] = DoubleZone.decode(
                terminal_id = terminal_id,
                terminal_status = terminal_status,
                zone_0_id = zone_0_id,
                zone_0_label = zone_labels[zone_0_id],
                zone_0_setting = zone_settings[zone_0_id],
                zone_1_id = zone_1_id,
                zone_1_label = zone_labels[zone_1_id],
                zone_1_setting = zone_settings[zone_1_id],
            )

        elif terminal_status.type == TerminalType.OUTPUT:
            terminals[terminal_id] = Output.decode(
                terminal_id = terminal_id,
                terminal_status = terminal_status,
                label = output_labels[terminal_id],
            )


    return terminals


async def update_terminal_statuses(
    protocol: Protocol,
    terminals: dict[int, Terminal],
    intervals: list[Interval],
    pin: str | None = None,
) -> dict[int, Terminal]:
    terminal_statuses = await get_terminal_statuses_by_intervals(
        protocol, intervals, pin
    )

    for terminal in terminals.values():
        terminal.update_status(terminal_statuses.get(terminal.terminal_id))

    return terminals
