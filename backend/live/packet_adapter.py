"""Convert captured Scapy packets into FlowAggregator inputs."""

from __future__ import annotations

from typing import Any

from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.inet6 import IPv6
from scapy.packet import Packet

from backend.live.flow_aggregator import FlowAggregator


def packet_to_flow(
    packet: Packet,
    aggregator: FlowAggregator,
    timestamp: float,
) -> Any | None:
    """Add a supported IPv4/IPv6 TCP/UDP packet to the flow aggregator."""

    if IP in packet:
        ip_layer = packet[IP]
        src_ip = ip_layer.src
        dst_ip = ip_layer.dst
        ttl = int(ip_layer.ttl)

    elif IPv6 in packet:
        ip_layer = packet[IPv6]
        src_ip = ip_layer.src
        dst_ip = ip_layer.dst
        ttl = int(ip_layer.hlim)

    else:
        return None

    if TCP in packet:
        transport = packet[TCP]

        proto = "tcp"
        src_port = int(transport.sport)
        dst_port = int(transport.dport)

        window = int(transport.window)
        seq = int(transport.seq)

        flags = int(transport.flags)

        syn = bool(flags & 0x02)
        ack = bool(flags & 0x10)
        fin = bool(flags & 0x01)
        rst = bool(flags & 0x04)

    elif UDP in packet:
        transport = packet[UDP]

        proto = "udp"
        src_port = int(transport.sport)
        dst_port = int(transport.dport)

        window = 0
        seq = 0

        syn = False
        ack = False
        fin = False
        rst = False

    else:
        return None

    return aggregator.add_packet(
        src_ip=src_ip,
        dst_ip=dst_ip,
        src_port=src_port,
        dst_port=dst_port,
        proto=proto,
        packet_size=len(packet),
        timestamp=timestamp,
        ttl=ttl,
        window=window,
        seq=seq,
        syn=syn,
        ack=ack,
        fin=fin,
        rst=rst,
    )