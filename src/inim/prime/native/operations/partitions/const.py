from typing import Final

from inim.prime.native.models import ArmingStatus

PARTITIONS_MAX_NUMBER: Final[int] = 30

ARMING_STATUS_MAP = {
    0x01: ArmingStatus.ARM_AWAY,
    0x02: ArmingStatus.ARM_STAY,
    0x03: ArmingStatus.ARM_INSTANT,
    0x04: ArmingStatus.DISARMED,
}

ARMING_STATUS_REVERSE_MAP = {
    value: key for key, value in ARMING_STATUS_MAP.items()
}