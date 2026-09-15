"""Context tracking for UNSW-NB15 live-flow contextual features."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from time import time


@dataclass(frozen=True)
class FlowContext:
    """Minimal identity information for one observed flow."""

    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    service: str
    state: str
    ttl: int


class ContextTracker:
    """Track recent flows for UNSW-NB15 contextual counters.

    The tracker keeps a bounded history of recently observed flows.
    Contextual values are calculated from that history rather than
    fabricated as constants.
    """

    def __init__(
        self,
        window_seconds: float = 100.0,
        max_history: int = 10000,
    ) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than zero.")

        if max_history <= 0:
            raise ValueError("max_history must be greater than zero.")

        self.window_seconds = window_seconds
        self.max_history = max_history

        self._history: deque[tuple[float, FlowContext]] = deque()

    def _purge(self, current_time: float) -> None:
        """Remove flow observations outside the context window."""

        cutoff = current_time - self.window_seconds

        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

    def record_flow(
        self,
        src_ip: str,
        dst_ip: str,
        src_port: int,
        dst_port: int,
        service: str,
        state: str,
        ttl: int,
        timestamp: float | None = None,
    ) -> None:
        """Record one finalized flow observation."""

        current_time = time() if timestamp is None else timestamp

        self._purge(current_time)

        context = FlowContext(
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=dst_port,
            service=service,
            state=state,
            ttl=ttl,
        )

        self._history.append((current_time, context))

        while len(self._history) > self.max_history:
            self._history.popleft()

    def _recent_contexts(self, current_time: float) -> list[FlowContext]:
        """Return contexts currently inside the tracking window."""

        self._purge(current_time)
        return [context for _, context in self._history]

    def ct_srv_src(
        self,
        service: str,
        src_ip: str,
        current_time: float | None = None,
    ) -> int:
        """Count recent flows using the same service and source IP."""

        now = time() if current_time is None else current_time

        return sum(
            1
            for context in self._recent_contexts(now)
            if context.service == service
            and context.src_ip == src_ip
        )

    def ct_state_ttl(
        self,
        state: str,
        ttl: int,
        current_time: float | None = None,
    ) -> int:
        """Count recent flows sharing state and TTL."""

        now = time() if current_time is None else current_time

        return sum(
            1
            for context in self._recent_contexts(now)
            if context.state == state
            and context.ttl == ttl
        )

    def ct_dst_ltm(
        self,
        dst_ip: str,
        current_time: float | None = None,
    ) -> int:
        """Count recent flows targeting the same destination."""

        now = time() if current_time is None else current_time

        return sum(
            1
            for context in self._recent_contexts(now)
            if context.dst_ip == dst_ip
        )

    def ct_src_dport_ltm(
        self,
        src_ip: str,
        dst_port: int,
        current_time: float | None = None,
    ) -> int:
        """Count recent flows sharing source IP and destination port."""

        now = time() if current_time is None else current_time

        return sum(
            1
            for context in self._recent_contexts(now)
            if context.src_ip == src_ip
            and context.dst_port == dst_port
        )

    def ct_dst_sport_ltm(
        self,
        dst_ip: str,
        src_port: int,
        current_time: float | None = None,
    ) -> int:
        """Count recent flows sharing destination IP and source port."""

        now = time() if current_time is None else current_time

        return sum(
            1
            for context in self._recent_contexts(now)
            if context.dst_ip == dst_ip
            and context.src_port == src_port
        )

    def ct_dst_src_ltm(
        self,
        dst_ip: str,
        src_ip: str,
        current_time: float | None = None,
    ) -> int:
        """Count recent flows sharing the same source/destination pair."""

        now = time() if current_time is None else current_time

        return sum(
            1
            for context in self._recent_contexts(now)
            if context.dst_ip == dst_ip
            and context.src_ip == src_ip
        )

    def ct_src_ltm(
        self,
        src_ip: str,
        current_time: float | None = None,
    ) -> int:
        """Count recent flows originating from the same source."""

        now = time() if current_time is None else current_time

        return sum(
            1
            for context in self._recent_contexts(now)
            if context.src_ip == src_ip
        )

    def ct_srv_dst(
        self,
        service: str,
        dst_ip: str,
        current_time: float | None = None,
    ) -> int:
        """Count recent flows using the same service and destination."""

        now = time() if current_time is None else current_time

        return sum(
            1
            for context in self._recent_contexts(now)
            if context.service == service
            and context.dst_ip == dst_ip
        )

    def is_sm_ips_ports(
        self,
        src_ip: str,
        dst_ip: str,
        src_port: int,
        dst_port: int,
        current_time: float | None = None,
    ) -> int:
        """Return 1 when source/destination IPs and ports are identical."""

        return int(
            src_ip == dst_ip
            and src_port == dst_port
        )

    def history_size(self) -> int:
        """Return the number of currently retained observations."""

        return len(self._history)

    def clear(self) -> None:
        """Clear all tracked flow context."""

        self._history.clear()