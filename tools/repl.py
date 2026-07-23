import asyncio

from inim.prime.native.wire import Protocol
from inim.prime.native.wire import Cipher
from inim.prime.native import operations, helpers
from inim.prime.native.models import PartitionMode
from inim.prime.native.wire.frame import Frame, OuterFrame, InnerFrame

from tools.filters import PacketFilter
from tools.packets import Packet, load_packets, decrypt_packets
from tools.utils import Config, get_yaml_config

# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

MENU = """\
Commands:
  help                      – Show this message
  load_packets              – Load packets from disk
  print_packets             – Print current (filtered) packets
  print_payloads            - Print payloads of the filtered packets
  set_filter                – Apply a filter expression to loaded packets
  current_filter            – Show the active filter (and optionally clear it)
  help_filter               – Show filter syntax reference
  resolve_address           - Resolves an address by performing an indirection lookup
  get_partition_labels      - Print partition names
  get_partition_statuses    - Print partitions statuses
  get_partitions            - Print partitions statuses
  set_partition_modes
  get_panel_info
  exit / quit               – Exit the program
"""


def print_help() -> None:
    print(MENU)


def print_packets(packets: list[Packet]) -> None:
    if not packets:
        print("No packets to display.")
        return

    for packet in packets:
        print(f"{packet.source} --> {packet.destination}")
        print(packet.frame)
        print()

def print_payloads(packets: list[Packet]) -> None:
    if not packets:
        print("No packets to display.")
        return

    for packet in packets:
        print(f"{packet.source} --> {packet.destination}")
        print(f"Operation: {packet.frame.operation_str}")
        print(f"Frame length: {packet.frame.length}")
        print(f"Payload length: {len(packet.payload)}")
        print(packet.payload.hex(" "))
        print()

# ---------------------------------------------------------------------------
# Business logic
# ---------------------------------------------------------------------------

def apply_filter(
    packets: list[Packet],
    current_filter: PacketFilter | None,
) -> tuple[list[Packet], PacketFilter | None]:
    """Prompt for a filter expression, apply it, and return (packets, filter).

    - Empty input  → clears the active filter.
    - '?'          → prints syntax reference; leaves state unchanged.
    - Valid expr   → returns filtered packets and the new PacketFilter.
    - Invalid expr → prints an error and leaves state unchanged.
    """
    print("Enter filter expression (empty to clear, '?' for help):")
    raw = input("filter> ").strip()

    if raw == "?":
        print(PacketFilter.help())
        return packets, current_filter

    if not raw:
        print("Filter cleared.")
        return packets, None

    try:
        pf = PacketFilter(raw)
        result = pf.apply(packets)
        print(f"Filter applied: {pf}  →  {len(result)} packet(s) matched.")
        return result, pf
    except ValueError as exc:
        print(f"Invalid filter: {exc}")
        return packets, current_filter

async def resolve_address(protocol: Protocol):
    address = int(input("Index: "))
    await protocol.connect()
    response_address = await operations.resolve_address(protocol, address)
    protocol.disconnect()

    print(f"Resolved address: {response_address} ({hex(response_address)})")

async def get_partition_labels(protocol: Protocol):
    await protocol.connect()
    partition_names = await operations.get_partition_labels(protocol)
    protocol.disconnect()

    print(f"{len(partition_names)} partition(s).")
    for p_id, p_name in partition_names.items():
        print(f"{p_id}\t{p_name}")
    print()

async def get_partition_statuses(protocol: Protocol):
    await protocol.connect()
    partition_statuses = await operations.get_partition_statuses(protocol)
    protocol.disconnect()

    print(f"{len(partition_statuses)} partition(s).")
    for idx, p in partition_statuses.items():
        print(idx, p)
    print()

async def get_partitions(protocol: Protocol):
    await protocol.connect()
    partitions = await helpers.get_partitions(protocol)
    protocol.disconnect()

    for p in partitions:
        print(p)
    print()

