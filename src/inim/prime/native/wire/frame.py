from __future__ import annotations

from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import Self, ClassVar, Final

from inim.prime.native.const import FrameOperation
from inim.prime.native.utils import round_up_to_block, crc16_arc, next_slice
from .cipher import Cipher
from .header import Header, OuterHeader, InnerHeader



@dataclass(slots = True)
class Frame(ABC):

    header: Header

    ### Abstract
    @property
    @abstractmethod
    def raw_bytes(self) -> bytes:
        """
        :return: Current frame bytes assembled from field values in wire order, without recomputing parameters.
        """
        ...

    @abstractmethod
    def to_bytes(self) -> bytes:
        """
        Recomputes meaningful parameters from current field values if necessary.
        Then assembles the complete wire frame as bytes.
        :return: Assembled frame bytes with recomputed parameters.
        """
        ...

    @property
    @abstractmethod
    def length(self) -> int:
        """
        :return: Frame length.
        """
        ...

    @property
    @abstractmethod
    def operation(self) -> bytes:
        """Return operation bytes."""
        ...

    @property
    @abstractmethod
    def is_valid(self) -> bool:
        """True if all validation checks pass."""
        ...

    @property
    @abstractmethod
    def encrypted_payload(self) -> bytes:
        """
        :return: Encrypted payload.
        """
        ...

    @classmethod
    @abstractmethod
    def from_bytes(
            cls,
            frame_bytes: bytes,
    ) -> Self:
        """
        Parses a raw bytes frame into a Frame instance.
        Does not validate the frame.
        :param frame_bytes:     Raw bytes of the frame to parse.
        :return:                The constructed frame object.
        """
        ...

    @property
    @abstractmethod
    def operation_str(self) -> str:
        """Returns frame operation as string."""
        ...

    ### Properties
    @property
    def header_type(self) -> type[Header]:
        return type(self.header)

    @property
    def encrypted_payload_length(self) -> int:
        """
        :return: Encrypted payload length.
        """
        return len(self.encrypted_payload)


