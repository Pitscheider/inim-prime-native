from __future__ import annotations

from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import ClassVar, Self, Final

from inim.prime.native.const import Encoding, CommandOperation, Panel, EncodingSizes
from inim.prime.native.utils import next_slice, previous_slice, decode_int, encode_int


### Helpers
def _checksum(data: bytes) -> int:
    """Simple 8-bit additive checksum (sum of all bytes, truncated to 1 byte)."""
    return sum(data) & 0xFF

### Payloads Abstract
class BasePayload(ABC):

    ### Main
    @classmethod
    @abstractmethod
    def assemble(cls, **kwargs) -> bytes:
        """
        Build a payload from logical parameters and return wire bytes.
        Convenience shortcut for build(...).to_bytes().
        Each subclass declares its own typed parameter list.
        """
        ...

    @classmethod
    @abstractmethod
    def disassemble(cls, raw: bytes) -> object:
        """
        Parse raw bytes and return meaningful content.
        Validates integrity if applicable.
        Concrete subclasses narrow the return type to their specific output.
        """
        ...

    ### Constructors
    @classmethod
    @abstractmethod
    def build(cls, **kwargs) -> Self:
        """Construct a payload instance from logical parameters."""
        ...

    @classmethod
    @abstractmethod
    def from_bytes(cls, raw: bytes) -> Self:
        """
        Parse raw bytes into a payload instance.
        Must not validate integrity — call validate() separately if needed.
        """
        ...

    ### Properties
    ## Serialization
    @property
    @abstractmethod
    def raw_bytes(self) -> bytes:
        """All fields in wire order, without recomputing any integrity value."""
        ...

    ### Methods
    ## Serialization
    def to_bytes(self) -> bytes:
        """
        Serialise the payload to bytes, finalising any integrity fields first.
        Default implementation delegates straight to raw_bytes.
        Overridden by ChecksummedPayload to update the checksum before returning.
        """
        return self.raw_bytes


class ChecksummedPayload(BasePayload, ABC):

    ### Constants
    class Layout:
        checksum_size: Final[int] = EncodingSizes.UINT8_SIZE

    CHECKSUM_COVERAGE: ClassVar[slice]  # subclasses define the exact coverage


    ### Properties
    ## Attributes
    @property
    @abstractmethod
    def checksum(self) -> bytes:
        """Subclasses must store this as a dataclass field."""
        ...

    @checksum.setter
    @abstractmethod
    def checksum(self, value: bytes) -> None:
        """Subclasses must store this as a dataclass field."""
        ...

    ## Helpers
    @property
    def checksum_int(self) -> int:
        return decode_int(self.checksum, Encoding.UINT8)

    @checksum_int.setter
    def checksum_int(self, value: int) -> None:
        self.checksum = encode_int(value, Encoding.UINT8)

    ## Validation
    @property
    def is_checksum_valid(self) -> bool:
        return self.checksum_int == self.calculate_checksum()


    ### Methods
    ## Checksum
    def calculate_checksum(self) -> int:
        """Computes the checksum over CHECKSUM_COVERAGE of the current raw bytes."""
        return _checksum(self.raw_bytes[self.CHECKSUM_COVERAGE])

    def update_checksum(self) -> None:
        """Writes the computed checksum into the checksum field."""
        self.checksum_int = self.calculate_checksum()

    ## Validation
    def validate(self) -> Self:
        """
        :raises ValueError: If the stored checksum does not match the computed one.
        """
        if not self.is_checksum_valid:
            raise ValueError(
                f"Checksum mismatch: declared {self.checksum_int}, "
                f"computed {self.calculate_checksum()}."
            )
        return self

    ## Serialization
    def to_bytes(self) -> bytes:
        """Updates the checksum field, then returns the wire bytes."""
        self.update_checksum()
        return self.raw_bytes


