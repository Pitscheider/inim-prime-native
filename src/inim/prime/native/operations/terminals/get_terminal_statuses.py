from typing import Final

from inim.prime.native.const import Encoding, CommandOperation
from inim.prime.native.models.terminals import TerminalStatus
from inim.prime.native.operations.terminals.const import TERMINAL_IDS_INTERVAL
from inim.prime.native.utils import encode_int, Interval
from inim.prime.native.wire.payload import CommandWithPinRequestPayload
from inim.prime.native.wire.protocol import Protocol

### Constants
TERMINAL_STATUS_SIZE: Final[int] = 10
MAX_CHUNK_TERMINALS: Final[int] = 20
RESPONSE_PAYLOAD_DATA_LENGTH: Final[int] = TERMINAL_STATUS_SIZE * MAX_CHUNK_TERMINALS
COMMAND_OPERATION: Final[CommandOperation] = CommandOperation.GET_TERMINAL_STATUSES

### Functions


def assemble_data(start_terminal: int, end_terminal: int) -> bytes:
    return b"".join((
        encode_int(start_terminal, Encoding.UINT16_LE),
        encode_int(end_terminal, Encoding.UINT16_LE),
    ))

def assemble_payload(start_terminal: int, end_terminal: int, pin: str | None = None) -> bytes:
    return CommandWithPinRequestPayload.assemble(
        COMMAND_OPERATION,
        pin = pin,
        data = assemble_data(start_terminal, end_terminal),
    )

def disassemble_payload(
        start_terminal: int,
        end_terminal: int,
        response_data: bytes
) -> dict[int, TerminalStatus]:
    terminal_statuses: dict[int, TerminalStatus] = {}

    for idx, t_id in enumerate(
            range(start_terminal, end_terminal, 1),
            start = 0,
    ):
        offset = idx * TERMINAL_STATUS_SIZE
        raw_status = response_data[offset:offset + TERMINAL_STATUS_SIZE]
        terminal_type = TerminalStatus.decode_type(raw_status)

        terminal_statuses[t_id] = TerminalStatus(
            raw = raw_status,
            type = terminal_type,
        )


    return terminal_statuses

async def get_chunk(
    protocol: Protocol,
    start_terminal: int,
    end_terminal: int,
    pin: str | None = None,
) -> dict[int, TerminalStatus]:


    response = await protocol.execute_command_with_pin(
        COMMAND_OPERATION,
        assemble_data(start_terminal, end_terminal),
        pin,
    )

    return disassemble_payload(start_terminal, end_terminal, response)

async def get_chunks(
    protocol: Protocol,
    start_terminal: int,
    end_terminal_ex: int,
    pin: str | None = None,
) -> dict[int, TerminalStatus]:

    chunks: dict[int, TerminalStatus] = {}

    for start_i in range(start_terminal, end_terminal_ex, MAX_CHUNK_TERMINALS):
        end_i = min(start_i + MAX_CHUNK_TERMINALS, end_terminal_ex)

        chunks |= await get_chunk(protocol, start_i, end_i, pin)

    return chunks

async def get_terminal_statuses(
        protocol: Protocol,
        interval: Interval = TERMINAL_IDS_INTERVAL,
        pin: str | None = None,
) -> dict[int, TerminalStatus]:
    chunks = await get_chunks(
        protocol = protocol,
        start_terminal = interval.start,
        end_terminal_ex = interval.end + 1,
        pin = pin,
    )

    return chunks
