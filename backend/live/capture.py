"""Controlled live packet-capture engine."""

from __future__ import annotations

from threading import Event
from time import time
from typing import Callable

from scapy.packet import Packet
from scapy.sendrecv import sniff

from backend.live.flow_aggregator import FlowAggregator
from backend.live.flow_manager import FlowManager
from backend.live.packet_adapter import packet_to_flow

FlowCallback = Callable[[dict], None]


class LiveCapture:
    """Capture packets, aggregate flows, and emit finalized flow features."""

    def __init__(
        self,
        iface: str,
        timeout_seconds: float = 5.0,
        on_flow: FlowCallback | None = None,
    ) -> None:
        self.iface = iface
        self.aggregator = FlowAggregator()
        self.manager = FlowManager(timeout_seconds=timeout_seconds)
        self.on_flow = on_flow
        self._stop_event = Event()
        self._running = False

    def _finalize_expired_flows(self, current_time: float) -> None:
        """Finalize inactive flows and remove them from both stores."""

        expired = self.manager.expire(current_time)

        for finalized in expired:
            self.aggregator.remove_flow(finalized.flow)

            if self.on_flow is not None:
                self.on_flow(finalized.features)

    def _process_packet(self, packet: Packet) -> None:
        """Process one captured packet."""

        timestamp = float(getattr(packet, "time", time()))

        flow = packet_to_flow(
            packet=packet,
            aggregator=self.aggregator,
            timestamp=timestamp,
        )

        if flow is None:
            return

        self.manager.add_flow(flow)
        self._finalize_expired_flows(timestamp)

    def start(self) -> None:
        """Start controlled packet capture until stop() is requested."""

        if self._running:
            raise RuntimeError("Live capture is already running.")

        self._running = True
        self._stop_event.clear()

        try:
            while not self._stop_event.is_set():
                sniff(
                    iface=self.iface,
                    prn=self._process_packet,
                    store=False,
                    timeout=1,
                )

                self._finalize_expired_flows(time())

        finally:
            self._running = False

    def stop(self) -> None:
        """Request capture shutdown."""

        self._stop_event.set()

    def is_running(self) -> bool:
        """Return whether live capture is currently running."""

        return self._running