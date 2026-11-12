from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Final, Self

from inim.prime.native.const import CommandOperation, FrameOperation, Panel
from .cipher import Cipher
from .frame import OuterFrame, InnerFrame, Frame
from .header import InnerHeader, OuterHeader
from .payload import ReadRequestPayload, ReadResponsePayload, CommandWithPinRequestPayload, ChecksummedPayload, \
    CommandRequestPayload, CommandResponsePayload, CommandWithPinResponsePayload
from .transport import Transport

### Logging helpers
HEX_LOG_LIMIT: Final[int] = 256  # bytes shown before truncating a hex dump
CHECKSUM_SEARCH_BACK: Final[int] = 4  # how far before the expected checksum position to search


def _hex(data: bytes, limit: int = HEX_LOG_LIMIT) -> str:
    """Hex dump, truncated after `limit` bytes."""
    if len(data) <= limit:
        return data.hex(" ")
    return f"{data[:limit].hex(' ')} ... (+{len(data) - limit} B)"


def _byte(value: int | None) -> str:
    return "none" if value is None else f"{value} (0x{value:02x})"


def _describe_payload(payload: bytes, pin_slice: slice | None) -> str:
    """Hex dump of a plaintext payload with the PIN field redacted."""
    if pin_slice is None or len(payload) < pin_slice.stop:
        return _hex(payload)
    pin = payload[pin_slice]
    pin_text = "[no PIN]" if pin == Panel.DEFAULT_MASTER_PIN else "[PIN redacted]"
    before = payload[:pin_slice.start].hex(" ")
    after = _hex(payload[pin_slice.stop:])
    return f"{before} {pin_text} {after}".strip()


def _read_summary(chunk_length: int, response: bytes) -> str:
    """Explain the layout of a memory-read response (where the checksum really is)."""
    got = len(response)
    data_sum = sum(response[:chunk_length]) & 0xFF
    after_data = response[chunk_length] if got > chunk_length else None
    last = response[-1] if response else None
    sum_but_last = (sum(response[:-1]) & 0xFF) if response else None

    # Offsets near the end whose byte equals the 8-bit sum of everything before it
    hits: list[int] = []
    running = sum(response[:max(0, chunk_length - CHECKSUM_SEARCH_BACK)])
    for offset in range(max(0, chunk_length - CHECKSUM_SEARCH_BACK), got):
        if response[offset] == running & 0xFF:
            hits.append(offset)
        running += response[offset]

    tail_start = max(0, chunk_length - 8)
    return (
        f"asked {chunk_length} B, got {got} B "
        f"(expected {chunk_length + 1}, extra {got - chunk_length - 1:+d}); "
        f"sum(data)={_byte(data_sum)}; byte after data={_byte(after_data)}; "
        f"last byte={_byte(last)}; sum(all but last)={_byte(sum_but_last)}; "
        f"checksum matches at offset(s) {hits or 'none'}; "
        f"tail from offset {tail_start}: {response[tail_start:].hex(' ')}"
    )

def _describe_panel_time(response: ReadResponsePayload) -> str:
    """Panel clock from a read response, with the drift against the local clock."""
    raw = f"raw {response.timestamp.hex(' ')} | utc offset {response.timestamp_utc_offset.hex(' ')}"
    try:
        panel_time = response.timestamp_datetime
    except (ValueError, OverflowError) as err:   # e.g. an implausible offset
        return f"undecodable ({err}) | {raw}"
    drift = (panel_time - datetime.now(timezone.utc)).total_seconds()
    return f"{panel_time.isoformat()} | drift {drift:+.1f} s vs local clock | {raw}"


