from __future__ import annotations

import asyncio
import logging
from types import MappingProxyType
from typing import Self

from inim.prime.native.const import Panel
from inim.prime.native.helpers.partitions import (
    get_zone_ids_by_partition,
    initialize_partitions,
    update_partition_statuses,
)
from inim.prime.native.helpers.terminals import (
    initialize_terminals,
    update_terminal_statuses,
)
from inim.prime.native.models.outputs import Output
from inim.prime.native.models.partitions import ArmingStatus, Partition
from inim.prime.native.models.terminals import Terminal
from inim.prime.native.models.zones import Zone, ZoneTerminal, DoubleZone, SingleZone
from inim.prime.native.operations.outputs.set_output_status import set_output_status
from inim.prime.native.operations.panel.get_panel_info import get_panel_info
from inim.prime.native.operations.partitions.reset_partition_alarm_memories import reset_partition_memories
from inim.prime.native.operations.partitions.set_partition_arming_statuses import set_partition_arming_statuses
from inim.prime.native.operations.zones.set_zone_bypass import set_zone_bypass
from inim.prime.native.utils import Interval
from inim.prime.native.wire.protocol import Protocol
from inim.prime.native.wire.transport import Transport


class NotInitializedError(RuntimeError):
    """Raised when a client operation requires initialise() to have been called first."""


