"""Example plugin agent — template for creating custom ShadowForge agents.

Copy this file, rename it, and implement your own agent logic.
ShadowForge will auto-discover any .py file in the plugins/ directory.
"""

from __future__ import annotations

from typing import Any

from shadowforge.core.base_agent import BaseAgent
from shadowforge.core.message_bus import MessageBus


class ExampleAgent(BaseAgent):
    """A sample custom agent that echoes task parameters."""

    def __init__(self, message_bus: MessageBus, name: str = "example") -> None:
        super().__init__(
            name=name,
            message_bus=message_bus,
            capabilities=["echo", "ping"],
        )

    def process(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "ping")
        params = task.get("params", {})

        if action == "echo":
            return {"success": True, "echo": params}
        return {"success": True, "message": "pong", "agent": self.name}