### Read Payloads
@dataclass(slots = True)
class ReadRequestPayload(ChecksummedPayload):

    ### Constants
    class Layout:
        address_size: Final[int] = EncodingSizes.UINT64_LE_SIZE
        transfer_length_size: Final[int] = EncodingSizes.UINT32_LE_SIZE
        chunk_length_size: Final[int] = EncodingSizes.UINT32_LE_SIZE
        padding_size: Final[int] = 2
        marker_size: Final[int] = 1
        checksum_size: Final[int] = ChecksummedPayload.Layout.checksum_size

        size: Final[int] = (
                address_size
                + transfer_length_size
                + chunk_length_size
                + padding_size
                + marker_size
                + checksum_size
        )

        address: Final[slice] = next_slice(0, address_size)
        transfer_length: Final[slice] = next_slice(address, transfer_length_size)
        chunk_length: Final[slice] = next_slice(transfer_length, chunk_length_size)
        padding: Final[slice] = next_slice(chunk_length, padding_size)
        marker: Final[slice] = next_slice(padding, marker_size)
        checksum: Final[slice] = next_slice(marker, checksum_size)

    MARKER: ClassVar[bytes] = b"\x11"
    CHECKSUM_COVERAGE: ClassVar[slice] = slice(Layout.address.start, Layout.marker.stop)


    ### Attributes
    address: bytes = bytes(Layout.address_size)
    transfer_length: bytes = bytes(Layout.transfer_length_size)
    chunk_length: bytes = bytes(Layout.chunk_length_size)
    padding: bytes = bytes(Layout.padding_size)
    marker: bytes = MARKER
    checksum: bytes = bytes(Layout.checksum_size)


    ### Main
    @classmethod
    def assemble(cls, address: int, chunk_length: int, transfer_length: int | None = None) -> bytes:
        """Builds the payload, computes its checksum, and returns the wire bytes."""
        return cls.build(
            address = address,
            chunk_length = chunk_length,
            transfer_length = transfer_length,
        ).to_bytes()

    @classmethod
    def disassemble(cls, raw: bytes) -> tuple[int, int, int]:
        """
        Validates the checksum and returns the parsed fields.
        :param raw:     Raw read request payload bytes.
        :return:        (address, transfer_length, chunk_length) as integers.
        :raises ValueError: If the checksum is invalid.
        """
        instance = cls.from_bytes(raw)
        instance.validate()
        return instance.address_int, instance.transfer_length_int, instance.chunk_length_int


    ### Constructors
    @classmethod
    def build(cls, address: int, chunk_length: int, transfer_length: int | None = None) -> Self:
        """Constructs a payload object from logical parameters. Checksum is 0-initialised."""
        instance = cls()
        instance.address_int = address
        if transfer_length is not None:
            instance.transfer_length_int = transfer_length
        else:
            instance.transfer_length_int = chunk_length
        instance.chunk_length_int = chunk_length
        return instance

    @classmethod
    def from_bytes(cls, raw: bytes) -> Self:
        """Parses raw bytes into a payload object. Does not validate the checksum."""
        return cls(
            address = raw[cls.Layout.address],
            transfer_length = raw[cls.Layout.transfer_length],
            chunk_length = raw[cls.Layout.chunk_length],
            padding = raw[cls.Layout.padding],
            marker = raw[cls.Layout.marker],
            checksum = raw[cls.Layout.checksum],
        )


    ### Properties
    ## Helpers
    @property
    def address_int(self) -> int:
        return decode_int(self.address, Encoding.UINT64_LE)

    @address_int.setter
    def address_int(self, value: int) -> None:
        self.address = encode_int(value, Encoding.UINT64_LE)

    @property
    def transfer_length_int(self) -> int:
        return decode_int(self.transfer_length, Encoding.UINT32_LE)

    @transfer_length_int.setter
    def transfer_length_int(self, value: int) -> None:
        self.transfer_length = encode_int(value, Encoding.UINT32_LE)

    @property
    def chunk_length_int(self) -> int:
        return decode_int(self.chunk_length, Encoding.UINT32_LE)

    @chunk_length_int.setter
    def chunk_length_int(self, value: int) -> None:
        self.chunk_length = encode_int(value, Encoding.UINT32_LE)

    ## Serialization
    @property
    def raw_bytes(self) -> bytes:
        return b"".join((
            self.address,
            self.transfer_length,
            self.chunk_length,
            self.padding,
            self.marker,
            self.checksum,
        ))


