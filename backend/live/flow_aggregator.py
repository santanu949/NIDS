"""Packet-to-flow aggregation for controlled live-mode traffic."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any

from backend.live.context_tracker import ContextTracker


def infer_service(src_port: int, dst_port: int, proto: str) -> str:
    """Infer a common UNSW-NB15 service from transport ports."""

    if proto == "udp":
        port_map = {
            53: "dns",
            67: "dhcp",
            68: "dhcp",
            161: "snmp",
        }
    elif proto == "tcp":
        port_map = {
            20: "ftp-data",
            21: "ftp",
            22: "ssh",
            25: "smtp",
            53: "dns",
            80: "http",
            110: "pop3",
            443: "ssl",
            6667: "irc",
        }
    else:
        return "-"

    return port_map.get(dst_port, port_map.get(src_port, "-"))


@dataclass
class Flow:
    """State accumulated from packets belonging to one bidirectional flow."""

    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    proto: str

    start_time: float
    last_time: float

    spkts: int = 0
    dpkts: int = 0
    sbytes: int = 0
    dbytes: int = 0

    sttl: int = 0
    dttl: int = 0
    swin: int = 0
    dwin: int = 0
    stcpb: int = 0
    dtcpb: int = 0

    syn_time: float | None = None
    synack_time: float | None = None
    ack_time: float | None = None

    saw_fin: bool = False
    saw_rst: bool = False
    saw_ack: bool = False
    state: str = "INT"

    src_times: list[float] = field(default_factory=list)
    dst_times: list[float] = field(default_factory=list)

    def add_packet(
        self,
        timestamp: float,
        packet_size: int,
        source_direction: bool,
        ttl: int = 0,
        window: int = 0,
        seq: int = 0,
        syn: bool = False,
        ack: bool = False,
        fin: bool = False,
        rst: bool = False,
    ) -> None:
        """Add one packet and retain measurable packet metadata."""

        self.last_time = timestamp

        if ack:
            self.saw_ack = True

        if fin:
            self.saw_fin = True

        if rst:
            self.saw_rst = True

        if rst:
            self.state = "RST"
        elif fin:
            self.state = "FIN"
        elif syn and not ack:
            self.state = "REQ"
        elif syn and ack:
            self.state = "CON"
        elif ack:
            self.state = "CON"

        if source_direction:
            self.spkts += 1
            self.sbytes += packet_size
            self.src_times.append(timestamp)

            if self.spkts == 1:
                self.sttl = ttl
                self.swin = window
                self.stcpb = seq

            if syn and not ack and self.syn_time is None:
                self.syn_time = timestamp

            if ack and self.syn_time is not None and self.ack_time is None:
                self.ack_time = timestamp

        else:
            self.dpkts += 1
            self.dbytes += packet_size
            self.dst_times.append(timestamp)

            if self.dpkts == 1:
                self.dttl = ttl
                self.dwin = window
                self.dtcpb = seq

            if syn and ack and self.synack_time is None:
                self.synack_time = timestamp

    @property
    def duration(self) -> float:
        return max(0.0, self.last_time - self.start_time)

    @property
    def total_packets(self) -> int:
        return self.spkts + self.dpkts

    @property
    def total_bytes(self) -> int:
        return self.sbytes + self.dbytes

    @property
    def rate(self) -> float:
        if self.duration <= 0:
            return 0.0

        return self.total_packets / self.duration

    @staticmethod
    def _mean_interval(timestamps: list[float]) -> float:
        if len(timestamps) < 2:
            return 0.0

        intervals = [
            current - previous
            for previous, current in zip(timestamps, timestamps[1:])
        ]

        return sum(intervals) / len(intervals)

    @staticmethod
    def _mean_jitter(timestamps: list[float]) -> float:
        if len(timestamps) < 3:
            return 0.0

        intervals = [
            current - previous
            for previous, current in zip(timestamps, timestamps[1:])
        ]

        if len(intervals) < 2:
            return 0.0

        jitter_values = [
            abs(current - previous)
            for previous, current in zip(intervals, intervals[1:])
        ]

        return sum(jitter_values) / len(jitter_values)

    @property
    def sinpkt(self) -> float:
        """Source inter-packet arrival time in milliseconds."""

        return self._mean_interval(self.src_times) * 1000.0

    @property
    def dinpkt(self) -> float:
        """Destination inter-packet arrival time in milliseconds."""

        return self._mean_interval(self.dst_times) * 1000.0

    @property
    def sjit(self) -> float:
        """Source packet jitter in milliseconds."""

        return self._mean_jitter(self.src_times) * 1000.0

    @property
    def djit(self) -> float:
        """Destination packet jitter in milliseconds."""

        return self._mean_jitter(self.dst_times) * 1000.0

    @property
    def synack(self) -> float:
        """Time between SYN and SYN-ACK in milliseconds."""

        if self.syn_time is None or self.synack_time is None:
            return 0.0

        return max(
            0.0,
            self.synack_time - self.syn_time,
        ) * 1000.0

    @property
    def ackdat(self) -> float:
        """Time between SYN-ACK and ACK in milliseconds."""

        if self.synack_time is None or self.ack_time is None:
            return 0.0

        return max(
            0.0,
            self.ack_time - self.synack_time,
        ) * 1000.0

    @property
    def tcprtt(self) -> float:
        """TCP setup round-trip time in milliseconds."""

        if self.syn_time is None or self.ack_time is None:
            return 0.0

        return max(
            0.0,
            self.ack_time - self.syn_time,
        ) * 1000.0

    def to_partial_features(
        self,
        context_tracker: ContextTracker | None = None,
    ) -> dict[str, Any]:
        """Return currently measurable UNSW-NB15-compatible fields.

        Contextual features are populated from ContextTracker when supplied.
        Features requiring application-level semantics remain zero until
        their extraction semantics are implemented.
        """

        duration = self.duration

        service = infer_service(
            self.src_port,
            self.dst_port,
            self.proto,
        )

        if context_tracker is not None:
            ct_srv_src = context_tracker.ct_srv_src(
                service=service,
                src_ip=self.src_ip,
                current_time=self.last_time,
            )

            ct_state_ttl = context_tracker.ct_state_ttl(
                state=self.state,
                ttl=self.sttl,
                current_time=self.last_time,
            )

            ct_dst_ltm = context_tracker.ct_dst_ltm(
                dst_ip=self.dst_ip,
                current_time=self.last_time,
            )

            ct_src_dport_ltm = context_tracker.ct_src_dport_ltm(
                src_ip=self.src_ip,
                dst_port=self.dst_port,
                current_time=self.last_time,
            )

            ct_dst_sport_ltm = context_tracker.ct_dst_sport_ltm(
                dst_ip=self.dst_ip,
                src_port=self.src_port,
                current_time=self.last_time,
            )

            ct_dst_src_ltm = context_tracker.ct_dst_src_ltm(
                dst_ip=self.dst_ip,
                src_ip=self.src_ip,
                current_time=self.last_time,
            )

            ct_src_ltm = context_tracker.ct_src_ltm(
                src_ip=self.src_ip,
                current_time=self.last_time,
            )

            ct_srv_dst = context_tracker.ct_srv_dst(
                service=service,
                dst_ip=self.dst_ip,
                current_time=self.last_time,
            )

            is_sm_ips_ports = context_tracker.is_sm_ips_ports(
                src_ip=self.src_ip,
                dst_ip=self.dst_ip,
                src_port=self.src_port,
                dst_port=self.dst_port,
                current_time=self.last_time,
            )
        else:
            ct_srv_src = 0
            ct_state_ttl = 0
            ct_dst_ltm = 0
            ct_src_dport_ltm = 0
            ct_dst_sport_ltm = 0
            ct_dst_src_ltm = 0
            ct_src_ltm = 0
            ct_srv_dst = 0
            is_sm_ips_ports = 0

        return {
            "dur": duration,
            "proto": self.proto,
            "service": service,
            "state": self.state,
            "spkts": self.spkts,
            "dpkts": self.dpkts,
            "sbytes": self.sbytes,
            "dbytes": self.dbytes,
            "rate": self.rate,
            "sttl": self.sttl,
            "dttl": self.dttl,
            "sload": (
                self.sbytes * 8 / duration
                if duration > 0
                else 0.0
            ),
            "dload": (
                self.dbytes * 8 / duration
                if duration > 0
                else 0.0
            ),
            "sloss": 0,
            "dloss": 0,
            "sinpkt": self.sinpkt,
            "dinpkt": self.dinpkt,
            "sjit": self.sjit,
            "djit": self.djit,
            "swin": self.swin,
            "stcpb": self.stcpb,
            "dtcpb": self.dtcpb,
            "dwin": self.dwin,
            "tcprtt": self.tcprtt,
            "synack": self.synack,
            "ackdat": self.ackdat,
            "smean": (
                self.sbytes / self.spkts
                if self.spkts
                else 0.0
            ),
            "dmean": (
                self.dbytes / self.dpkts
                if self.dpkts
                else 0.0
            ),
            "trans_depth": 0,
            "response_body_len": 0,
            "ct_srv_src": ct_srv_src,
            "ct_state_ttl": ct_state_ttl,
            "ct_dst_ltm": ct_dst_ltm,
            "ct_src_dport_ltm": ct_src_dport_ltm,
            "ct_dst_sport_ltm": ct_dst_sport_ltm,
            "ct_dst_src_ltm": ct_dst_src_ltm,
            "is_ftp_login": 0,
            "ct_ftp_cmd": 0,
            "ct_flw_http_mthd": 0,
            "ct_src_ltm": ct_src_ltm,
            "ct_srv_dst": ct_srv_dst,
            "is_sm_ips_ports": is_sm_ips_ports,
        }


class FlowAggregator:
    """Maintain active bidirectional flows."""

    def __init__(self) -> None:
        self._flows: dict[tuple[Any, ...], Flow] = {}

    @staticmethod
    def _flow_key(
        src_ip: str,
        dst_ip: str,
        src_port: int,
        dst_port: int,
        proto: str,
    ) -> tuple[Any, ...]:
        forward = (
            src_ip,
            dst_ip,
            src_port,
            dst_port,
            proto,
        )

        reverse = (
            dst_ip,
            src_ip,
            dst_port,
            src_port,
            proto,
        )

        return min(forward, reverse)

    def add_packet(
        self,
        src_ip: str,
        dst_ip: str,
        src_port: int,
        dst_port: int,
        proto: str,
        packet_size: int,
        timestamp: float | None = None,
        ttl: int = 0,
        window: int = 0,
        seq: int = 0,
        syn: bool = False,
        ack: bool = False,
        fin: bool = False,
        rst: bool = False,
    ) -> Flow:
        """Add a packet and return the updated flow."""

        now = time() if timestamp is None else timestamp

        key = self._flow_key(
            src_ip,
            dst_ip,
            src_port,
            dst_port,
            proto,
        )

        flow = self._flows.get(key)

        if flow is None:
            flow = Flow(
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_port=src_port,
                dst_port=dst_port,
                proto=proto,
                start_time=now,
                last_time=now,
            )

            self._flows[key] = flow

        source_direction = (
            src_ip == flow.src_ip
            and dst_ip == flow.dst_ip
            and src_port == flow.src_port
            and dst_port == flow.dst_port
        )

        flow.add_packet(
            timestamp=now,
            packet_size=packet_size,
            source_direction=source_direction,
            ttl=ttl,
            window=window,
            seq=seq,
            syn=syn,
            ack=ack,
            fin=fin,
            rst=rst,
        )

        return flow

    def active_flow_count(self) -> int:
        return len(self._flows)

    def remove_flow(self, flow: Flow) -> None:
        """Remove a completed flow from the active-flow store."""

        key = self._flow_key(
            flow.src_ip,
            flow.dst_ip,
            flow.src_port,
            flow.dst_port,
            flow.proto,
        )

        self._flows.pop(key, None)

    def clear(self) -> None:
        self._flows.clear()