async def set_partition_modes(protocol: Protocol, pin: str | None):
    await protocol.connect()
    partition_modes: dict[int, PartitionMode] = {}

    print("Enter partition index and mode.")
    print("Type 'q' at any prompt to finish.\n")

    print("Available modes:")
    for mode in PartitionMode:
        print(f"  - {mode.name}")

    while True:
        idx_input = input("\nPartition index: ").strip()

        if idx_input.lower() == 'q':
            break

        try:
            idx = int(idx_input)
        except ValueError:
            print("Invalid partition index")
            continue

        mode_input = input(
            "Partition mode (TOTAL/PARTIAL/INSTANT/DISARMED): "
        ).strip().upper()

        if mode_input.lower() == 'q':
            break

        try:
            partition_mode = PartitionMode[mode_input]
        except KeyError:
            print("Invalid partition mode")
            continue

        partition_modes[idx] = partition_mode

        print(f"Added: partition {idx} -> {partition_mode.name}")

    if pin is not None:
        await operations.set_partition_modes(protocol, partition_modes, pin)
    else:
        await operations.set_partition_modes(protocol, partition_modes)
    await asyncio.sleep(1)
    await get_partitions(protocol)
    protocol.disconnect()


async def reset_partitions(protocol: Protocol, pin: str):
    await protocol.connect()

    partition_ids: set[int] = set()

    print("Enter partition ids to reset.")
    print("Type 'q' at any prompt to finish.\n")

    while True:
        idx_input = input("\nPartition index: ").strip()

        if idx_input.lower() == 'q':
            break

        try:
            idx = int(idx_input)
        except ValueError:
            print("Invalid partition index")
            continue

        partition_ids.add(idx)

        print(f"Added: partition {idx}")

    await operations.partitions.reset_partitions(protocol, partition_ids, pin)
    await asyncio.sleep(1)
    await get_partitions(protocol)
    protocol.disconnect()

async def get_panel_info(protocol: Protocol):
    await protocol.connect()

    serial_number, firmware, model = await operations.panel.get_panel_info(protocol)

    print(f"Serial number: {serial_number}")
    print(f"Firmware: {firmware}")
    print(f"Model: {model}")
    print()

    protocol.disconnect()



# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

async def repl(config: Config) -> None:
    packets: list[Packet] | None = None
    filtered_packets: list[Packet] | None = None
    active_filter: PacketFilter | None = None
    cipher = Cipher(config.password)
    frame_type: type[Frame] = OuterFrame if config.use_outer_frame else InnerFrame
    protocol = Protocol(
        host=config.host,
        password=config.password,
        port=config.port,
        use_outer_frame = config.use_outer_frame,
    )

    print_help()

    handlers = {
        "help":                print_help,
        "help_filter":         lambda: print(PacketFilter.help()),
    }

    while True:
        choice = input("> ").strip().lower()

        if choice in ("exit", "quit"):
            print("Goodbye.")
            break

        elif choice in handlers:
            handlers[choice]()

        elif choice == "resolve_address":
            await resolve_address(protocol)

        elif choice == "load_packets":
            try:
                packets = load_packets(frame_type)
                if packets is not None:
                    decrypt_packets(packets, cipher)

                    filtered_packets = packets
                    active_filter = None
                    print(f"Loaded {len(packets)} packet(s).")
            except Exception as exc:  # noqa: BLE001
                print(f"Error loading packets: {exc}")

        elif choice == "print_packets":
            if filtered_packets is not None:
                print_packets(filtered_packets)
            else:
                print("No packets loaded. Run 'load_packets' first.")
        elif choice == "print_payloads":
            if filtered_packets is not None:
                print_payloads(filtered_packets)
            else:
                print("No packets loaded. Run 'load_packets' first.")
        elif choice == "set_filter":
            if packets is None:
                print("No packets loaded. Run 'load_packets' first.")
            else:
                filtered_packets, active_filter = apply_filter(packets, active_filter)

        elif choice == "current_filter":
            if active_filter is None:
                print("No active filter.")
            else:
                print(f"Active filter: {active_filter}")
                if input("Clear it? [y/N] ").strip().lower() == "y":
                    filtered_packets = packets
                    active_filter = None
                    print("Filter cleared.")
        elif choice == "get_partition_labels":
            await get_partition_labels(protocol)
        elif choice == "get_partition_statuses":
            await get_partition_statuses(protocol)
        elif choice == "get_partitions":
            await get_partitions(protocol)
        elif choice == "set_partition_modes":
            await set_partition_modes(protocol, config.pin)
        elif choice == "get_panel_info":
            await get_panel_info(protocol)

        else:
            print(f"Unknown command '{choice}'. Type 'help' for a list of commands.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    config = get_yaml_config()
    await repl(config)


if __name__ == "__main__":
    asyncio.run(main())