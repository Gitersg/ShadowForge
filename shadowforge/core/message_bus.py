"""Simple pub/sub message bus for inter-agent communication."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Message:
    """A message passed between agents."""

    sender: str
    recipient: str
    message_type: str
    payload: dict[str, Any]
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)


MessageHandler = Callable[[Message], None]


class MessageBus:
    """Thread-safe message bus supporting direct and broadcast delivery."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[MessageHandler]] = {}
        self._history: list[Message] = []
        self._lock = threading.Lock()
        self._max_history = 500

    def subscribe(self, agent_name: str, handler: MessageHandler) -> None:
        """Register a handler for messages addressed to an agent."""
        with self._lock:
            if agent_name not in self._subscribers:
                self._subscribers[agent_name] = []
            self._subscribers[agent_name].append(handler)

    def unsubscribe(self, agent_name: str, handler: MessageHandler) -> None:
        """Remove a handler from an agent's subscription list."""
        with self._lock:
            if agent_name in self._subscribers:
                self._subscribers[agent_name] = [
                    h for h in self._subscribers[agent_name] if h != handler
                ]

    def publish(self, message: Message) -> None:
        """Deliver a message to recipient(s) and store in history."""
        with self._lock:
            self._history.append(message)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]

        handlers: list[MessageHandler] = []
        with self._lock:
            if message.recipient == "*":
                for agent_handlers in self._subscribers.values():
                    handlers.extend(agent_handlers)
            elif message.recipient in self._subscribers:
                handlers = list(self._subscribers[message.recipient])

        for handler in handlers:
            try:
                handler(message)
            except Exception:
                pass  # Handlers should log their own errors

    def get_history(self, limit: int = 50) -> list[Message]:
        """Return recent message history."""
        with self._lock:
            return list(self._history[-limit:])

    def clear_history(self) -> None:
        """Clear message history."""
        with self._lock:
            self._history.clear()