from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Self, Final

from inim.prime.native.const import Encoding, FrameOperation, EncodingSizes
from inim.prime.native.utils import next_slice, decode_int, encode_int


@dataclass(slots = True)
class Header(ABC):

    ### Constants
    class Layout:
        size: int

    @property
    @abstractmethod
    def inner_body_length(self) -> int:
        ...

    @classmethod
    @abstractmethod
    def from_bytes(
            cls,
            header: bytes
    ) -> Self:
        ...

    @property
    @abstractmethod
    def raw_bytes(self) -> bytes:
        ...


@dataclass(slots = True)
class OuterHeader(Header):

    ### Constants
    class Layout:
        magic_size: Final[int] = 2
        padding_size: Final[int] = 2
        inner_frame_length_size: Final[int] = EncodingSizes.UINT32_LE_SIZE
        response_inner_frame_length_size: Final[int] = EncodingSizes.UINT32_LE_SIZE

        size: Final[int] = (
                magic_size
                + padding_size
                + inner_frame_length_size
                + response_inner_frame_length_size
        )

        magic: Final[slice] = next_slice(0, magic_size)
        padding: Final[slice] = next_slice(magic, padding_size)
        inner_frame_length: Final[slice] = next_slice(padding, inner_frame_length_size)
        response_inner_frame_length: Final[slice] = next_slice(inner_frame_length, response_inner_frame_length_size)

    MAGIC: ClassVar[bytes] = b"\x50\x53"
    RESPONSE_INNER_FRAME_LENGTH_DEFAULT: ClassVar[int] = 0


    ### Attributes
    # Magic                        [0:2]     0x50 0x53       raw
    # Padding                      [2:4]     0-initialised   raw
    # Inner frame length           [4:8]     0-initialised   uint32 LE
    # Response inner frame length  [8:12]    0-initialised   uint32 LE
    magic: bytes = MAGIC
    padding: bytes = bytes(Layout.padding_size)
    inner_frame_length: bytes = bytes(Layout.inner_frame_length_size)
    response_inner_frame_length: bytes = bytes(Layout.response_inner_frame_length_size)


    ### Constructors
    @classmethod
    def build(
            cls,
            inner_frame_length: int,
            response_inner_frame_length: int,
    ) -> Self:
        outer_header = cls()
        outer_header.inner_frame_length_int = inner_frame_length
        outer_header.response_inner_frame_length_int = response_inner_frame_length
        return outer_header

    @classmethod
    def from_bytes(
            cls,
            header: bytes
    ) -> Self:
        return cls(
            magic = header[cls.Layout.magic],
            padding = header[cls.Layout.padding],
            inner_frame_length = header[cls.Layout.inner_frame_length],
            response_inner_frame_length = header[cls.Layout.response_inner_frame_length],
        )


    ### Properties
    ## Header
    @property
    def inner_body_length(self) -> int:
        return self.inner_frame_length_int

    ## Helper
    @property
    def inner_frame_length_int(self) -> int:
        return decode_int(self.inner_frame_length, Encoding.UINT32_LE)

    @inner_frame_length_int.setter
    def inner_frame_length_int(self, value: int) -> None:
        self.inner_frame_length = encode_int(value, Encoding.UINT32_LE)

    @property
    def response_inner_frame_length_int(self) -> int:
        return decode_int(self.response_inner_frame_length, Encoding.UINT32_LE)

    @response_inner_frame_length_int.setter
    def response_inner_frame_length_int(self, value: int) -> None:
        self.response_inner_frame_length = encode_int(value, Encoding.UINT32_LE)

    ## Serialization
    @property
    def raw_bytes(self) -> bytes:
        return b"".join((
            self.magic,
            self.padding,
            self.inner_frame_length,
            self.response_inner_frame_length,
        ))

    ## Validation
    @property
    def is_magic_valid(self) -> bool:
        """True if magic bytes match 0x5053."""
        return self.magic == OuterHeader.MAGIC

    @property
    def is_padding_valid(self) -> bool:
        """True if padding bytes are 0x0000."""
        return self.padding == bytes(OuterHeader.Layout.padding_size)

    @property
    def is_valid(self) -> bool:
        """True if all validation checks pass."""
        return (
            self.is_magic_valid
            and self.is_padding_valid
        )


    ### To String
    def to_str(self, indent: int = 0) -> str:
        pad = " " * indent
        return (
            f"{pad}OuterHeader\n"
            f"{pad}  magic                        {self.magic.hex()}\n"
            f"{pad}  padding                      {self.padding.hex()}\n"
            f"{pad}  inner_frame_length           {self.inner_frame_length.hex():<12}  ({self.inner_frame_length_int})\n"
            f"{pad}  response_inner_frame_length  {self.response_inner_frame_length.hex():<12}  ({self.response_inner_frame_length_int})\n"
        )

    def __str__(self) -> str:
        return self.to_str()


    ### Methods
    ## Validation
    def validate(self) -> None:
        """
        Validates raising ValueError on the first failed check.
        :raises ValueError: If a checked property fails the check.
        """
        if not self.is_magic_valid:
            raise ValueError(
                f"Outer header magic mismatch: expected {OuterHeader.MAGIC.hex()}, "
                f"got {self.magic.hex()}."
            )
        if not self.is_padding_valid:
            raise ValueError(
                f"Outer header padding mismatch: expected {bytes(OuterHeader.Layout.padding_size).hex()}, "
                f"got {self.padding.hex()}."
            )