@dataclass(slots = True)
class ReadResponsePayload(ChecksummedPayload):

    ### Constants
    class Layout:
        checksum_size: Final[int] = ChecksummedPayload.Layout.checksum_size

        checksum: Final[slice] = previous_slice(None, checksum_size)
        data: Final[slice] = previous_slice(checksum, None)

    CHECKSUM_COVERAGE: ClassVar[slice] = Layout.data


    ### Attributes
    data: bytes = b""
    checksum: bytes = bytes(1)

    ### Main
    @classmethod
    def assemble(cls, data: bytes) -> bytes:
        """Wraps data with a checksum and returns the wire bytes."""
        return cls.build(data = data).to_bytes()

    @classmethod
    def disassemble(cls, raw: bytes) -> bytes:
        """
        Validates the checksum and returns the data without it.
        :param raw:         Raw read response payload bytes.
        :return:            Data bytes, without checksum.
        :raises ValueError: If the checksum is invalid.
        """
        return cls.from_bytes(raw).validate().data


    ### Constructors
    @classmethod
    def build(cls, data: bytes) -> Self:
        """Constructs a payload object from logical parameters. Checksum is 0-initialised."""
        return cls(data = data)

    @classmethod
    def from_bytes(cls, raw: bytes) -> Self:
        """Parses raw bytes into a payload object. Does not validate the checksum."""
        return cls(
            data = raw[cls.Layout.data],
            checksum = raw[cls.Layout.checksum],
        )


    ### Properties
    ## Serialization
    @property
    def raw_bytes(self) -> bytes:
        return b"".join((self.data, self.checksum))


### Command Payloads
@dataclass(slots = True)
class CommandRequestPayload(BasePayload):

    ### Constants
    class Layout:
        operation_size: Final[int] = EncodingSizes.UINT32_LE_SIZE

        operation: Final[slice] = next_slice(0, operation_size)
        data: Final[slice] = next_slice(operation, None)


    ### Attributes
    operation: bytes = bytes(Layout.operation_size)
    data: bytes = b""


    ### Main
    @classmethod
    def assemble(
            cls,
            operation: CommandOperation,
            data: bytes | None = None,
    ) -> bytes:
        return cls.build(operation = operation, data = data).to_bytes()

    @classmethod
    def disassemble(cls, raw: bytes) -> tuple[CommandOperation, bytes | None]:
        """
        Parses a raw command request payload.
        :param raw: Raw command request payload bytes.
        :return:    (operation, data) tuple.
        """
        instance = cls.from_bytes(raw)
        return instance.operation_enum, instance.data or None


    ### Constructors
    @classmethod
    def build(
            cls,
            operation: CommandOperation,
            data: bytes | None = None,
    ) -> Self:
        """Constructs a payload object from logical parameters."""
        payload = cls()
        payload.operation_enum = operation
        if data is not None:
            payload.data = data
        return payload

    @classmethod
    def from_bytes(cls, raw: bytes) -> Self:
        """Parses raw bytes into a payload object."""
        return cls(
            operation = raw[cls.Layout.operation],
            data = raw[cls.Layout.data],
        )


    ### Properties
    ## Helpers
    @property
    def operation_int(self) -> int:
        return decode_int(self.operation, Encoding.UINT32_LE)

    @operation_int.setter
    def operation_int(self, value: int) -> None:
        self.operation = encode_int(value, Encoding.UINT32_LE)

    @property
    def operation_enum(self) -> CommandOperation:
        try:
            return CommandOperation(self.operation_int)
        except ValueError:
            raise ValueError(f"Unknown operation: {self.operation.hex()}")

    @operation_enum.setter
    def operation_enum(self, operation: CommandOperation) -> None:
        self.operation = encode_int(operation.value, Encoding.UINT32_LE)

    ## Serialization
    @property
    def raw_bytes(self) -> bytes:
        return b"".join((self.operation, self.data))