@dataclass(slots = True)
class InnerFrame(Frame):

    ### Constants
    class Layout:
        inner_header_size: Final[int] = InnerHeader.Layout.size

        inner_header: Final[slice] = next_slice(0, inner_header_size)
        encrypted_payload: Final[slice] = next_slice(inner_header, None)

    CRC_COVERAGE: ClassVar[slice] = slice(InnerHeader.Layout.operation.start, None)
    MIN_SIZE: ClassVar[int] = InnerHeader.Layout.size + Cipher.AES_BLOCK_SIZE


    ### Attributes
    header: InnerHeader
    encrypted_payload: bytes


    ### Main methods
    @classmethod
    def assemble(
            cls,
            encrypted_payload: bytes,
            operation: FrameOperation,
    ) -> bytes:
        """
        Assembles a raw inner frame from meaningful parameters, computes CRC, and returns it as bytes.
        :param encrypted_payload:           AES-128-CBC ciphertext to embed.
        :param operation:                   FrameOperation type.
        :return: The constructed inner frame as bytes.
        """
        inner_frame = cls.build(
            encrypted_payload = encrypted_payload,
            operation = operation,
        )

        return inner_frame.to_bytes()

    @classmethod
    def disassemble(
            cls,
            inner_frame_bytes: bytes,
    ) -> bytes:
        """
        Disassembles a raw inner frame, validates its integrity, and returns the encrypted payload.
        :param inner_frame_bytes:   Raw inner frame bytes.
        :return:                    The encrypted payload as bytes.
        :raises ValueError:         If the validation of the frame fails.
        """
        inner_frame = cls.from_bytes(inner_frame_bytes)
        inner_frame.validate()
        return inner_frame.encrypted_payload


    ### Constructors
    @classmethod
    def build(
            cls,
            encrypted_payload: bytes,
            operation: FrameOperation,
    ) -> Self:
        """
        Constructs an inner frame from meaningful parameters.
        CRC is 0-initialised.
        :param encrypted_payload:           AES-128-CBC ciphertext to embed.
        :param operation:                   FrameOperation type.
        :return: The constructed frame object.
        """
        inner_frame_length = InnerHeader.Layout.size + len(encrypted_payload)

        inner_frame = cls(
            header = InnerHeader.build(
                operation = operation,
                inner_frame_length = inner_frame_length,
            ),
            encrypted_payload = encrypted_payload,
        )

        return inner_frame

    @classmethod
    def from_bytes(cls, frame_bytes: bytes) -> Self:
        """
        Parses a raw bytes frame into an InnerFrame instance.
        Does not validate the inner frame.
        :param frame_bytes:   Raw bytes of the inner frame to parse.
        :return:                    The constructed inner frame object.
        """
        inner_header = frame_bytes[cls.Layout.inner_header]
        encrypted_payload = frame_bytes[cls.Layout.encrypted_payload]

        return cls(
            header = InnerHeader.from_bytes(inner_header),
            encrypted_payload = encrypted_payload,
        )


    ### Properties
    ## Validation properties
    @property
    def is_size_valid(self) -> bool:
        """True if the encrypted payload meets the minimum valid size."""
        return len(self.encrypted_payload) >= Cipher.AES_BLOCK_SIZE

    @property
    def is_inner_frame_length_valid(self) -> bool:
        """True if inner_frame_length_inner matches the actual inner frame size."""
        actual = InnerHeader.Layout.size + len(self.encrypted_payload)
        return self.header.inner_frame_length_int == actual

    @property
    def is_crc_valid(self) -> bool:
        """True if the declared CRC matches the value calculated from current fields."""
        return self.header.crc_int == self.calculate_crc()

    @property
    def is_valid(self) -> bool:
        """True if all validation checks pass."""
        return (
                self.is_size_valid
                and self.header.is_magic_valid
                and self.is_inner_frame_length_valid
                and self.is_crc_valid
        )

    @property
    def length(self) -> int:
        """
        :return: Inner frame length.
        """
        return InnerHeader.Layout.size + self.encrypted_payload_length

    @property
    def operation(self) -> bytes:
        """Return operation bytes."""
        return self.header.operation

    ## Serialization
    @property
    def raw_bytes(self) -> bytes:
        """
        :return: Current inner frame bytes assembled from field values in wire order, without recomputing CRC.
        """
        return b"".join((
            self.header.raw_bytes,
            self.encrypted_payload,
        ))

    @property
    def operation_str(self) -> str:
        """Returns frame operation as string."""
        return self.header.operation_str


    ### To String
    def to_str(self, indent: int = 0) -> str:
        pad = " " * indent
        payload_hex = self.encrypted_payload.hex()
        if len(payload_hex) > 64:
            payload_hex = payload_hex[:64] + f"..."

        return (
            f"{pad}InnerFrame\n"
            f"{self.header.to_str(indent + 2)}"
            f"{pad}  Encrypted Payload ({self.encrypted_payload_length})\n"
            f"{pad}    encrypted_payload          {payload_hex}\n"
        )

    def __str__(self) -> str:
        return self.to_str()


    ### Methods
    def validate(self) -> None:
        """
        Validates the inner frame raising ValueError on the first failed check.
        :raises ValueError: If a checked property fails the check.
        """
        self.header.validate()
        if not self.is_size_valid:
            raise ValueError(f"Encrypted payload too short: need ≥ {Cipher.AES_BLOCK_SIZE} bytes.")
        if not self.is_inner_frame_length_valid:
            actual = InnerHeader.Layout.size + len(self.encrypted_payload)
            raise ValueError(
                f"Inner frame length mismatch: "
                f"declared {self.header.inner_frame_length_int}, actual {actual}."
            )
        if not self.is_crc_valid:
            raise ValueError(
                f"CRC mismatch: declared 0x{self.header.crc_int:04X}, "
                f"computed 0x{self.calculate_crc():04X}."
            )

    ## CRC
    def calculate_crc(self) -> int:
        """
        :return: Calculated CRC-16/ARC from current field values.
        """
        return crc16_arc(
            self.raw_bytes[self.CRC_COVERAGE]
        )

    def update_crc(self) -> Self:
        """
        Updates the stored CRC bytes to match the value calculated from current fields.
        :return: Self with updated CRC-16/ARC from current fields.
        """
        self.header.crc_int = self.calculate_crc()
        return self

    ## Serialization
    def to_bytes(self) -> bytes:
        """
        Recomputes CRC from current field values then assembles the complete wire inner frame as bytes.
        :return: Assembled inner frame bytes with updated CRC.
        """
        self.update_crc()
        return self.raw_bytes