class Client:
    """
    High-level, stateful client for an INIM Prime alarm panel.

    Wraps the low-level :class:`Protocol` wire engine together with the
    initialisation / update helpers and the individual command operations
    of the ``inim.prime.native`` package, exposing a single object that:

    * owns the TCP connection lifecycle,
    * discovers terminals (zones, double-zones, outputs) and partitions,
    * refreshes their status on demand,
    * sends arm/disarm, zone bypass, output and alarm-memory-reset commands.

    Instances are meant to back something like a Home Assistant integration:
    create one ``Client`` per panel, ``connect()`` + ``initialise()`` it once
    (e.g. in a config entry setup), then let a polling coordinator call
    ``update_status()`` and the various command methods.

    Not thread-safe across event loops, but safe to call concurrently from
    coroutines on the same loop: every method that talks to the panel is
    serialised through an internal ``asyncio.Lock`` since the wire protocol
    is a single stateful TCP connection.
    """

    __slots__ = (
        "_protocol",
        "_pin",
        "_logger",
        "_lock",
        "_terminals",
        "_terminal_intervals",
        "_zone_to_terminal",
        "_zones",
        "_outputs",
        "_single_zones",
        "_double_zones",
        "_partitions",
        "_serial_number",
        "_firmware",
        "_model",
        "_initialized",
    )

    ### Constructors
    def __init__(
            self,
            host: str,
            password: str,
            use_outer_frame: bool,
            port: int = Panel.DEFAULT_PORT,
            pin: str | None = None,
            logger: logging.Logger | None = None,
            connect_timeout: float = Transport.DEFAULT_CONNECT_TIMEOUT,
            receive_timeout: float = Transport.DEFAULT_RECEIVE_TIMEOUT,
    ) -> None:
        """
        Creates the client. No TCP connection is made here, call connect()
        (or use the client as an async context manager) to establish one.

        :param host:            IP address or hostname of the panel.
        :param password:        UTF-8 password string, 1-16 characters, used to derive
                                the AES-128-CBC key/IV for the wire protocol.
        :param use_outer_frame: Whether the panel expects frames wrapped in an outer frame.
                                Set True if using PrimeLAN card, False otherwise
        :param port:            TCP port of the panel. Defaults to Panel.DEFAULT_PORT.
        :param pin:             Default user PIN used for commands that require one
                                (arming, bypass, output control, alarm reset, status reads
                                on some panels) when no per-call PIN is supplied.
        :param logger:          Optional logger for debug and error messages.
        :param connect_timeout: Seconds before connect() gives up.
        :param receive_timeout: Seconds before a pending reception raises TimeoutError.
        """
        self._protocol = Protocol(
            host = host,
            password = password,
            port = port,
            use_outer_frame = use_outer_frame,
            logger = logger,
            connect_timeout = connect_timeout,
            receive_timeout = receive_timeout,
        )

        self._pin = pin
        self._logger = logger
        self._lock = asyncio.Lock()

        self._terminals: dict[int, Terminal] = {}
        self._terminal_intervals: list[Interval] = []
        self._zone_to_terminal: dict[int, int] = {}
        self._zones: dict[int, Zone] = {}
        self._outputs: dict[int, Output] = {}
        self._single_zones: dict[int, SingleZone] = {}
        self._double_zones: dict[int, DoubleZone] = {}
        self._partitions: dict[int, Partition] = {}

        self._serial_number: str | None = None
        self._firmware: str | None = None
        self._model: str | None = None

        self._initialized = False

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    @property
    def is_connected(self) -> bool:
        """:return: True if the TCP connection to the panel is active and not closing."""
        return self._protocol.is_connected

    @property
    def is_initialized(self) -> bool:
        """:return: True once initialise() has completed successfully at least once."""
        return self._initialized

    async def connect(self) -> Self:
        """Opens the TCP connection to the panel."""
        await self._protocol.connect()
        return self

    def disconnect(self) -> None:
        """Closes the TCP connection."""
        self._protocol.disconnect()

    async def reconnect(self, delay: float = Transport.RECONNECT_DELAY) -> None:
        """Closes the current connection, waits briefly, then reconnects."""
        await self._protocol.reconnect(delay)

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        self.disconnect()

    # ------------------------------------------------------------------
    # Discovery / status refresh
    # ------------------------------------------------------------------
    async def initialize(self) -> None:
        """
        Performs full panel discovery: reads panel info, terminals (zones,
        double-zones, outputs) and partitions, and stores them on the client.

        Must be called (and awaited) once, after connect(), before using any
        of the status/command accessors below.

        """

        async with self._lock:
            serial_number, firmware, model = await get_panel_info(self._protocol)

            terminals, intervals = await initialize_terminals(self._protocol, self._pin)

            zone_to_terminal: dict[int, int] = {}
            zones: dict[int, Zone] = {}
            outputs: dict[int, Output] = {}
            single_zones: dict[int, SingleZone] = {}
            double_zones: dict[int, DoubleZone] = {}

            for terminal_id, terminal in terminals.items():
                if isinstance(terminal, ZoneTerminal):
                    if isinstance(terminal, SingleZone):
                        single_zones[terminal_id] = terminal
                    elif isinstance(terminal, DoubleZone):
                        double_zones[terminal_id] = terminal
                    for zone in terminal.zones:
                        zone_to_terminal[zone.zone_id] = terminal_id
                        zones[zone.zone_id] = zone
                if isinstance(terminal, Output):
                    outputs[terminal_id] = terminal

            zone_ids_by_partition = get_zone_ids_by_partition(zones)
            partitions = await initialize_partitions(
                protocol = self._protocol,
                zone_ids_by_partition = zone_ids_by_partition,
                pin = self._pin,
            )

            self._serial_number = serial_number
            self._firmware = firmware
            self._model = model
            self._terminals = terminals
            self._terminal_intervals = intervals
            self._zone_to_terminal = zone_to_terminal
            self._zones = zones
            self._outputs = outputs
            self._single_zones = single_zones
            self._double_zones = double_zones
            self._partitions = partitions
            self._initialized = True

    async def update_status(self) -> None:
        await self.update_terminals()
        await self.update_partitions()


    async def update_terminals(self) -> None:
        self._require_initialized()

        async with self._lock:
            await update_terminal_statuses(
                self._protocol, self._terminals, self._terminal_intervals, self._pin,
            )

    async def update_partitions(self) -> None:
        self._require_initialized()

        async with self._lock:
            await update_partition_statuses(
                self._protocol, self._partitions, self._pin,
            )

    def get_terminal_id_from_zone_id(self, zone_id: int) -> int:
        try:
            return self._zone_to_terminal[zone_id]
        except KeyError:
            raise KeyError(f"Unknown zone id: {zone_id}") from None

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise NotInitializedError(
                "Client.initialize() must be awaited before this operation is available."
            )

    # ------------------------------------------------------------------
    # Read accessors
    # ------------------------------------------------------------------

    @property
    def panel_info(self) -> tuple[str, str, str] | None:
        """:return: (serial_number, firmware, model), or None if not initialised yet."""
        if not self._initialized:
            return None

        return self._serial_number, self._firmware, self._model

    @property
    def terminals(self) -> MappingProxyType[int, Terminal]:
        """:return: Read-only view of all terminals, keyed by terminal ID."""
        return MappingProxyType(self._terminals)

    @property
    def partitions(self) -> MappingProxyType[int, Partition]:
        """:return: Read-only view of all partitions, keyed by partition ID."""
        return MappingProxyType(self._partitions)

    @property
    def outputs(self) -> MappingProxyType[int, Output]:
        """:return: Terminals that are outputs, keyed by terminal ID."""
        return MappingProxyType(self._outputs)

    @property
    def single_zones(self) -> MappingProxyType[int, SingleZone]:
        """:return: Terminals that are single zones, keyed by terminal ID."""
        return MappingProxyType(self._single_zones)

    @property
    def double_zones(self) -> MappingProxyType[int, DoubleZone]:
        """:return: Terminals that are double zones, keyed by terminal ID."""
        return MappingProxyType(self._double_zones)

    @property
    def zones(self) -> MappingProxyType[int, Zone]:
        """:return: All zones (from single and double-zone terminals), keyed by zone ID."""
        return MappingProxyType(self._zones)

    def get_terminal(self, terminal_id: int) -> Terminal | None:
        return self._terminals.get(terminal_id)

    def get_output(self, terminal_id: int) -> Output | None:
        return self._outputs.get(terminal_id)

    def get_partition(self, partition_id: int) -> Partition | None:
        return self._partitions.get(partition_id)

    def get_zone(self, zone_id: int) -> Zone | None:
        return self._zones.get(zone_id)

    def get_single_zone(self, terminal_id: int) -> SingleZone | None:
        return self._single_zones.get(terminal_id)

    def get_double_zone(self, terminal_id: int) -> DoubleZone | None:
        return self._double_zones.get(terminal_id)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    ###
    ### Set output
    ###
    async def set_output(
            self,
            output_id: int,
            state: bool,
    ) -> None:
        """Turns an output on or off."""
        async with self._lock:
            await set_output_status(
                self._protocol, output_id, state, self._pin,
            )

    ###
    ### Set zone bypass
    ###
    async def set_zone_bypass(
            self,
            zone_id: int,
            bypass: bool,
    ) -> None:
        """Enables or disables bypass on a single zone."""
        async with self._lock:
            await set_zone_bypass(
                self._protocol, zone_id, bypass, self._pin,
            )

    async def set_all_zones_bypass(
            self,
            bypass: bool,
    ) -> None:
        """Enables or disables bypass on every zone that isn't already in that state.
        Unknown state is updated.
        The state considered is the one the client has when the function is called."""
        self._require_initialized()
        for zone in self.zones.values():
            if zone.zone_status is not None and zone.zone_status.bypass == bypass:
                continue
            await self.set_zone_bypass(zone.zone_id, bypass)


    ###
    ### Set partition arming status
    ###
    async def set_partition_arming_statuses(
            self,
            arming_statuses: dict[int, ArmingStatus],
    ) -> None:
        """Sets the arming status of one or more partitions in a single command."""
        async with self._lock:
            await set_partition_arming_statuses(
                self._protocol, arming_statuses, self._pin,
            )

    async def set_partition_arming_status(
            self,
            partition_id: int,
            arming_status: ArmingStatus,
    ) -> None:
        """Sets the arming status of a single partition."""
        await self.set_partition_arming_statuses({partition_id: arming_status})


    async def set_all_partitions_arming_status(
            self,
            arming_status: ArmingStatus,
    ) -> None:
        """Sets an arming status of all partitions in a single command."""
        self._require_initialized()

        arming_statuses = {
            partition_id: arming_status
            for partition_id in self._partitions
        }

        await self.set_partition_arming_statuses(arming_statuses)

    async def disarm_all_partitions(
            self,
    ) -> None:
        """Convenience wrapper to disarm all partitions."""
        await self.set_all_partitions_arming_status(ArmingStatus.DISARMED)


    ###
    ### Reset partition memory
    ###
    async def reset_partition_memories(
            self,
            partition_ids: set[int],
    ) -> None:
        """Clears alarm memory for the given partitions."""
        async with self._lock:
            await reset_partition_memories(
                self._protocol, partition_ids, self._pin,
            )

    async def reset_partition_memory(
            self,
            partition_id: int,
    ) -> None:
        """Clears alarm memory for the given partition."""
        await self.reset_partition_memories({partition_id})

    async def reset_all_partition_memories(
            self,
    ) -> None:
        """Convenience wrapper to clear memory for all partitions."""
        self._require_initialized()
        await self.reset_partition_memories(set(self._partitions))


    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    ### Special methods
    def __repr__(self) -> str:
        return (
            f"Client(host={self._protocol!r}, initialized={self._initialized}, "
            f"connected={self.is_connected})"
        )