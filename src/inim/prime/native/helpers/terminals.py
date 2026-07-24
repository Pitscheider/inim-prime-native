import asyncio
from collections import defaultdict
from typing import TypeVar

from inim.prime.native.models.terminals import Terminal, TerminalStatus, TerminalState
from inim.prime.native.operations.terminals.get_terminal_labels import get_terminal_labels
from inim.prime.native.operations.terminals.get_terminal_statuses import get_terminal_statuses
from inim.prime.native.utils import Interval, make_intervals
from inim.prime.native.wire import Protocol

async def get_terminals_by_intervals(
        protocol: Protocol,
        intervals: list[Interval],
        pin: str | None = None,
) -> dict[int, Terminal]:

    terminal_labels, terminal_statuses = await asyncio.gather(
        get_terminal_labels_by_intervals(protocol, intervals),
        get_terminal_statuses_by_intervals(protocol, intervals, pin),
    )

    return {
        idx: Terminal(
            id = idx,
            label = label,
            terminal_status = terminal_statuses.get(idx),
        )
        for idx, label in terminal_labels.items()
    }


async def get_terminal_statuses_by_intervals(
    protocol: Protocol,
    intervals: list[Interval],
    pin: str | None = None,
) -> dict[int, TerminalStatus]:
    terminal_statuses: dict[int, TerminalStatus] = {}

    for interval in intervals:
        terminal_statuses |= await get_terminal_statuses(protocol, interval, pin)

    return terminal_statuses

async def get_terminal_labels_by_intervals(
        protocol: Protocol,
        intervals: list[Interval],
) -> dict[int, str]:
    terminal_labels: dict[int, str] = {}

    for interval in intervals:
        terminal_labels |= await get_terminal_labels(protocol, interval)

    return terminal_labels



async def get_terminals_intervals_by_state(
    protocol: Protocol,
    pin: str | None = None,
) -> dict[TerminalState, list[Interval]]:
    t_statuses = await get_terminal_statuses(protocol, pin=pin)

    ids_by_state: dict[TerminalState, list[int]] = defaultdict(list)

    for t_id, status in t_statuses.items():
        ids_by_state[status.state].append(t_id)

    return {
        state: make_intervals(ids)
        for state, ids in ids_by_state.items()
    }

T = TypeVar("T", bound=Terminal)

async def update_terminal_statuses_by_intervals(
    protocol: Protocol,
    terminals: dict[int, T],
    intervals: list[Interval],
    pin: str | None = None,
) -> dict[int, T]:
    terminal_statuses = await get_terminal_statuses_by_intervals(
        protocol, intervals, pin
    )

    for terminal in terminals.values():
        terminal.terminal_status = terminal_statuses.get(terminal.id)

    return terminals