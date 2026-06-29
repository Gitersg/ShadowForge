"""Abstract base class for all ShadowForge agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from shadowforge.core.message_bus import Message, MessageBus


class BaseAgent(ABC):
    """Abstract base agent with message-passing and lifecycle hooks."""

    def __init__(
        self,
        name: str,
        message_bus: MessageBus,
        capabilities: Optional[list[str]] = None,
    ) -> None:
        self.name = name
        self.message_bus = message_bus
        self.capabilities = capabilities or []
        self.logger = logging.getLogger(f"shadowforge.agent.{name}")
        self._running = False
        self.message_bus.subscribe(self.name, self._on_message)

    @abstractmethod
    def process(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute a task and return a result dictionary."""

    def start(self) -> None:
        """Mark agent as active."""
        self._running = True
        self.logger.info("Agent started: %s", self.name)

    def stop(self) -> None:
        """Mark agent as inactive."""
        self._running = False
        self.logger.info("Agent stopped: %s", self.name)

    @property
    def is_running(self) -> bool:
        return self._running

    def send_message(
        self,
        recipient: str,
        payload: dict[str, Any],
        message_type: str = "task",
    ) -> None:
        """Send a message to another agent via the message bus."""
        msg = Message(
            sender=self.name,
            recipient=recipient,
            message_type=message_type,
            payload=payload,
        )
        self.message_bus.publish(msg)

    def broadcast(self, payload: dict[str, Any], message_type: str = "broadcast") -> None:
        """Broadcast a message to all agents."""
        msg = Message(
            sender=self.name,
            recipient="*",
            message_type=message_type,
            payload=payload,
        )
        self.message_bus.publish(msg)

    def _on_message(self, message: Message) -> None:
        """Handle incoming messages. Override for custom behavior."""
        self.logger.debug(
            "Received %s from %s", message.message_type, message.sender
        )

    def get_status(self) -> dict[str, Any]:
        """Return agent status for dashboard display."""
        return {
            "name": self.name,
            "running": self._running,
            "capabilities": self.capabilities,
        }