from typing import Final

ARMING_SCENARIOS_MAX_NUMBER: Final[int] = 50
LAST_ARMING_SCENARIO_ID: Final[int] = ARMING_SCENARIOS_MAX_NUMBER - 1

ARMING_SCENARIO_RECORD_SIZE: Final[int] = 19
# One nibble per partition: 30 partitions -> 15 bytes (bytes 0-14).
# Bytes 15-18: unknown.
ARMING_SCENARIO_MODES_SIZE: Final[int] = 15