from __future__ import annotations

import logging
from typing import Final, Self

from inim.prime.native.const import CommandOperation, FrameOperation
from .cipher import Cipher
from .frame import OuterFrame, InnerFrame, Frame
from .payload import ReadRequestPayload, ReadResponsePayload, CommandWithPinRequestPayload, ChecksummedPayload, \
    CommandRequestPayload, CommandResponsePayload, CommandWithPinResponsePayload
from .transport import Transport


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
    ) -> bytes:
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

        # Send the frame and receive the raw response
        response_frame = await self._transport.exchange_frame(
            frame.to_bytes(),
            frame.header_type,
        )

        response_encrypted_payload: bytes
        # Strip headers and validate, returns the encrypted response payload
        if self._use_outer_frame:
            response_encrypted_payload = OuterFrame.disassemble(response_frame)
        else:
            response_encrypted_payload = InnerFrame.disassemble(response_frame)

        # Decrypt and return the plaintext response
        response_payload = self._crypto.decrypt(response_encrypted_payload)

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
        )

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
        )

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

        response_payload_bytes = await self.exchange_payload(
            payload = payload,
            operation = FrameOperation.READ,
            response_payload_length = chunk_length + ChecksummedPayload.Layout.checksum_size,
        )

        # Validate the response payload, strip checksum, and returns read bytes
        return ReadResponsePayload.disassemble(response_payload_bytes)

    
    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "Protocol":
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        self.disconnect()