class Protocol:
    READ_REQUEST_MAX_CHUNK_SIZE: Final[int] = 1024

    __slots__ = (
        "_logger",
        "_crypto",
        "_transport",
        "_use_outer_frame",
    )

    def __init__(
            self,
            host: str,
            password: str,
            port: int,
            use_outer_frame: bool,
            logger: logging.Logger | None = None,
            connect_timeout: float = Transport.DEFAULT_CONNECT_TIMEOUT,
            receive_timeout: float = Transport.DEFAULT_RECEIVE_TIMEOUT,
    ) -> None:
        """
        Initialises the wire engine with connection parameters.
        No TCP connection is made here, call connect() to establish one.

        :param host:            IP address or hostname of the panel.
        :param password:        UTF-8 password string, 1–16 characters.
        :param port:            TCP port of the panel.
        :param logger:          Optional logger for debug and error messages.
                                At DEBUG level every exchange is logged in detail
                                (PIN redacted; password and key never logged).
        :param connect_timeout: Seconds before connect() gives up.
                                Defaults to Transport.DEFAULT_CONNECT_TIMEOUT.
        :param receive_timeout: Seconds before a pending reception raises TimeoutError.
                                Defaults to Transport.DEFAULT_RECEIVE_TIMEOUT.
        """

        self._logger = logger

        # AES-128-CBC cipher, owns the key and IV derived from the password.
        # The class never sees the raw password after this point.
        self._crypto = Cipher(password)

        self._use_outer_frame = use_outer_frame

        # TCP transport, owns the connection lifecycle and raw byte exchange.
        self._transport = Transport(
            host = host,
            port = port,
            logger = logger,
            connect_timeout = connect_timeout,
            receive_timeout = receive_timeout,
        )

    #
    # Logging
    #

    @property
    def _debug_enabled(self) -> bool:
        """True when detailed exchange logging is active (avoids formatting costs otherwise)."""
        return self._logger is not None and self._logger.isEnabledFor(logging.DEBUG)

    def _log(self, level: int, msg: str, *args: object) -> None:
        if self._logger is not None:
            self._logger.log(level, msg, *args)

    def _log_command_response(
            self,
            operation: CommandOperation,
            response: bytes,
            header_size: int,
    ) -> None:
        """Log a command response: header, opcode echo check, data."""
        expected_echo = (~int(operation) & 0xFFFFFFFF).to_bytes(4, "little")
        echo_ok = response[:4] == expected_echo

        if not echo_ok:
            self._log(
                logging.WARNING,
                "PROTOCOL -> [CMD %s] unexpected response header %s (expected echo %s)",
                operation.name, response[:header_size].hex(" "), expected_echo.hex(" "),
            )

        if self._debug_enabled:
            self._logger.debug(
                "PROTOCOL -> [CMD %s] response %d B | header (%d B): %s | echo %s | data (%d B): %s",
                operation.name,
                len(response),
                header_size,
                response[:header_size].hex(" "),
                "OK" if echo_ok else "MISMATCH",
                max(0, len(response) - header_size),
                _hex(response[header_size:]),
            )

    #
    # Connection lifecycle
    #

    @property
    def is_connected(
            self,
    ) -> bool:
        """
        :return: True if the TCP connection to the panel is active and not closing.
        """
        return self._transport.is_connected

    async def connect(
            self,
    ) -> Self:
        """
        Opens the TCP connection to the panel.
        :raises TimeoutError:   If the connection times out.
        :raises OSError:        If the connection is refused or the host is unreachable.
        """
        await self._transport.connect()
        return self

    def disconnect(
            self,
    ) -> None:
        """
        Closes the TCP connection
        """
        self._transport.close()

    async def reconnect(
            self,
            delay: float = Transport.RECONNECT_DELAY,
    ) -> None:
        """
        Closes the current connection, waits briefly, then reconnects.
        :param delay:           Delay between reconnects.
                                Defaults to TransportConfig.RECONNECT_DELAY.
        :raises TimeoutError:   If the new connection attempt times out.
        :raises OSError:        If the connection is refused or the host is unreachable.
        """
        await self._transport.reconnect(delay)

    # ------------------------------------------------------------------
    # Raw read / command primitives
    # ------------------------------------------------------------------
    async def exchange_payload(
            self,
            payload: bytes,
            operation: FrameOperation,
            response_payload_length: int | None = None,
            *,
            label: str = "",
            pin_slice: slice | None = None,
    ) -> bytes:
        """
        Encrypts and sends a payload, then receives, validates and decrypts the response.
        :param label:       Short tag used in log lines (e.g. "CMD GET_PANEL_INFO").
        :param pin_slice:   Position of the PIN field in `payload`, redacted in logs.
        """
        debug = self._debug_enabled
        tag = label or operation.name

        if debug:
            self._logger.debug(
                "PROTOCOL -> [%s] TX plaintext (%d B): %s",
                tag, len(payload), _describe_payload(payload, pin_slice),
            )

        # Encrypt the payload using AES-128-CBC
        encrypted_payload = self._crypto.encrypt(
            plaintext = payload,
        )

        inner_frame = InnerFrame.build(
            encrypted_payload = encrypted_payload,
            operation = operation,
        )

        frame: Frame = inner_frame

        if self._use_outer_frame:
            frame = OuterFrame.build(
                inner_frame = inner_frame,
                response_payload_length = response_payload_length,
            )

        frame_bytes = frame.to_bytes()

        if debug:
            header_len = len(frame_bytes) - len(encrypted_payload)
            self._logger.debug(
                "PROTOCOL -> [%s] TX frame %d B | header: %s | ciphertext %d B | announced response length: %s",
                tag,
                len(frame_bytes),
                frame_bytes[:header_len].hex(" "),
                len(encrypted_payload),
                response_payload_length if self._use_outer_frame else "n/a (no outer frame)",
            )

        # Send the frame and receive the raw response
        started = time.monotonic()
        response_frame = await self._transport.exchange_frame(
            frame_bytes,
            frame.header_type,
        )
        elapsed_ms = (time.monotonic() - started) * 1000

        inner_offset = OuterHeader.Layout.size if self._use_outer_frame else 0
        response_header_len = inner_offset + InnerHeader.Layout.size

        if debug:
            magic = response_frame[inner_offset:inner_offset + 2]
            self._logger.debug(
                "PROTOCOL -> [%s] RX frame %d B in %.1f ms | header: %s | inner magic: %s",
                tag,
                len(response_frame),
                elapsed_ms,
                response_frame[:response_header_len].hex(" "),
                magic.hex(" "),
            )

        # Strip headers and validate, returns the encrypted response payload
        response_encrypted_payload: bytes
        try:
            if self._use_outer_frame:
                response_encrypted_payload = OuterFrame.disassemble(response_frame)
            else:
                response_encrypted_payload = InnerFrame.disassemble(response_frame)
        except ValueError as err:
            self._log(
                logging.ERROR,
                "PROTOCOL -> [%s] response frame validation failed: %s | raw frame (%d B): %s",
                tag, err, len(response_frame), _hex(response_frame, 512),
            )
            raise

        # Decrypt and return the plaintext response
        try:
            response_payload = self._crypto.decrypt(response_encrypted_payload)
        except ValueError as err:
            self._log(
                logging.ERROR,
                "PROTOCOL -> [%s] decryption failed (wrong password?): %s | ciphertext (%d B): %s",
                tag, err, len(response_encrypted_payload), _hex(response_encrypted_payload),
            )
            raise

        if debug:
            self._logger.debug(
                "PROTOCOL -> [%s] RX plaintext (%d B): %s",
                tag, len(response_payload), _hex(response_payload),
            )

        return response_payload

    async def execute_command(
            self,
            operation: CommandOperation,
            data: bytes | None = None,
            response_payload_data_length: int | None = None,
    ) -> bytes:

        response_payload_length = response_payload_data_length - CommandResponsePayload.Layout.header_size if response_payload_data_length else None

        payload = CommandRequestPayload.assemble(
            operation = operation,
            data = data,
        )

        response_payload = await self.exchange_payload(
            payload = payload,
            operation = FrameOperation.COMMAND,
            response_payload_length = response_payload_length,
            label = f"CMD {operation.name}",
        )

        self._log_command_response(operation, response_payload, CommandResponsePayload.Layout.header_size)

        return CommandResponsePayload.disassemble(response_payload)

    async def execute_command_with_pin(
            self,
            operation: CommandOperation,
            data: bytes | None = None,
            pin: str | None = None,
            response_payload_data_length: int | None = None,
    ) -> bytes:

        response_payload_length = response_payload_data_length - CommandWithPinResponsePayload.Layout.header_size if response_payload_data_length else None

        payload = CommandWithPinRequestPayload.assemble(
            operation = operation,
            pin = pin,
            data = data,
        )

        response_payload = await self.exchange_payload(
            payload = payload,
            operation = FrameOperation.COMMAND,
            response_payload_length = response_payload_length,
            label = f"CMD {operation.name}",
            pin_slice = CommandWithPinRequestPayload.Layout.pin,
        )

        header_size = (
                CommandWithPinResponsePayload.Layout.header_size
                + CommandWithPinResponsePayload.Layout.header_with_pin_size
        )
        self._log_command_response(operation, response_payload, header_size)

        return CommandWithPinResponsePayload.disassemble(response_payload)

    async def read_memory(
            self,
            start_address: int,
            bytes_to_read: int
    ) -> bytes:
        """
        Reads the specified amount of bytes from the memory starting at the specified address.
        :param start_address:   Memory address to start reading from.
        :param bytes_to_read:   Number of bytes to read.
        :return:                The bytes read from the memory, merged into one buffer without checksum.
        """

        result = bytearray(bytes_to_read)

        num_chunks = (bytes_to_read + self.READ_REQUEST_MAX_CHUNK_SIZE - 1) // self.READ_REQUEST_MAX_CHUNK_SIZE

        if self._debug_enabled:
            self._logger.debug(
                "PROTOCOL -> READ 0x%08X..0x%08X: %d B in %d chunk(s)",
                start_address, start_address + bytes_to_read - 1, bytes_to_read, num_chunks,
            )

        for chunk_index in range(num_chunks):
            offset = chunk_index * self.READ_REQUEST_MAX_CHUNK_SIZE

            # Last chunk may be smaller than the maximum read request chunk size
            chunk_size = min(self.READ_REQUEST_MAX_CHUNK_SIZE, bytes_to_read - offset)

            address = start_address + offset

            response_payload_chunk = await self._read_memory_chunk(
                address = address,
                chunk_length = chunk_size,
                transfer_length = bytes_to_read if chunk_index == 0 else None
            )

            result[offset: offset + chunk_size] = response_payload_chunk

        return bytes(result)

    async def _read_memory_chunk(
            self,
            address: int,
            chunk_length: int,
            transfer_length: int | None = None,
    ) -> bytes:
        """
        Reads a memory chunk of the specified amount of bytes, starting at the specified address.
        :param address:         Memory address to start reading from.
        :param chunk_length:    Number of bytes to read in the current chunk. This value is <= than the maximum read request chunk size.
        :param transfer_length: Total number of bytes to read in the read memory operation. This value is None if this is not the first chunk in the operation.
        :return:                The bytes read from the memory, without checksum.
        """

        # Build the plaintext read request payload
        payload = ReadRequestPayload.assemble(
            address = address,
            chunk_length = chunk_length,
            transfer_length = transfer_length,
        )

        tag = f"READ 0x{address:08X}+{chunk_length}"

        response_payload_bytes = await self.exchange_payload(
            payload = payload,
            operation = FrameOperation.READ,
            response_payload_length = chunk_length + ChecksummedPayload.Layout.checksum_size,
            label = tag,
        )

        if self._debug_enabled:
            self._logger.debug(
                "PROTOCOL -> [%s] layout: %s",
                tag, _read_summary(chunk_length, response_payload_bytes),
            )

        # Validate the response payload, strip checksum and timestamp, return the read bytes
        try:
            response = ReadResponsePayload.from_bytes(response_payload_bytes)

            if self._debug_enabled:
                self._logger.debug(
                    "PROTOCOL -> [%s] panel time: %s",
                    tag, _describe_panel_time(response),
                )

            data = response.validate().data
            if len(data) != chunk_length:
                raise ValueError(
                    f"Read response length mismatch: asked {chunk_length} B, got {len(data)} B."
                )
            return data
        except ValueError as err:
            self._log(
                logging.ERROR,
                "PROTOCOL -> [%s] %s | %s",
                tag, err, _read_summary(chunk_length, response_payload_bytes),
            )
            raise

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "Protocol":
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        self.disconnect()