from inim.prime.native.firmware import FirmwareProfile
from inim.prime.native.operations.base import get_labels
from inim.prime.native.utils import Interval
from inim.prime.native.wire.protocol import Protocol


async def get_output_labels(
        protocol: Protocol,
        profile: FirmwareProfile,
        interval: Interval | None = None,
) -> dict[int, str]:
    # Labels are indexed from the first output terminal, not from terminal 0
    return await get_labels(
        protocol,
        interval or profile.output_terminal_ids,
        profile.memory.output_labels,
        -profile.output_terminal_ids.start,
    )