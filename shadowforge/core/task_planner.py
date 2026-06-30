"""Task planning engine — decomposes high-level goals into executable steps."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """A single unit of work assigned to an agent."""

    name: str
    agent: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    parent_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "agent": self.agent,
            "action": self.action,
            "params": self.params,
            "status": self.status.value,
            "priority": self.priority.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "parent_id": self.parent_id,
        }


# Rule-based workflow templates
WORKFLOW_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "device_scanner": [
        {"name": "Scan directory", "agent": "file", "action": "scan_directory", "params": {"path": "~/Desktop", "depth": 5}},
        {"name": "Analyze & summarize", "agent": "file", "action": "analyze_summary", "params": {}},
        {"name": "Find duplicates", "agent": "file", "action": "find_duplicates", "params": {}},
    ],
    "organize_desktop": [
        {"name": "Scan desktop", "agent": "file", "action": "scan_directory", "params": {"path": "~/Desktop"}},
        {"name": "Analyze & summarize", "agent": "file", "action": "analyze_summary", "params": {}},
        {"name": "Find duplicates", "agent": "file", "action": "find_duplicates", "params": {}},
    ],
    "screen_audit": [
        {"name": "Capture screen", "agent": "vision", "action": "capture_screen", "params": {}},
        {"name": "Extract text", "agent": "vision", "action": "ocr_screen", "params": {}},
        {"name": "Detect UI elements", "agent": "vision", "action": "detect_elements", "params": {}},
    ],
    "cleanup_downloads": [
        {"name": "Scan downloads", "agent": "file", "action": "scan_directory", "params": {"path": "~/Downloads"}},
        {"name": "Analyze & summarize", "agent": "file", "action": "analyze_summary", "params": {}},
        {"name": "Find duplicates", "agent": "file", "action": "find_duplicates", "params": {}},
    ],
    "smart_automate": [
        {"name": "Capture screen", "agent": "vision", "action": "capture_screen", "params": {}},
        {"name": "Find target text", "agent": "vision", "action": "find_text", "params": {}},
        {"name": "Click target", "agent": "automation", "action": "click", "params": {"require_target": True}},
        {"name": "Execute keys", "agent": "automation", "action": "execute_keys", "params": {}},
    ],
    "automate_click": [
        {"name": "Capture screen", "agent": "vision", "action": "capture_screen", "params": {}},
        {"name": "Find target text", "agent": "vision", "action": "find_text", "params": {}},
        {"name": "Click target", "agent": "automation", "action": "click", "params": {"require_target": True}},
        {"name": "Execute keys", "agent": "automation", "action": "execute_keys", "params": {}},
    ],
}


class TaskPlanner:
    """Plans and manages task queues from workflows or custom definitions."""

    def __init__(self) -> None:
        self._queue: list[Task] = []
        self._completed: list[Task] = []

    def create_workflow(self, workflow_name: str, overrides: Optional[dict[str, Any]] = None) -> list[Task]:
        """Create a task list from a named workflow template."""
        template = WORKFLOW_TEMPLATES.get(workflow_name)
        if not template:
            raise ValueError(f"Unknown workflow: {workflow_name}")

        overrides = overrides or {}
        parent_id = str(uuid.uuid4())
        tasks: list[Task] = []

        for step in template:
            params = {**step.get("params", {}), **overrides}
            task = Task(
                name=step["name"],
                agent=step["agent"],
                action=step["action"],
                params=params,
                parent_id=parent_id,
            )
            tasks.append(task)

        return tasks

    def create_custom_task(
        self,
        name: str,
        agent: str,
        action: str,
        params: Optional[dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> Task:
        """Create a single custom task."""
        return Task(
            name=name,
            agent=agent,
            action=action,
            params=params or {},
            priority=priority,
        )

    def enqueue(self, task: Task) -> None:
        """Add a task to the queue, sorted by priority."""
        self._queue.append(task)
        self._queue.sort(key=lambda t: t.priority.value, reverse=True)

    def enqueue_workflow(self, workflow_name: str, overrides: Optional[dict[str, Any]] = None) -> list[Task]:
        """Create and enqueue all tasks from a workflow."""
        tasks = self.create_workflow(workflow_name, overrides)
        for task in tasks:
            self.enqueue(task)
        return tasks

    def dequeue(self) -> Optional[Task]:
        """Get the next pending task."""
        for task in self._queue:
            if task.status == TaskStatus.PENDING:
                return task
        return None

    def mark_running(self, task: Task) -> None:
        task.status = TaskStatus.RUNNING

    def mark_completed(self, task: Task, result: dict[str, Any]) -> None:
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.completed_at = time.time()
        self._completed.append(task)

    def mark_failed(self, task: Task, error: str) -> None:
        task.status = TaskStatus.FAILED
        task.error = error
        task.completed_at = time.time()
        self._completed.append(task)

    def get_queue(self) -> list[Task]:
        return list(self._queue)

    def get_completed(self) -> list[Task]:
        return list(self._completed)

    def clear_queue(self) -> None:
        self._queue.clear()

    def get_stats(self) -> dict[str, int]:
        statuses = [t.status for t in self._queue]
        return {
            "pending": sum(1 for s in statuses if s == TaskStatus.PENDING),
            "running": sum(1 for s in statuses if s == TaskStatus.RUNNING),
            "completed": len(self._completed),
            "failed": sum(1 for t in self._completed if t.status == TaskStatus.FAILED),
            "total_queued": len(self._queue),
        }