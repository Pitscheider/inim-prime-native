import asyncio
from typing import FrozenSet

from inim.prime.native.models.terminals import Terminal, TerminalStatus, TerminalSetting
from inim.prime.native.operations.terminals.get_terminal_labels import get_terminal_labels_by_interval
from inim.prime.native.operations.terminals.get_terminal_settings import get_terminal_settings_by_interval
from inim.prime.native.operations.terminals.get_terminal_statuses import get_terminal_statuses_by_interval
from inim.prime.native.utils import Interval
from inim.prime.native.wire import Protocol

async def get_terminals_by_intervals(
        protocol: Protocol,
        intervals: list[Interval],
        pin: str | None = None,
) -> list[Terminal]:
    terminals: list[Terminal] = []

    terminal_labels, terminal_statuses, terminal_settings = await asyncio.gather(
        get_terminal_labels_by_intervals(protocol, intervals),
        get_terminal_statuses_by_intervals(protocol, intervals, pin),
        get_terminal_settings_by_intervals(protocol, intervals),
    )

    for idx, t_label in terminal_labels.items():
        t_status = terminal_statuses.get(idx)
        t_setting = terminal_settings.get(idx)
        terminals.append(Terminal(
            id = idx,
            label = t_label,
            terminal_status = t_status,
            setting = t_setting
        ))

    return terminals

async def get_terminal_statuses_by_intervals(
    protocol: Protocol,
    intervals: list[Interval],
    pin: str | None = None,
) -> dict[int, TerminalStatus]:
    terminal_statuses: dict[int, TerminalStatus] = {}

    for interval in intervals:
        terminal_statuses |= await get_terminal_statuses_by_interval(protocol, interval, pin)

    return terminal_statuses

async def get_terminal_labels_by_intervals(
        protocol: Protocol,
        intervals: list[Interval],
) -> dict[int, str]:
    terminal_labels: dict[int, str] = {}

    for interval in intervals:
        terminal_labels |= await get_terminal_labels_by_interval(protocol, interval)

    return terminal_labels

async def get_terminal_settings_by_intervals(
        protocol: Protocol,
        intervals: list[Interval],
) -> dict[int, TerminalSetting]:
    terminal_settings: dict[int, TerminalSetting] = {}

    for interval in intervals:
        terminal_settings |= await get_terminal_settings_by_interval(protocol, interval)

    return terminal_settings

async def get_active_terminal_intervals(
    protocol: Protocol,
    pin: str | None = None,
) -> list[Interval]:


    t_statuses = await get_terminal_statuses_by_interval(protocol,  pin = pin)

    intervals: list[Interval] = []

    start: int | None = None
    end: int

    for t_id, status in t_statuses.items():
        if not status.active:
            continue

        if start is None:
            start = end = t_id
        elif t_id == end + 1:
            end = t_id
        else:
            intervals.append(Interval(start, end))
            start = end = t_id

    if start is not None:
        intervals.append(Interval(start, end))

    return intervals

async def update_terminal_statuses_by_intervals(
    protocol: Protocol,
    terminals: list[Terminal],
    intervals: list[Interval],
    pin: str | None = None,
) -> list[Terminal]:
    terminal_statuses = await get_terminal_statuses_by_intervals(protocol, intervals, pin)

    for t in terminals:
        t.terminal_status = terminal_statuses.get(t.id)

    return terminals