@dataclass(slots = True)
class OuterFrame(Frame):

    ### Constants
    class Layout:
        outer_header_size: Final[int] = OuterHeader.Layout.size

        outer_header: Final[slice] = next_slice(0, outer_header_size)
        inner_frame: Final[slice] = next_slice(outer_header, None)

    MIN_SIZE: ClassVar[int] = OuterHeader.Layout.size + InnerFrame.MIN_SIZE


    ### Attributes
    header: OuterHeader
    inner_frame: InnerFrame


    ### Main methods
    @classmethod
    def assemble(
            cls,
            inner_frame: InnerFrame,
            response_payload_length: int | None = None,
    ) -> bytes:
        """
        Assembles a raw outer frame from meaningful parameters, computes CRC, and returns it as bytes.
        :param inner_frame:                 Inner frame instance.
        :param response_payload_length:     Expected length of the response plaintext payload.
        :return: The constructed outer frame as bytes.
        """
        frame = cls.build(
            inner_frame = inner_frame,
            response_payload_length = response_payload_length,
        )

        return frame.to_bytes()

    @classmethod
    def disassemble(
            cls,
            frame_bytes: bytes,
    ) -> bytes:
        """
        Disassembles a raw outer frame, validates its integrity, and returns the encrypted payload.
        :param frame_bytes: Raw frame bytes.
        :return:            The encrypted payload as bytes.
        :raises ValueError: If the validation of the frame fails.
        """
        frame = cls.from_bytes(frame_bytes)
        frame.validate()
        return frame.inner_frame.encrypted_payload


    ### Constructors
    @classmethod
    def build(
            cls,
            inner_frame: InnerFrame,
            response_payload_length: int | None = None,
    ) -> Self:
        """
        Constructs an outer frame from meaningful parameters.
        CRC is 0-initialised.
        :param inner_frame:                 Inner frame instance.
        :param response_payload_length:     Expected length of the response plaintext payload.
        :return: The constructed outer frame object.
        """
        inner_frame_length = inner_frame.header.inner_frame_length_int

        if response_payload_length is not None:
            response_inner_frame_length = round_up_to_block(response_payload_length, Cipher.AES_BLOCK_SIZE) + InnerHeader.Layout.size
        else:
            response_inner_frame_length = OuterHeader.RESPONSE_INNER_FRAME_LENGTH_DEFAULT

        frame = cls(
            header = OuterHeader.build(
                inner_frame_length = inner_frame_length,
                response_inner_frame_length = response_inner_frame_length,
            ),
            inner_frame = inner_frame,
        )

        return frame

    @classmethod
    def from_bytes(cls, frame_bytes: bytes) -> Self:
        """
        Parses a raw bytes outer frame into a OuterFrame instance.
        Does not validate the frame.
        :param frame_bytes:     Raw bytes of the outer frame to parse.
        :return:                The constructed frame object.
        """
        outer_header = frame_bytes[cls.Layout.outer_header]
        inner_frame = frame_bytes[cls.Layout.inner_frame]

        return cls(
            header = OuterHeader.from_bytes(outer_header),
            inner_frame = InnerFrame.from_bytes(inner_frame),
        )

    ### Properties
    ## Helper
    @property
    def encrypted_payload(self) -> bytes:
        """
        :return: Encrypted payload.
        """
        return self.inner_frame.encrypted_payload

    @property
    def length(self) -> int:
        """
        :return: Outer frame length.
        """
        return OuterHeader.Layout.size + self.inner_frame.length

    @property
    def operation(self) -> bytes:
        """Return operation bytes."""
        return self.inner_frame.operation

    @property
    def operation_str(self) -> str:
        """Returns frame operation as string."""
        return self.inner_frame.operation_str

    ## Serialization
    @property
    def raw_bytes(self) -> bytes:
        """
        :return: Current outer frame bytes assembled from field values in wire order, without recomputing CRC.
        """
        return b"".join((
            self.header.raw_bytes,
            self.inner_frame.raw_bytes,
        ))

    ## Validation properties
    @property
    def is_inner_frame_length_consistent(self) -> bool:
        """True if both headers declare the same inner frame length."""
        return self.header.inner_frame_length_int == self.inner_frame.header.inner_frame_length_int

    @property
    def is_valid(self) -> bool:
        """True if all validation checks pass."""
        return (
            self.header.is_valid
            and self.inner_frame.is_valid
            and self.is_inner_frame_length_consistent
        )


    ### To String
    def to_str(self, indent: int = 0) -> str:
        pad = " " * indent
        return (
            f"{pad}OuterFrame\n"
            f"{self.header.to_str(indent + 2)}"
            f"{self.inner_frame.to_str(indent + 2)}"
        )

    def __str__(self) -> str:
        return self.to_str()

    ### Methods
    ## Validation
    def validate(self) -> None:
        """
        Validates the outer frame raising ValueError on the first failed check.
        :raises ValueError: If a checked property fails the check.
        """
        self.header.validate()
        self.inner_frame.validate()
        if not self.is_inner_frame_length_consistent:
            raise ValueError(
                f"Inner frame length inconsistency: "
                f"outer = {self.header.inner_frame_length_int}, "
                f"inner = {self.inner_frame.header.inner_frame_length_int}."
            )

    ## Serialization
    def to_bytes(self) -> bytes:
        """
        Recomputes CRC from current field values then assembles the complete wire outer frame as bytes.
        :return: Assembled outer frame bytes with updated CRC.
        """
        return b"".join((
            self.header.raw_bytes,
            self.inner_frame.to_bytes(),
        ))
