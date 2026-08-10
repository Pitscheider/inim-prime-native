from __future__ import annotations

import asyncio
import logging
import socket
from typing import Self, ClassVar

from .header import Header


class Transport:
    ### Constants
    DEFAULT_CONNECT_TIMEOUT: ClassVar[float] = 15.0  # 15 seconds
    DEFAULT_RECEIVE_TIMEOUT: ClassVar[float] = 20.0  # 20 seconds
    RECONNECT_DELAY: ClassVar[float] = 0.02  # 20 ms
    MIN_EXCHANGE_INTERVAL: ClassVar[float] = 0.005  # 5 ms

    ###
    __slots__ = (
        "_host",
        "_port",
        "_logger",
        "_connect_timeout",
        "_receive_timeout",
        "_reader",
        "_writer",
        "_lock",
        "_last_exchanged_at",
    )

    def __init__(
            self,
            host: str,
            port: int,
            logger: logging.Logger | None = None,
            connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
            receive_timeout: float = DEFAULT_RECEIVE_TIMEOUT,
    ) -> None:
        """
        Initialises the transport with connection parameters and internal state.
        No TCP connection is made here, call connect() to establish one.
        :param host:            IP address or hostname of the panel.
        :param port:            TCP port of the panel.
        :param logger:          Optional logger for debug and error messages.
        :param connect_timeout: Seconds before connect() gives up.
                                Defaults to DEFAULT_CONNECT_TIMEOUT.
        :param receive_timeout: Seconds before a pending reception raises TimeoutError.
                                Defaults to DEFAULT_RECEIVE_TIMEOUT.
        """

        # Connection parameters
        self._host = host
        self._port = port
        self._logger = logger
        self._connect_timeout = connect_timeout
        self._receive_timeout = receive_timeout

        # Asyncio stream handles. None until connect() is called successfully.
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

        # Mutex that serialises all send/receive operations.
        # Ensures only one command is in flight at a time
        self._lock = asyncio.Lock()

        # Timestamp of the last sent frame, used by _enforce_rate_limit().
        # None means no frame has been sent yet in this session.
        self._last_exchanged_at: float | None = None

    #
    # Properties
    #

    @property
    def is_connected(
            self,
    ) -> bool:
        """
        :return: True if both reader and writer are initialised and the writer is not closing.
        """
        return (
                self._writer is not None
                and not self._writer.is_closing()
                and self._reader is not None
        )

    #
    # Lifecycle
    #

    async def connect(
            self,
    ) -> None:
        """
        Opens a TCP connection to the panel and configures the socket.

        If a connection is already open, it is closed before opening a new one.
        The socket is configured with TCP_NODELAY to disable Nagle's algorithm,
        ensuring frames are sent immediately without buffering.

        :raises TimeoutError:   If the connection is not established within connect_timeout seconds.
        :raises OSError:        If the connection is refused or the host is unreachable.
        """
        # Close any existing connection before opening a new one
        self.close()

        try:
            # Open the TCP connection with a timeout to prevent hanging indefinitely
            reader, writer = await asyncio.wait_for(
                fut = asyncio.open_connection(self._host, self._port),
                timeout = self._connect_timeout,
            )

            # Disable Nagle's algorithm to ensure frames are sent immediately.
            # Without this, small frames may be buffered for up to 200ms before sending.
            sock: socket.socket | None = writer.get_extra_info("socket")
            if sock is not None:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            # Only store the stream handles after the socket is fully configured
            self._reader = reader
            self._writer = writer

            if self._logger:
                self._logger.debug(
                    "TRANSPORT -> TCP connected to %s:%d", self._host, self._port
                )

        except Exception:
            # Clean up any partially initialised state before propagating the exception
            self.close()
            raise

    def close(
            self,
    ) -> None:
        """
        Closes the current TCP connection and resets the transport state.

        This method is safe to call multiple times and will never raise exceptions.
        If a connection is active, it is closed in a best-effort manner.

        Notes:
            - The underlying StreamWriter is closed without awaiting full shutdown
              (i.e. wait_closed() is not used) to keep this method synchronous.
            - Any errors during socket closure are intentionally ignored.
            - After this call, the transport is considered disconnected.

        Side effects:
            - _writer and _reader are set to None.
            - is_connected will return False after this call.
        """

        # If a writer exists, attempt to close the TCP connection
        if self._writer is not None:
            try:
                # Initiates closing the socket (non-blocking)
                self._writer.close()
            except Exception:
                # Ignore all errors during cleanup to guarantee safe teardown
                pass

            # Mark writer as no longer usable
            self._writer = None

        # Reader does not require explicit closing.
        self._reader = None

        # Logs connection closure
        if self._logger:
            self._logger.debug("TRANSPORT -> TCP connection closed.")

    async def reconnect(
            self,
            delay: float = RECONNECT_DELAY,
    ) -> None:
        """
        Closes the current connection (if any) and establishes a new one.

        An optional delay can be introduced between closing and reconnecting
        to avoid rapid reconnect attempts and allow the underlying system or
        remote endpoint to stabilise.

        :param delay:           Seconds to wait before reconnecting.
                                Defaults to RECONNECT_DELAY.
        :raises TimeoutError:   If the new connection attempt times out.
        :raises OSError:        If the connection fails.
        """

        # Ensure previous connection is closed
        self.close()

        # Waits the given delay to avoid tight reconnect loops / TCP edge cases
        if delay > 0:
            await asyncio.sleep(delay)

        # Establish a new connection
        await self.connect()

    #
    # I/O
    #

    async def exchange_frame(
            self,
            frame: bytes,
            header_type: type[Header]
    ) -> bytes:
        """
        Sends a frame to the panel and waits for the corresponding response.

        Notes:
            - Only one exchange is in flight at a time (via an async lock)
            - A minimum delay between consecutive exchanges
            - Full transmission of the outgoing frame before receiving

        :param frame:               The raw frame to send.
        :param header_type:         Header class type
        :return:                    The response as a raw frame.
        :raises ConnectionError:    If the transport is not connected.
        :raises TimeoutError:       If the response is not received in time.
        :raises OSError:            If the connection fails during transmission.
        """

        async with self._lock:
            # Enforce minimum delay between exchanges
            await self._enforce_exchange_interval()

            # Ensure connection is active
            if not self.is_connected:
                raise ConnectionError(
                    f"TCP connection to {self._host}:{self._port} is not active. "
                    "Call connect() first."
                )

            # Log outgoing frame
            if self._logger:
                self._logger.debug(
                    "TRANSPORT -> TX %d bytes", len(frame)
                )

            # Send frame
            assert self._writer is not None
            self._writer.write(frame)
            await self._writer.drain()

            # Receive response
            response = await self._receive(header_type)

            # Record exchange timestamp (for rate limiting)
            self._last_exchanged_at = asyncio.get_running_loop().time()

            return response

    async def _receive(
            self,
            header_type: type[Header],
    ) -> bytes:
        """
        Low-level transport receive method.

        Responsibilities:
            - Reads a complete framed response from the TCP stream
            - Extracts inner frame size from outer header
            - Reads the exact number of inner frame bytes
            - Enforces per-stage receive timeout

        Notes:
            - Caller is responsible for ensuring is_connected is True before calling.

        :return: Raw response frame composed of outer header + inner frame.
        :raises ConnectionError:    If the transport is not connected or connection is lost mid-read.
        :raises TimeoutError:       If the panel does not respond within the configured timeout.

        """

        try:
            # Precondition: is_connected is True - guaranteed by exchange_frame
            assert self._reader is not None

            # Read fixed-size outer header
            header_bytes = await asyncio.wait_for(
                self._reader.readexactly(header_type.Layout.size),
                timeout = self._receive_timeout,
            )

            header = header_type.from_bytes(header_bytes)

            if self._logger:
                self._logger.debug(
                    "TRANSPORT -> Header received, declared inner body length = %d bytes.",
                    header.inner_body_length,
                )

            # Read inner frame
            inner_body = await asyncio.wait_for(
                self._reader.readexactly(header.inner_body_length),
                timeout = self._receive_timeout,
            )

        except asyncio.IncompleteReadError as exc:
            if self._logger:
                self._logger.error(
                    "TRANSPORT -> Connection closed mid-response after %d bytes.",
                    len(exc.partial),
                )
            self.close()
            raise ConnectionError(
                "Panel closed the connection mid-response."
            ) from exc

        except asyncio.TimeoutError:
            if self._logger:
                self._logger.error(
                    "TRANSPORT -> Timeout waiting for response (%.0fs).",
                    self._receive_timeout,
                )
            raise TimeoutError(
                f"Panel did not respond within {self._receive_timeout:.0f}s."
            ) from None

        result = b"".join((
            header.raw_bytes,
            inner_body,
        ))

        if self._logger:
            self._logger.debug(
                "TRANSPORT -> RX complete: %d bytes received.",
                len(result),
            )

        return result


    async def _enforce_exchange_interval(
            self,
    ) -> None:
        """
        Ensures that a minimum amount of time has elapsed between completed
        request/response exchanges.

        This prevents the transport from issuing exchanges too rapidly,
        which may violate wire timing requirements or overwhelm the device.

        Notes:
            - The first exchange is not delayed.
            - Uses a monotonic event loop clock for accurate timing.
            - Only sleeps if the last exchange occurred too recently.
        """

        if self._last_exchanged_at is None:
            return

        # Calculates the elapsed time from the last exchange
        elapsed = asyncio.get_running_loop().time() - self._last_exchanged_at

        # Calculates the difference between the minimum exchange interval and the elapsed time.
        # It stops for an amount of time equal to that difference if it is greater than 0.
        gap = self.MIN_EXCHANGE_INTERVAL - elapsed
        if gap > 0:
            await asyncio.sleep(gap)

    #
    # Context manager
    #

    async def __aenter__(
            self,
    ) -> Self:
        """
        Opens a TCP connection when entering the context.
        """
        await self.connect()
        return self

    async def __aexit__(
            self,
            *_: object,
    ) -> None:
        """
        Closes the TCP connection when exiting the context.
        """
        self.close()
