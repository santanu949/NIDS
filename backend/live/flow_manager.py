"""Manage active live flows and finalize inactive flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.live.context_tracker import ContextTracker
from backend.live.flow_aggregator import Flow


@dataclass
class FinalizedFlow:
    """A flow that has become inactive and is ready for processing."""

    flow: Flow
    features: dict[str, Any]


class FlowManager:
    """Track flows and finalize them after an inactivity timeout."""

    def __init__(
        self,
        timeout_seconds: float = 5.0,
        context_tracker: ContextTracker | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")

        self.timeout_seconds = timeout_seconds
        self.context_tracker = (
            context_tracker
            if context_tracker is not None
            else ContextTracker()
        )
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

    def add_flow(self, flow: Flow) -> None:
        """Register or update an active flow."""

        key = self._flow_key(
            flow.src_ip,
            flow.dst_ip,
            flow.src_port,
            flow.dst_port,
            flow.proto,
        )

        self._flows[key] = flow

    def expire(self, current_time: float) -> list[FinalizedFlow]:
        """Finalize flows inactive for longer than the configured timeout."""

        expired: list[FinalizedFlow] = []

        for key, flow in list(self._flows.items()):
            if current_time - flow.last_time < self.timeout_seconds:
                continue

            features = flow.to_partial_features(
                context_tracker=self.context_tracker,
            )

            expired.append(
                FinalizedFlow(
                    flow=flow,
                    features=features,
                )
            )

            self.context_tracker.record_flow(
                src_ip=flow.src_ip,
                dst_ip=flow.dst_ip,
                src_port=flow.src_port,
                dst_port=flow.dst_port,
                service=features["service"],
                state=features["state"],
                ttl=features["sttl"],
                timestamp=flow.last_time,
            )

            del self._flows[key]

        return expired

    def active_flow_count(self) -> int:
        return len(self._flows)

    def clear(self) -> None:
        self._flows.clear()
        self.context_tracker.clear()