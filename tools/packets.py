import os
from dataclasses import dataclass

from scapy.all import rdpcap
from scapy.layers.inet import IP, TCP
from scapy.packet import Raw
from scapy.plist import PacketList

from inim.prime.native.const import Panel
from inim.prime.native.wire.cipher import Cipher
from inim.prime.native.wire.frame import Frame

from tools.utils import list_files, choose_from_list


# Resolve path relative to this script (tools/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PCAP_DIR = os.path.join(BASE_DIR, "..", "data", "captures")

@dataclass
class Packet:
    source: str
    destination: str
    frame: Frame
    payload: bytes = None


def filter_raw_packets(
        raw_packets: PacketList,
        frame_type: type[Frame],
        port: int = Panel.DEFAULT_PORT,
) -> list[Packet]:
    packets: list[Packet] = []
    for pkt in raw_packets:
        if not (pkt.haslayer(IP) and pkt.haslayer(TCP) and pkt.haslayer(Raw)):
            continue
        if not (pkt[TCP].sport == port or pkt[TCP].dport == port):
            continue

        packets.append(
            Packet(
                source=pkt[IP].src,
                destination=pkt[IP].dst,
                frame=frame_type.from_bytes(bytes(pkt[Raw].load)),
            )
        )

    return packets

def decrypt_packets(packets: list[Packet], cipher: Cipher) -> list[Packet]:
    for pkt in packets:
        pkt.payload = cipher.decrypt(pkt.frame.encrypted_payload)
    return packets

def load_packets(frame_type: type[Frame], port: int = Panel.DEFAULT_PORT) -> list[Packet]:
    directory = os.path.normpath(PCAP_DIR)
    if not os.path.exists(directory):
        print(f"Directory not found: {directory}")
        raise FileNotFoundError(f"Directory not found: {directory}")

    files = list_files(directory, [".pcap"])
    selected = choose_from_list(files, "Available pcap files:")

    if not selected:
        raise ValueError("No file selected")
    pcap_path = os.path.join(directory, selected)
    packets_raw = rdpcap(pcap_path)
    packets = filter_raw_packets(packets_raw, frame_type, port)

    return packets