@dataclass(slots = True)
class CommandWithPinRequestPayload(CommandRequestPayload):

    ### Constants
    class Layout:
        operation_size: Final[int] = CommandRequestPayload.Layout.operation_size
        pin_size: Final[int] = 6

        operation: Final[slice] = next_slice(0, operation_size)
        pin: Final[slice] = next_slice(operation, pin_size)
        data: Final[slice] = next_slice(pin, None)

    PIN_PADDING: ClassVar[int] = 0xFF


    ### Attributes
    pin: bytes = Panel.DEFAULT_MASTER_PIN


    ### Main
    @classmethod
    def assemble(
            cls,
            operation: CommandOperation,
            pin: str | None = None,
            data: bytes | None = None,
    ) -> bytes:
        """Builds the payload and returns the wire bytes. No checksum is applied."""
        return cls.build(operation = operation, data = data, pin = pin).to_bytes()

    @classmethod
    def disassemble(cls, raw: bytes) -> bytes:
        """
        Parses a raw command request payload.
        :param raw: Raw command request payload bytes.
        :return:    data bytes
        """
        instance = cls.from_bytes(raw)

        return instance.data


    ### Constructors
    @classmethod
    def build(
            cls,
            operation: CommandOperation,
            pin: str | None = None,
            data: bytes | None = None,
    ) -> Self:
        """Constructs a payload object from logical parameters."""
        instance = cls()
        instance.operation_enum = operation
        if pin is not None:
            instance.pin_str = pin
        if data is not None:
            instance.data = data

        return instance

    @classmethod
    def from_bytes(cls, raw: bytes) -> Self:
        """Parses raw bytes into a payload object."""
        return cls(
            operation = raw[cls.Layout.operation],
            pin = raw[cls.Layout.pin],
            data = raw[cls.Layout.data],
        )


    ### Properties
    ## Helpers
    @property
    def pin_str(self) -> str | None:
        if self.pin == Panel.DEFAULT_MASTER_PIN:
            return None
        return self._decode_pin()

    @pin_str.setter
    def pin_str(self, pin: str) -> None:
        if not pin.isdigit():
            raise ValueError(f"PIN must contain digits only, got: {pin!r}")
        if not (1 <= len(pin) <= self.Layout.pin_size):
            raise ValueError(f"PIN must be 1–{self.Layout.pin_size} digits, got {len(pin)}.")
        encoded = [int(d) for d in pin]
        encoded += [self.PIN_PADDING] * (self.Layout.pin_size - len(pin))
        self.pin = bytes(encoded)

    ## Serialization
    @property
    def raw_bytes(self) -> bytes:
        return b"".join((self.operation, self.pin, self.data))


    ### Methods
    ## Pin
    def _decode_pin(self) -> str:
        digits = []
        for byte in self.pin:
            if byte == self.PIN_PADDING:
                break
            if byte > 9:
                raise ValueError(f"Invalid PIN byte: 0x{byte:02X}.")
            digits.append(str(byte))
        if not digits:
            raise ValueError(f"No valid digits found in PIN: {self.pin.hex(' ')}.")
        return "".join(digits)


@dataclass(slots = True)
class CommandResponsePayload(BasePayload):

    ### Constants
    class Layout:
        header_size: Final[int] = 4

        header: Final[slice] = next_slice(0, header_size)
        data: Final[slice] = next_slice(header, None)


    ### Attributes
    header: bytes = bytes(Layout.header_size)
    data: bytes = b""


    ### Main
    @classmethod
    def assemble(cls, data: bytes) -> bytes:
        return cls.build(data).to_bytes()

    @classmethod
    def disassemble(cls, raw: bytes) -> bytes:
        """Parses a raw response and returns the payload data."""
        return cls.from_bytes(raw).data


    ### Constructors
    @classmethod
    def build(cls, data: bytes) -> Self:
        return cls(data = data)

    @classmethod
    def from_bytes(cls, raw: bytes) -> Self:
        return cls(
            header = raw[cls.Layout.header],
            data = raw[cls.Layout.data],
        )


    ### Properties
    ## Serialization
    @property
    def raw_bytes(self) -> bytes:
        return self.data


@dataclass(slots = True)
class CommandWithPinResponsePayload(CommandResponsePayload):

    ### Constants
    class Layout:
        header_size: Final[int] = CommandResponsePayload.Layout.header_size
        header_with_pin_size: Final[int] = 14

        header: Final[slice] = next_slice(0, header_size)
        header_with_pin: Final[slice] = next_slice(header, header_with_pin_size)
        data: Final[slice] = next_slice(header_with_pin, None)


    ### Attributes
    header_with_pin: bytes = bytes(Layout.header_with_pin_size)


    ### Constructors
    @classmethod
    def build(cls, data: bytes) -> Self:
        return cls(data = data)

    @classmethod
    def from_bytes(cls, raw: bytes) -> Self:
        return cls(
            header = raw[cls.Layout.header],
            header_with_pin = raw[cls.Layout.header_with_pin],
            data = raw[cls.Layout.data],
        )