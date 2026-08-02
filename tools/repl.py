import asyncio

from inim.prime.native.client import Client
from inim.prime.native.models.partitions import ArmingStatus
from inim.prime.native.models.zones import ZoneTerminal
from inim.prime.native.wire.cipher import Cipher
from inim.prime.native.wire.frame import Frame, OuterFrame, InnerFrame
from tools.filters import PacketFilter
from tools.packets import Packet, load_packets, decrypt_packets
from tools.utils import Config, get_yaml_config

# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

MENU = """\
Commands:
    help                          – Show this message
    
    DEVELOPMENT OPERATIONS
    load_packets                  – Load packets from disk
    print_packets                 – Print current (filtered) packets
    print_payloads                - Print payloads of the filtered packets
    set_filter                    – Apply a filter expression to loaded packets
    current_filter                – Show the active filter (and optionally clear it)
    help_filter                   – Show filter syntax reference
    
    PANEL OPERATIONS
    get_terminals                 - Print terminals info updated
    get_partitions                - Print partitions updated
    set_partition_arming_statuses - Set the arming state for partitions
    reset_partition_memory        - Reset partition memory
    set_zone_bypass               - Set bypass state for a zone
    set_output_status             - Set output state
    get_panel_info                - Print panel info
    
    exit / quit                   – Exit the program
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



async def get_partitions(client: Client):
    await client.ensure_initialized()

    partitions = await client.update_partitions()

    for p in partitions.values():
        print(p)
    print()

async def set_arming_statuses(client: Client):
    await client.ensure_initialized()

    arming_statuses: dict[int, ArmingStatus] = {}

    print("Enter partition index and mode.")
    print("Type 'q' at any prompt to finish.\n")

    print("Available modes:")
    for mode in ArmingStatus:
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
            "Arming state (ARM_AWAY/ARM_STAY/ARM_INSTANT/DISARMED): "
        ).strip().upper()

        if mode_input.lower() == 'q':
            break

        try:
            arming_status = ArmingStatus[mode_input]
        except KeyError:
            print("Invalid arming state")
            continue

        arming_statuses[idx] = arming_status

        print(f"Added: partition {idx} -> {arming_status.name}")


    await client.set_partition_arming_statuses(arming_statuses)
    await get_partitions(client)



async def get_panel_info(client: Client):
    await client.ensure_initialized()

    serial_number, firmware, model = client.panel_info

    print(f"Serial number: {serial_number}")
    print(f"Firmware: {firmware}")
    print(f"Model: {model}")
    print()


async def set_zone_bypass(client: Client):
    await client.ensure_initialized()

    idx = int(input("Zone ID: "))
    bypass = input("Bypass [True/False]: ")
    if bypass.lower() == "true":
        bypass = True
    else:
        bypass = False
    print(f"Chose {bypass}")

    await client.set_zone_bypass(idx, bypass)


async def rest_partition(client: Client):
    await client.ensure_initialized()
    idx = int(input("Partition index: "))
    await client.reset_partition_memory(idx)

async def set_output_status(client: Client):
    await client.ensure_initialized()

    idx = int(input("Output ID: "))
    enable = input("Enable/Disable [True/False]: ")
    if enable.lower() == "true":
        enable = True
    else:
        enable = False
    print(f"Chose {enable}")

    await client.set_output(idx, enable)

async def get_terminals(client: Client):
    await client.ensure_initialized()

    terminals = await client.update_terminals()
    partitions = client.partitions

    partition_labels = {
        partition_id: partition.label
        for partition_id, partition in partitions.items()
    }

    for terminal in terminals.values():
        if isinstance(terminal, ZoneTerminal):
            print(terminal.to_string_partition_labels(partition_labels))
        else:
            print(terminal)

# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

async def repl(config: Config) -> None:
    packets: list[Packet] | None = None
    filtered_packets: list[Packet] | None = None
    active_filter: PacketFilter | None = None
    cipher = Cipher(config.password)
    frame_type: type[Frame] = OuterFrame if config.use_outer_frame else InnerFrame

    client = client = await Client(
        host = config.host,
        password = config.password,
        use_outer_frame = config.use_outer_frame,
        port = config.port,
        pin = config.pin,
    ).connect()

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

        elif choice == "get_partitions":
            await get_partitions(client)
        elif choice == "set_partition_arming_statuses":
            await set_arming_statuses(client)
        elif choice == "set_zone_bypass":
            await set_zone_bypass(client)
        elif choice == "set_output_status":
            await set_output_status(client)
        elif choice == "reset_partition_memory":
            await rest_partition(client)
        elif choice == "get_panel_info":
            await get_panel_info(client)
        elif choice == "get_terminals":
            await get_terminals(client)

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