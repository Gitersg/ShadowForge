"""Action history tracker for audit and dashboard display."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class HistoryEntry:
    """A single recorded agent action."""

    entry_id: str
    agent: str
    action: str
    status: str
    details: dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ActionHistory:
    """Persistent action history with in-memory cache."""

    def __init__(self, history_file: Optional[Path] = None) -> None:
        self.history_file = history_file or Path("data") / "history.json"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._entries: list[HistoryEntry] = []
        self._load()

    def record(
        self,
        agent: str,
        action: str,
        status: str,
        details: Optional[dict[str, Any]] = None,
    ) -> HistoryEntry:
        """Record a new action entry."""
        entry = HistoryEntry(
            entry_id=str(uuid.uuid4()),
            agent=agent,
            action=action,
            status=status,
            details=details or {},
        )
        self._entries.append(entry)
        self._save()
        return entry

    def get_recent(self, limit: int = 50) -> list[HistoryEntry]:
        return list(self._entries[-limit:])

    def get_by_agent(self, agent: str, limit: int = 20) -> list[HistoryEntry]:
        return [e for e in self._entries if e.agent == agent][-limit:]

    def clear(self) -> None:
        self._entries.clear()
        self._save()

    def _save(self) -> None:
        try:
            data = [e.to_dict() for e in self._entries[-1000:]]
            self.history_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _load(self) -> None:
        if not self.history_file.exists():
            return
        try:
            data = json.loads(self.history_file.read_text(encoding="utf-8"))
            self._entries = [
                HistoryEntry(
                    entry_id=d["entry_id"],
                    agent=d["agent"],
                    action=d["action"],
                    status=d["status"],
                    details=d.get("details", {}),
                    timestamp=d.get("timestamp", 0),
                )
                for d in data
            ]
        except (json.JSONDecodeError, KeyError, OSError):
            self._entries = []