@dataclass(slots = True)
class InnerHeader(Header):

    ### Constants
    class Layout:
        magic_size: Final[int] = 2
        crc_size: Final[int] = EncodingSizes.UINT16_LE_SIZE
        operation_size: Final[int] = EncodingSizes.UINT16_LE_SIZE
        inner_frame_length_size: Final[int] = EncodingSizes.UINT32_LE_SIZE

        size: Final[int] = (
                magic_size
                + crc_size
                + operation_size
                + inner_frame_length_size
        )

        magic: Final[slice] = next_slice(0, magic_size)
        crc: Final[slice] = next_slice(magic, crc_size)
        operation: Final[slice] = next_slice(crc, operation_size)
        inner_frame_length: Final[slice] = next_slice(operation, inner_frame_length_size)

    MAGIC: ClassVar[bytes] = b"\x50\x50"


    ### Attributes
    # Magic                 [0:2]     0x50 0x50       raw
    # CRC-16/ARC            [2:4]     0-initialised   uint16 LE
    # FrameOperation             [4:6]     0-initialised   raw
    # Inner frame length    [6:10]    0-initialised   uint32 LE
    magic: bytes = MAGIC
    crc: bytes = bytes(Layout.crc_size)
    operation: bytes = bytes(Layout.operation_size)
    inner_frame_length: bytes = bytes(Layout.inner_frame_length_size)


    ### Constructors
    @classmethod
    def build(
            cls,
            operation: FrameOperation,
            inner_frame_length: int,
    ) -> Self:
        inner_header = cls()
        inner_header.operation_enum = operation
        inner_header.inner_frame_length_int = inner_frame_length

        return inner_header

    @classmethod
    def from_bytes(
            cls,
            header: bytes
    ) -> Self:
        return cls(
            magic = header[cls.Layout.magic],
            crc = header[cls.Layout.crc],
            operation = header[cls.Layout.operation],
            inner_frame_length = header[cls.Layout.inner_frame_length],
        )


    ### Properties
    ## Header
    @property
    def inner_body_length(self) -> int:
        return self.inner_frame_length_int - self.Layout.size

    ## Helper
    @property
    def inner_frame_length_int(self) -> int:
        return decode_int(self.inner_frame_length, Encoding.UINT32_LE)

    @inner_frame_length_int.setter
    def inner_frame_length_int(self, value: int) -> None:
        self.inner_frame_length = encode_int(value, Encoding.UINT32_LE)

    @property
    def crc_int(self) -> int:
        """Inner header CRC value as an integer (uint16 LE)."""
        return decode_int(self.crc, Encoding.UINT16_LE)

    @crc_int.setter
    def crc_int(self, value: int) -> None:
        self.crc = encode_int(value, Encoding.UINT16_LE)

    @property
    def operation_enum(self) -> FrameOperation | None:
        """Return operation as enum."""
        try:
            return FrameOperation(self.operation)
        except ValueError:
            raise ValueError(f"Unknown operation: {self.operation.hex()}")

    @operation_enum.setter
    def operation_enum(self, operation: FrameOperation) -> None:
        self.operation = operation.value

    @property
    def operation_str(self) -> str:
        try:
            op = self.operation_enum
            assert op is not None
            return op.name
        except ValueError:
            return "UNKNOWN"

    ## Serialization
    @property
    def raw_bytes(self) -> bytes:
        return b"".join((
            self.magic,
            self.crc,
            self.operation,
            self.inner_frame_length,
        ))

    ## Validation
    @property
    def is_magic_valid(self) -> bool:
        """True if magic bytes match 0x5050."""
        return self.magic == InnerHeader.MAGIC

    @property
    def is_valid(self) -> bool:
        """True if all validation checks pass."""
        return (
            self.is_magic_valid
        )


    ## To String
    def to_str(self, indent: int = 0) -> str:
        pad = " " * indent
        return (
            f"{pad}InnerHeader\n"
            f"{pad}  magic                      {self.magic.hex()}\n"
            f"{pad}  crc                        {self.crc.hex():<12}  (0x{self.crc_int:04X})\n"
            f"{pad}  operation                  {self.operation.hex()} ({self.operation_str})\n"
            f"{pad}  inner_frame_length         {self.inner_frame_length.hex():<12}  ({self.inner_frame_length_int})\n"
        )

    def __str__(self) -> str:
        return self.to_str()


    ### Methods
    ## Validation
    def validate(self) -> None:
        """
        Validates the frame raising ValueError on the first failed check.
        :raises ValueError: If a checked property fails the check.
        """
        if not self.is_magic_valid:
            raise ValueError(
                f"Inner header magic mismatch: expected {InnerHeader.MAGIC.hex()}, "
                f"got {self.magic.hex()}."
            )
