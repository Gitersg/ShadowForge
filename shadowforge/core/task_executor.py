"""Task execution engine — runs queued tasks against registered agents."""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

from shadowforge.core.base_agent import BaseAgent
from shadowforge.core.task_planner import Task, TaskPlanner, TaskStatus


class TaskExecutor:
    """Executes tasks from the planner queue using registered agents."""

    def __init__(
        self,
        planner: TaskPlanner,
        on_task_complete: Optional[Callable[[Task], None]] = None,
        on_task_error: Optional[Callable[[Task, str], None]] = None,
    ) -> None:
        self.planner = planner
        self.agents: dict[str, BaseAgent] = {}
        self.logger = logging.getLogger("shadowforge.executor")
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._on_task_complete = on_task_complete
        self._on_task_error = on_task_error

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent for task execution."""
        self.agents[agent.name] = agent
        self.logger.info("Registered agent: %s", agent.name)

    def unregister_agent(self, agent_name: str) -> None:
        """Remove an agent from the executor."""
        self.agents.pop(agent_name, None)

    def execute_task(self, task: Task) -> dict[str, Any]:
        """Execute a single task synchronously."""
        agent = self.agents.get(task.agent)
        if not agent:
            raise RuntimeError(f"No agent registered for: {task.agent}")

        self.planner.mark_running(task)
        self.logger.info("Executing task: %s [%s]", task.name, task.task_id)

        try:
            payload = {
                "action": task.action,
                "params": task.params,
                "task_id": task.task_id,
            }
            result = agent.process(payload)
            self.planner.mark_completed(task, result)
            if self._on_task_complete:
                self._on_task_complete(task)
            return result
        except Exception as exc:
            error_msg = str(exc)
            self.planner.mark_failed(task, error_msg)
            self.logger.error("Task failed: %s — %s", task.name, error_msg)
            if self._on_task_error:
                self._on_task_error(task, error_msg)
            raise

    def start(self) -> None:
        """Start background task execution loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.logger.info("Task executor started")

    def stop(self) -> None:
        """Stop background execution loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self.logger.info("Task executor stopped")

    def _run_loop(self) -> None:
        """Continuously dequeue and execute pending tasks."""
        while self._running:
            task = self.planner.dequeue()
            if task:
                try:
                    self.execute_task(task)
                except Exception:
                    pass
            else:
                threading.Event().wait(0.5)

    @property
    def is_running(self) -> bool:
        return self._running