# inim-prime-native

An unofficial Python library for communicating with **Inim Prime** alarm panels using the native binary protocol, the same protocol used by the official Inim Prime/STUDIO software.

> **Legal notice:** This library was developed through passive observation of network traffic between Inim Prime/STUDIO and an Inim Prime panel owned by the author, for personal interoperability purposes. No proprietary code or firmware was decompiled or reproduced. This work is published in good faith under the GNU GPL v3.0. See [LEGAL.md](LEGAL.md) for a full statement.

> **Status: early / experimental.**
> The wire layer is functional. A small set of operations (partition control, panel info) are implemented. A unified client class does not yet exist. The API surface will change. This is an initial publication to share the protocol research, not a production-ready library.

---

## Background

Inim alarm panels can be controlled via an HTTP-based API when a Prime LAN network card is installed. I previously developed a Python library for interacting with a Prime panel using this interface: https://github.com/Pitscheider/inim-prime-primelan.

In practice, however, this API is slow, incomplete, and partially unreliable on certain firmware versions (e.g. 4.07). The native protocol used by Inim Prime STUDIO communicates directly over TCP and is significantly faster and more capable.

No public specification exists for this native protocol. This library was developed through analysis of network communications between Inim Prime/STUDIO and an Inim Prime panel owned by the author, captured using Wireshark on a local network.

The goal is to provide a Home Assistant integration that communicates with Inim Prime panels using this native protocol.

---

## What Is Implemented

**Wire layer** (`inim/prime/native/wire/`)

- AES-128-CBC encryption and decryption, with key and IV derived from the panel password
- CRC-16/ARC frame integrity checking
- Frame assembly and disassembly (outer header, inner header, encrypted payload)
- Read request and response payloads, with 8-bit additive checksum
- Command request and response payloads
- Async TCP transport with connection lifecycle, rate limiting, and chunked memory reads

**Operations** (`inim/prime/native/operations/`)

- `get_panel_info` — serial number, firmware version, model
- `get_partition_names` — names of configured partitions
- `get_partition_statuses` — current armed mode and alarm state per partition
- `get_partitions` — combined names and statuses
- `set_partition_arming_statuses` — arm or disarm partitions (total, partial, instant, disarmed)
- `reset_partition_memories` — reset partition alarm state
- `resolve_address` — internal address indirection lookup

**Developer tools** (`tools/`)

- A REPL for interactive exploration of a live panel
- A pcap loader and packet inspector for analysing Wireshark captures
- A packet filter DSL for navigating captured traffic

---

## What Is Not Yet Implemented

- A unified `Client` class, currently callers must manage a `Protocol` instance directly
- Zone state (sensors, detectors)
- Output control
- Event log reading
- Complete handling of the command response envelope
- Proper packaging (`pyproject.toml`, etc.)

---

## Protocol Notes

The protocol runs over TCP, default port `6004`. Each message is a frame composed of:

- A 12-byte outer header (magic `0x5053`, frame length fields)
- A 10-byte inner header (magic `0x5050`, CRC-16/ARC, operation type, frame length)
- An AES-128-CBC encrypted payload

The encryption key and IV are derived deterministically from the panel password. The IV is not random, it is defined by the panel's own derivation scheme and cannot be changed without breaking compatibility.

Read operations carry an 8-bit additive checksum in the plaintext payload. Command operations do not.

Memory reads support chunking up to 1024 bytes per request. Larger reads are split and merged transparently.

---

## Requirements

- Python 3.11+
- `pycryptodome` (AES encryption)
- `pyyaml` (configuration)
- `scapy` (optional, developer tools only — for pcap analysis)

---

## Configuration

The REPL and tools read from a `config.yaml` file in the project root:

```yaml
host: 192.168.1.100   # IP address of your panel
password: yourpass    # Panel connection password (default: pass)
port: 6004            # TCP port (default: 6004)
pin: "1234"           # User PIN for arming/disarming (optional)
use_outer_frame: true # Set false if using the OnboardLAN, true if using the PrimeLAN
poll: 1.0             # Poll interval in seconds (for future use)
```

---

## Quick Example

```python
import asyncio
from inim.prime.native.wire.protocol import Protocol
from inim.prime.native.operations import get_partitions


async def main():
    async with Protocol(host = "192.168.1.100", password = "yourpass", port = 6004) as proto:
        partitions = await get_partitions(proto)
        for p in partitions:
            print(p)


asyncio.run(main())
```

---

## Legal and Disclaimer

This project is not affiliated with, endorsed by, or supported by Inim Electronics s.r.l. in any way. "Inim", "Inim Prime", and "Inim Prime/STUDIO" are trademarks of Inim Electronics s.r.l., used here solely to identify the hardware and software this library is designed to interoperate with.

Use this software at your own risk. The author takes no responsibility for any damage to your alarm system or its configuration.

This software is released under the **GNU General Public License v3.0**. See [LICENSE](LICENSE) for the full text.

See [LEGAL.md](LEGAL.md) for a full statement covering the legal basis for this work, the applicable EU legislation, the EULA of Inim Prime/STUDIO, trademark usage, warranty disclaimer, and contact information.

---
made with ❤️ by Pitscheider
