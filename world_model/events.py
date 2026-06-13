from __future__ import annotations

import asyncio
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional


class EventSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class RoboticsEvent:
    event_type: str
    agent_id: str
    severity: EventSeverity
    payload: dict
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    world_object_id: Optional[str] = None


class EventType:
    QR_FOUND = "qr_found"
    OBSTACLE_DETECTED = "obstacle_detected"
    BATTERY_LOW = "battery_low"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    TOOL_WEAR_WARNING = "tool_wear_warning"
    LEAK_DETECTED = "leak_detected"
    AGENT_READY = "agent_ready"
    MISSION_STARTED = "mission_started"
    MISSION_COMPLETE = "mission_complete"


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = {}
        self._wildcard: list[Callable] = []
        self._history: deque[RoboticsEvent] = deque(maxlen=500)

    async def publish(self, event: RoboticsEvent) -> None:
        self._history.append(event)
        callbacks = list(self._subscribers.get(event.event_type, [])) + list(self._wildcard)
        for cb in callbacks:
            try:
                result = cb(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass

    def subscribe(self, event_type: str, callback: Callable) -> None:
        self._subscribers.setdefault(event_type, []).append(callback)

    def subscribe_all(self, callback: Callable) -> None:
        self._wildcard.append(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass

    def get_history(
        self, event_type: Optional[str] = None, limit: int = 50
    ) -> list[RoboticsEvent]:
        events = list(self._history)
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]
